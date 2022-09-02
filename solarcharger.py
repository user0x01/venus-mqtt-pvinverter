#!/usr/bin/env python

"""
/data/Pathtothisscript/vedbus.py
/data/Pathtothisscript/ve_utils.py
python -m ensurepip --upgrade
pip install paho-mqtt
"""

"""

"""

import dbus.service
import dbus
from vedbus import VeDbusService
from datetime import timedelta
import datetime

#################################################
servicenamespace = "com.victronenergy.solarcharger"
productid = 1300
path_UpdateIndex = "/UpdateIndex"
disconnect_timeout = 60 
null_timeout = 10
# MQTT
mqttbroker_address = "Homeassistant.local" ## mqtt server
mqttclientid = "Venus.solarcharger"
mqttusername = "Venus"
mqttpassword = ""
topics = "venus/solarcharger/#"  # Topicsfilter
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
            ip_address = jsonpayload["ip_address"]
            _newservice(key, deviceinstance, productname,
              customname, 0, 0, ip_address, hardware, firmware)

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
            state = 5 # jsonpayload["state"]
            loadcurrent = float(jsonpayload["loadcurrent"])
            pvvoltage = float(jsonpayload["pvvoltage"])
            pvpower = float(jsonpayload["pvpower"])
            dcvoltage = float(jsonpayload["dcvoltage"])
            dcpower = float(jsonpayload["dcpower"])
            yielduser = float(jsonpayload["yielduser"])
            yieldsystem = float(jsonpayload["yieldsystem"])
            serivice._update(state, loadcurrent, pvvoltage,
                             pvpower, dcvoltage, dcpower, yielduser, yieldsystem)

    except Exception as e:
        logging.exception(e)
        print(e)


class DbusService:
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
      self._VeDbus["/Mode"] = 4
    if nodata > timedelta(seconds=null_timeout):
      self._VeDbus["/State"] = 0
      self._VeDbus["/Dc/0/Voltage"] = None
      self._VeDbus["/Dc/0/Current"] = None
      self._VeDbus["/Load/State"] = None
      self._VeDbus["/Pv/V"] = None
      self._VeDbus["/Yield/Power"] = None

    return True

  def _update(self, state, loadcurrent, pvvoltage,
    pvpower, dcvoltage, dcpower, yielduser, yieldsystem):
    try:
      self.timestamp = datetime.datetime.now(datetime.timezone.utc)

      self._VeDbus["/Connected"] = 1
      self._VeDbus["/Mode"] = 1 if (loadcurrent > 0) else 4
      self._VeDbus["/State"] = state
      self._VeDbus["/Load/I"] = loadcurrent
      self._VeDbus["/Load/State"] = 1 if (loadcurrent > 0) else 0
      self._VeDbus["/Pv/V"] = pvvoltage
      self._VeDbus["/Yield/Power"] = pvpower
      self._VeDbus["/Dc/0/Voltage"]=dcvoltage
      self._VeDbus["/Dc/0/Current"]=dcpower
      self._VeDbus["/Yield/User"]= yielduser
      self._VeDbus["/Yield/System"] = yieldsystem
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
        "/Show": {"initial": 1},
        "/NrOfTrackers": {"initial": 1}
    },
    pathsReadWrite={
        "/MppOperationMode": {"initial": 2, "gettextcallback": None},
        "/DeviceOffReason": {"initial": 0, "gettextcallback": None},
        "/State": {"initial": 3, "gettextcallback": None},
        "/StatusCode": {"initial": 7, "gettextcallback": None },
        "/Connected": {"initial": 0, "gettextcallback": None },
        "/Mode": {"initial": 4, "gettextcallback": None},

        "/Settings/BmsPresent": {"initial": 0, "gettextcallback": None},
        "/Settings/ChargeCurrentLimit": {"initial": 0, "gettextcallback": lambda p, v: "{: 0.2f}A".format(v)},

        "/Link/NetworkMode": {"initial": 0, "gettextcallback": None},
        "/Link/BatteryCurrent": {"initial": 0, "gettextcallback": lambda p, v: "{:0.2f}A".format(v)},
        "/Link/ChargeCurrent": {"initial": 0, "gettextcallback": lambda p, v: "{: 0.2f}A".format(v)},
        "/Link/ChargeVoltage": {"initial": 0, "gettextcallback": lambda p, v: "{: 0.2f}V".format(v)},
        "/Link/NetworkStatus": {"initial": 0, "gettextcallback": None},
        "/Link/TemperatureSense": {"initial": 0, "gettextcallback": lambda p, v: "{: 0.0f}°C".format(v)},
        "/Link/TemperatureSenseActive": {"initial": 0, "gettextcallback": None},
        "/Link/VoltageSense": {"initial": 0, "gettextcallback": lambda p, v: "{: 0.2f}A".format(v)},
        "/Link/VoltageSenseActive": {"initial": 0, "gettextcallback": None},

        "/Pv/V": {"initial": 0, "gettextcallback": lambda p, v: "{:0.1f}V".format(v)},
        "/Yield/Power": {"initial": 0, "gettextcallback": lambda p, v: "{:0.0f}W".format(v)},
        "/Dc/0/Voltage": {"initial": 0, "gettextcallback": lambda p, v: "{:0.2f}V".format(v)},
        "/Dc/0/Current": {"initial": 0, "gettextcallback": lambda p, v: "{:0.2f}A".format(v)},
        "/Yield/User": {"initial": 0, "gettextcallback": lambda p, v: "{:0.2f}kWh".format(v)},
        "/Yield/System": {"initial": 0, "gettextcallback": lambda p, v: "{:0.2f}kWh".format(v)},
        "/Load/State": {"initial": 0, "gettextcallback": None},
        "/Load/I": {"initial": 0, "gettextcallback": lambda p, v: "{:0.2f}A".format(v)},
        "/ErrorCode": {"initial": 0, "gettextcallback": None},
        path_UpdateIndex: {"initial": 0, "gettextcallback": None}
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