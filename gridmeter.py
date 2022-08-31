#!/usr/bin/env python

"""
/data/Pathtothisscript/vedbus.py
/data/Pathtothisscript/ve_utils.py
opkg update && opkg upgrade python3-pip
pip3 install paho-mqtt
"""
##########################################
servicename= 'com.victronenergy.grid.sdm';
customname = 'Powermeter via MQTT' ## name in Venus
deviceinstance = 183 ## vrm nummer
##########################################
path_UpdateIndex = '/UpdateIndex';
null_timeout = 3
# MQTT
mqttbroker_address = 'Homeassistant.local'  # mqtt server
mqttclientid = 'Venus.GridMeter.1'
mqttusername = 'Venus'
mqttpassword = ''
topic = 'venus/powermeter/values'
##########################################

import os
import datetime
from datetime import timedelta
try:
  import gobject  # Python 2.x
except:
  from gi.repository import GLib as gobject # Python 3.x
from array import array
import platform
import logging
import time
import sys
import json
import paho.mqtt.client as mqtt
try:
  import thread   # for daemon = True  / Python 2.x
except:
  import _thread as thread   # for daemon = True  / Python 3.x

# our own packages
sys.path.insert(1, os.path.join(os.path.dirname(__file__), '../ext/velib_python'))
from vedbus import VeDbusService

def on_disconnect(client, userdata, rc):
    print('Client Got Disconnected')
    if rc != 0:
        print('Unexpected MQTT disconnection. Will auto-reconnect')
    else:
        print('rc value:' + str(rc))
    try:
        print('Trying to Reconnect')
        client.connect(mqttbroker_address)
    except Exception as e:
        logging.exception('Fehler beim reconnecten mit Broker')
        print('Error in Retrying to Connect with Broker')
        print(e)

def on_connect(client, userdata, flags, rc):
       if rc == 0:
            print('Connected to MQTT Broker!')
            client.subscribe(topic)
       else:
            print('Failed to connect, return code %d\n', rc)

def on_message(client, userdata, msg):
    try:
        global meter
        jsonpayload = json.loads(msg.payload)
        meter._update(jsonpayload)
    except Exception as e:
        logging.exception(e)
        print(e)

class DbusService:
  timestamp = datetime.datetime.now(datetime.timezone.utc)

  def __init__(self, servicename, deviceinstance, pathsReadOnly, pathsReadWrite):
    self._dbusservice = VeDbusService(servicename)
    gobject.timeout_add(333, self._disconnect)

    logging.debug('%s /DeviceInstance = %d' % (servicename, deviceinstance))

    for path, settings in pathsReadOnly.items():
        self._dbusservice.add_path(path, settings['initial']);

    for path, settings in pathsReadWrite.items():
        self._dbusservice.add_path(path, settings['initial'], writeable=True, 
            onchangecallback=self._handlechangedvalue,
            gettextcallback=settings['gettextcallback']);

  def _disconnect(self):
    nodata = datetime.datetime.now(datetime.timezone.utc) - self.timestamp
    if nodata > timedelta(seconds=null_timeout):
      self._dbusservice['/Connected'] = 0
      self._dbusservice['/Ac/Power'] = None
      self._dbusservice['/Ac/L1/Current'] = None
      self._dbusservice['/Ac/L2/Current'] = None
      self._dbusservice['/Ac/L3/Current'] = None
      self._dbusservice['/Ac/L1/Power'] = None
      self._dbusservice['/Ac/L2/Power'] = None
      self._dbusservice['/Ac/L3/Power'] = None
    return True

  def _update(self, jsonpayload):
    self.timestamp = datetime.datetime.now(datetime.timezone.utc)
    self._dbusservice['/Connected'] = 1
    self._dbusservice['/Ac/Energy/Forward'] = float(jsonpayload['Forward'] or 0)
    self._dbusservice['/Ac/Energy/Reverse'] = float(jsonpayload['Reverse'] or 0)
    self._dbusservice['/Ac/Power'] = float(jsonpayload['Power'] or 0)
    self._dbusservice['/Ac/L1/Voltage'] = float(jsonpayload['L1Voltage'] or 0)
    self._dbusservice['/Ac/L2/Voltage'] = float(jsonpayload['L2Voltage'] or 0)
    self._dbusservice['/Ac/L3/Voltage'] = float(jsonpayload['L3Voltage'] or 0)
    self._dbusservice['/Ac/L1/Current'] = float(jsonpayload['L1Current'] or 0)
    self._dbusservice['/Ac/L2/Current'] = float(jsonpayload['L2Current'] or 0)
    self._dbusservice['/Ac/L3/Current'] = float(jsonpayload['L3Current'] or 0)
    self._dbusservice['/Ac/L1/Power'] = float(jsonpayload['L1Power'] or 0)
    self._dbusservice['/Ac/L2/Power'] = float(jsonpayload['L2Power'] or 0)
    self._dbusservice['/Ac/L3/Power'] = float(jsonpayload['L3Power'] or 0)
    self._dbusservice['/Ac/L1/Energy/Forward'] = float(jsonpayload['L1EnergyForward'] or 0)
    self._dbusservice['/Ac/L1/Energy/Reverse'] = float(jsonpayload['L1EnergyReverse'] or 0)
    self._dbusservice['/Ac/L2/Energy/Forward'] = float(jsonpayload['L2EnergyForward'] or 0)
    self._dbusservice['/Ac/L2/Energy/Reverse'] = float(jsonpayload['L2EnergyReverse'] or 0)
    self._dbusservice['/Ac/L3/Energy/Forward'] = float(jsonpayload['L3EnergyForward'] or 0)
    self._dbusservice['/Ac/L3/Energy/Reverse'] = float(jsonpayload['L3EnergyReverse'] or 0)
    self._dbusservice[path_UpdateIndex] = (self._dbusservice[path_UpdateIndex] + 1) % 256;
    return True

  def _handlechangedvalue(self, path, value):
    return True # accept the change

def main():
  global meter
  logging.basicConfig(level=logging.DEBUG) # use .INFO for less logging
  thread.daemon = True # allow the program to quit

  from dbus.mainloop.glib import DBusGMainLoop
  # Have a mainloop, so we can send/receive asynchronous calls to and from dbus
  DBusGMainLoop(set_as_default=True)
  
  meter = DbusService(
    servicename,
    deviceinstance,
    pathsReadOnly={
      '/Mgmt/ProcessName': {'initial': __file__ },
      '/Mgmt/ProcessVersion': {'initial': 'Python' },
      '/Mgmt/Connection': {'initial': 'MQTT' },
      '/DeviceInstance': {'initial': deviceinstance},
      '/ProductId': {'initial': 45069}, # value used in ac_sensor_bridge.cpp of dbus-cgwacs
      '/ProductName': {'initial': 'PowerMeter'},
      '/CustomName': {'initial': customname},
      '/FirmwareVersion': {'initial': 1},
      '/HardwareVersion': {'initial': 1},
      '/Connected': {'initial': 1}
    },
    pathsReadWrite={
      '/Ac/Energy/Forward': {'initial': 0, 'gettextcallback': lambda p, v: '{:0.1f}kWh'.format(v)},
      '/Ac/Energy/Reverse': {'initial': 0, 'gettextcallback': lambda p, v: '{:0.1f}kWh'.format(v)},
      '/Ac/Power': {'initial': 0, 'gettextcallback': lambda p, v: '{:0.1f}W'.format(v) },
      '/Ac/L1/Voltage': {'initial': 0, 'gettextcallback': lambda p, v: '{:0.1f}V'.format(v) },
      '/Ac/L2/Voltage': {'initial': 0, 'gettextcallback': lambda p, v: '{:0.1f}V'.format(v) },
      '/Ac/L3/Voltage': {'initial': 0, 'gettextcallback': lambda p, v: '{:0.1f}V'.format(v) },
      '/Ac/L1/Current': {'initial': 0, 'gettextcallback': lambda p, v: '{:0.2f}A'.format(v) },
      '/Ac/L2/Current': {'initial': 0, 'gettextcallback': lambda p, v: '{:0.2f}A'.format(v) },
      '/Ac/L3/Current': {'initial': 0, 'gettextcallback': lambda p, v: '{:0.2f}A'.format(v) },
      '/Ac/L1/Power': {'initial': 0, 'gettextcallback': lambda p, v: '{:0.1f}W'.format(v) },
      '/Ac/L2/Power': {'initial': 0, 'gettextcallback': lambda p, v: '{:0.1f}W'.format(v) },
      '/Ac/L3/Power': {'initial': 0, 'gettextcallback': lambda p, v: '{:0.1f}W'.format(v) },
      '/Ac/L1/Energy/Forward': {'initial': 0, 'gettextcallback': lambda p, v: '{:0.1f}W'.format(v)},
      '/Ac/L1/Energy/Reverse': {'initial': 0, 'gettextcallback': lambda p, v: '{:0.1f}W'.format(v) },
      '/Ac/L2/Energy/Forward': {'initial': 0, 'gettextcallback': lambda p, v: '{:0.1f}W'.format(v) },
      '/Ac/L2/Energy/Reverse': {'initial': 0, 'gettextcallback': lambda p, v: '{:0.1f}W'.format(v)},
      '/Ac/L3/Energy/Forward': {'initial': 0, 'gettextcallback': lambda p, v: '{:0.1f}W'.format(v) },
      '/Ac/L3/Energy/Reverse': {'initial': 0, 'gettextcallback': lambda p, v: '{:0.1f}W'.format(v)},
      '/ErrorCode': {'initial': 0, 'gettextcallback': None},
      path_UpdateIndex: {'initial': 0, 'gettextcallback': None }
    })

  client = mqtt.Client(mqttclientid)
  client.on_disconnect = on_disconnect
  client.on_connect = on_connect
  client.on_message = on_message
  client.username_pw_set(mqttusername, mqttpassword)
  client.connect(mqttbroker_address)
  client.loop_start()

  logging.info(
      'Connected to dbus, and switching over to gobject.MainLoop() (= event based)')
  mainloop = gobject.MainLoop()
  mainloop.run()

if __name__ == '__main__':
  main()
