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


## References

Victronenergy
* https://github.com/victronenergy/velib_python
* https://github.com/victronenergy/venus/wiki/dbus

Soyosource from Syssi 
* https://github.com/syssi/esphome-soyosource-gtn-virtual-meter





