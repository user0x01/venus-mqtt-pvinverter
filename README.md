# venus-mqtt-pvinverter
connect pvinverter to victron gx via mqtt

# Example topic for create inverter:
```
venus/pvinverter/soyosource1/init
{
  "key": "soyosource1",
  "productname": "Soyosource GTN 1200G48",
  "customname": "Soyo GTN1200 1",
  "deviceinstance": 184,
  "ip_address": "192.168.66.81",
  "phase": 1,
  "position": 1,
  "timestamp": 1658265588
}
```

# Example topic for values:
```
venus/pvinverter/soyosource1/values
{
  "key": "soyosource1",
  "voltage": 234,
  "power": 336.6121,
  "energy": 55.1,
  "maxpower": 600,
  "powerlimit": 340,
  "timestamp": 1658265809
}
```

# venus-mqtt-gridmeter
connect gridmeter to victron gx via mqtt
# Example topic for values:
```
venus/powermeter/values
{
  "Reverse": 132,
  "Forward": 142,
  "Power": 12,
  "L1Voltage": 12,
  "L2Voltage": 12,
  "L3Voltage": 227.3126,
  "L1Current": 12,
  "L2Current": 12,
  "L3Current": 0,
  "L1Power": 12,
  "L2Power": 12,
  "L3Power": 0,
  "L1EnergyForward": 12,
  "L1EnergyReverse": 12,
  "L2EnergyForward": 12,
  "L2EnergyReverse": 12,
  "L3EnergyForward": 12,
  "L3EnergyReverse": 12,
  "timestamp": 1661893778
}
```

## installation
please refer:
https://github.com/RalfZim/venus.dbus-fronius-smartmeter#installation

plus load paho-mqtt on venus os
```
python -m ensurepip --upgrade
pip install paho-mqtt
```

edit mqttsettings in the Pythonfile
# MQTT
mqttbroker_address = "Homeassistant.local" ## mqtt server
mqttclientid = "Venus.pvinverter"
mqttusername = "Venus"
mqttpassword = ""
topics = "venus/pvinverter/#"  # Topicsfilter
topic_init = "/init"  # Topic constructor
topic_values = "/values"  # Topic values
topic_close = "/close"  # Topic

start ../service/run
or reboot 


## References

Victronenergy
* https://github.com/victronenergy/velib_python
* https://github.com/victronenergy/venus/wiki/dbus

Soyosource from Syssi 
* https://github.com/syssi/esphome-soyosource-gtn-virtual-meter





