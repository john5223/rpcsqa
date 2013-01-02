Usage
=====

In the node attributes, populate the network_interfaces attribute (node['network_interfaces']. Give them these attributes:

:auto => iface['auto'] || true,
:type => iface['type'] || "static",
:device => iface['device'],
:netmask => iface['netmask'],
:address => iface['address']

Here's an example

"normal": {
    "network_interfaces": [
		{
    		"auto": "true",
    		"type": "static",
    		"device": "eth0",
    		"netmask": "255.255.255.0",
    		"address": "192.168.10.10"
		},
		{
    		"auto": "true",
    		"type": "static",
    		"device": "eth1",
    		"netmask: "255.255.255.0",
    		"address": "10.0.0.2"
		}
    ]
}
