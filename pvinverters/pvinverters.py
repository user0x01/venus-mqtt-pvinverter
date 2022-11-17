#!/usr/bin/env python

"""
/data/Pathtothisscript/vedbus.py
/data/Pathtothisscript/ve_utils.py
python -m ensurepip --upgrade
pip install paho-mqtt
"""

import dbus.service
import dbus
from vedbus import VeDbusService
from datetime import timedelta
import datetime

#################################################
servicenamespace = "com.victronenergy.pvinverter"
productid = 1200
path_UpdateIndex = "/UpdateIndex"
disconnect_timeout = 60 
null_timeout = 10
# MQTT
mqttbroker_address = "Homeassistant.local" ## mqtt server
mqttclientid = "Venus.pvinverter"
mqttusername = "Venus"
mqttpassword = ""
topics = "venus/pvinverter/#"  # Topicsfilter
topic_init = "/init"  # Topic constructor
topic_values = "/values"  # Topic values
topic_close = "/close"  # Topic
#################################################

try:
  import gobject  # Python 2.x
except:
  from gi.repository import GLib as gobject # Python 3.x
import platform
import logging
import time
import sys
import json
import os
import paho.mqtt.client as mqtt
try:
  import thread   # for daemon = True  / Python 2.x
except:
  import _thread as thread   # for daemon = True  / Python 3.x

# our own packages
sys.path.insert(1, os.path.join(os.path.dirname(__file__), "../ext/velib_python"))

# Again not all of these needed this is just duplicating the Victron code.
class SystemBus(dbus.bus.BusConnection):
    def __new__(cls):
        return dbus.bus.BusConnection.__new__(cls, dbus.bus.BusConnection.TYPE_SYSTEM)

class SessionBus(dbus.bus.BusConnection):
    def __new__(cls):
        return dbus.bus.BusConnection.__new__(cls, dbus.bus.BusConnection.TYPE_SESSION)

def dbusconnection():
    return SessionBus() if 'DBUS_SESSION_BUS_ADDRESS' in os.environ else SystemBus()


global serivices

def on_disconnect(client, userdata, rc):
    print("Client Got Disconnected")
    if rc != 0:
        print("Unexpected MQTT disconnection. Will auto-reconnect")

    else:
        print("rc value:" + str(rc))

    try:
        print("Trying to Reconnect")
        client.connect(mqttbroker_address)
    except Exception as e:
        logging.exception("Fehler beim reconnecten mit Broker")
        print("Error in Retrying to Connect with Broker")
        print(e)

def on_connect(client, userdata, flags, rc):
        if rc == 0:
            print("Connected to MQTT Broker!")
            client.subscribe(topics)
        else:
            print("Failed to connect, return code %d\n", rc)


def on_message(client, userdata, msg):
    try:
        global serivices

        if msg.topic.endswith(topic_init):
            jsonpayload = json.loads(msg.payload)
            key = jsonpayload["key"]
            if key in serivices:
              return

            deviceinstance = jsonpayload["deviceinstance"]
            productname = jsonpayload["productname"]
            customname = jsonpayload["customname"]
            hardware = jsonpayload["hardware"]
            firmware = jsonpayload["firmware"]
            phase = jsonpayload["phase"]
            ip_address = jsonpayload["ip_address"]
            position = jsonpayload["position" or 1]
            _newservice(key, deviceinstance, productname,
              customname, phase, position, ip_address, hardware, firmware)

        if msg.topic.endswith(topic_close):
            jsonpayload = json.loads(msg.payload)
            key = jsonpayload["key"]
            if not key in serivices:
                return
            serivice = serivices[key]
            del serivices[key]
            del serivice

        if msg.topic.endswith(topic_values):
            jsonpayload = json.loads(msg.payload)
            key = jsonpayload["key"]
            if not key in serivices:
                return

            serivice = serivices[key]
            voltage = float(jsonpayload["voltage"] or 0)
            power = float(jsonpayload["power"] or 0)
            totalout = float(jsonpayload["energy"] or 0)
            if voltage > 0:
                curr = round(power / voltage, 2)
            else:
                curr = 0.0
            maxpower = float(jsonpayload["maxpower"] or 4800.0)
            powerlimit = float(jsonpayload["powerlimit"] or 4800.0)
            serivice._update(curr, power, totalout,
                             voltage, maxpower, powerlimit)

    except Exception as e:
        logging.exception(e)
        print(e)


class DbusService:
  phase = 1
  timestamp = datetime.datetime.now(datetime.timezone.utc)

  def __init__(self, servicename, deviceinstance, pathsReadOnly, pathsReadWrite):
    self._VeDbus = VeDbusService(servicename, dbusconnection())
    logging.debug("%s /DeviceInstance = %d" % (servicename, deviceinstance))

    for path, settings in pathsReadOnly.items():
        self._VeDbus.add_path(path, settings["initial"])

    for path, settings in pathsReadWrite.items():
        self._VeDbus.add_path(path, settings["initial"], writeable=True,
            onchangecallback=self._handlechangedvalue,
            gettextcallback=settings["gettextcallback"])

    gobject.timeout_add(1000, self._disconnect)

  def _handlechangedvalue(self, path, value):
    return True  # accept the change

  def _disconnect(self):
    nodata = datetime.datetime.now(datetime.timezone.utc) - self.timestamp
    if nodata > timedelta(seconds=disconnect_timeout):
      self._VeDbus["/Connected"] = 0
    if nodata > timedelta(seconds=null_timeout):
      self._VeDbus["/Ac/Current"] = 0
      self._VeDbus["/Ac/Power"] = 0
      self._VeDbus["/Ac/L{:0}/Power".format(self.phase)] = 0
    return True

  def _update(self, curr, power, totalout, voltage, maxpower, powerlimit):
    try:
      self.timestamp = datetime.datetime.now(datetime.timezone.utc)

      # 7=Running; 8=Standby; 9=Boot loading; 10=Error
      self._VeDbus["/StatusCode"] = 7
      self._VeDbus["/Connected"] = 1
      self._VeDbus["/Ac/Current"] = curr
      self._VeDbus["/Ac/Power"] = power
      self._VeDbus["/Ac/MaxPower"] = maxpower
      self._VeDbus["/Ac/PowerLimit"] = powerlimit
      self._VeDbus["/Ac/Energy/Forward"] = totalout
      self._VeDbus["/Ac/L{:0}/Voltage".format(self.phase)] = voltage
      self._VeDbus["/Ac/L{:0}/Current".format(self.phase)] = curr
      self._VeDbus["/Ac/L{:0}/Power".format(self.phase)] = power
      self._VeDbus["/Ac/L{:0}/Energy/Forward".format(self.phase)] = totalout
      self._VeDbus[path_UpdateIndex] = (self._VeDbus[path_UpdateIndex] + 1) % 256
      return True

    except Exception as e:
        logging.exception(e)
        print(e)


def _newservice(key, deviceinstance, productname, customname, phase, position, ip_address, hardware, firmware):
  global serivices
  servicename = servicenamespace + "." + key

  print("DbusService " + servicename)
  self = DbusService(
    servicename,
    deviceinstance,
    pathsReadOnly={
      "/Mgmt/ProcessName": {"initial": __file__ },
      "/Mgmt/ProcessVersion": {"initial": "Python" },
      "/Mgmt/Connection": {"initial": ip_address + " >-< " + mqttbroker_address},
      "/DeviceInstance": {"initial": deviceinstance},
      "/ProductId": {"initial": productid},
      '/ProductName': {'initial': productname},
      '/CustomName': {'initial': customname},
      "/FirmwareVersion": {"initial": firmware},
      "/HardwareVersion": {"initial": hardware},
      "/Position": {"initial": position},
      "/Show": {"initial": 1}
    },
    pathsReadWrite={
      "/StatusCode": {"initial": 7, "gettextcallback": None },
      "/Connected": {"initial": 0, "gettextcallback": None },
      "/Ac/Current": {"initial": 0, "gettextcallback": lambda p, v: "{:0.2f}A".format(v) },
      "/Ac/Power": {"initial": 0, "gettextcallback": lambda p, v: "{:0.0f}W".format(v) },
      "/Ac/Energy/Forward": {"initial": 0, "gettextcallback": lambda p, v: "{:0.2f}kWh".format(v) },
      "/Ac/MaxPower": {"initial": 0, "gettextcallback": lambda p, v: "{:0.0f}W".format(v) },
      "/Ac/PowerLimit": {"initial": 0, "gettextcallback": lambda p, v: "{:0.0f}W".format(v) },
      "/Ac/L1/Voltage": {"initial": 0, "gettextcallback": lambda p, v: "{:0.0f}V".format(v) },
      "/Ac/L2/Voltage": {"initial": 0, "gettextcallback": lambda p, v: "{:0.0f}V".format(v) },
      "/Ac/L3/Voltage": {"initial": 0, "gettextcallback": lambda p, v: "{:0.0f}V".format(v) },
      "/Ac/L1/Current": {"initial": 0, "gettextcallback": lambda p, v: "{:0.2f}A".format(v) },
      "/Ac/L2/Current": {"initial": 0, "gettextcallback": lambda p, v: "{:0.2f}A".format(v) },
      "/Ac/L3/Current": {"initial": 0, "gettextcallback": lambda p, v: "{:0.2f}A".format(v) },
      "/Ac/L1/Power": {"initial": 0, "gettextcallback": lambda p, v: "{:0.0f}W".format(v) },
      "/Ac/L2/Power": {"initial": 0, "gettextcallback": lambda p, v: "{:0.0f}W".format(v) },
      "/Ac/L3/Power": {"initial": 0, "gettextcallback": lambda p, v: "{:0.0f}W".format(v) },
      "/Ac/L1/Energy/Forward": {"initial": 0, "gettextcallback": lambda p, v: "{:0.2f}kWh".format(v) },
      "/Ac/L2/Energy/Forward": {"initial": 0, "gettextcallback": lambda p, v: "{:0.2f}kWh".format(v) },
      "/Ac/L3/Energy/Forward": {"initial": 0, "gettextcallback": lambda p, v: "{:0.2f}kWh".format(v) },
      path_UpdateIndex: {"initial": 0, "gettextcallback": None }
    })
  self.phase = phase

  print("DbusService " + servicename + " added")
  serivices[key] = self
  return self


def main():
  logging.basicConfig(level=logging.INFO) # use .INFO for less logging
  thread.daemon = True # allow the program to quit
  global serivices 
  serivices = {}

  client = mqtt.Client(mqttclientid)
  client.on_disconnect = on_disconnect
  client.on_connect = on_connect
  client.on_message = on_message
  client.username_pw_set(mqttusername, mqttpassword)
  client.connect(mqttbroker_address)
  client.loop_start()

  from dbus.mainloop.glib import DBusGMainLoop
  DBusGMainLoop(set_as_default=True)
  logging.info(
      "Connected to dbus, and switching over to gobject.MainLoop() (= event based)")

  mainloop = gobject.MainLoop()
  mainloop.run()


if __name__ == "__main__":
  main()