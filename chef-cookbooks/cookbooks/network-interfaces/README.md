Usage
=====

In the node attributes, populate the network_interfaces attribute (node['network_interfaces']. Give them these attributes:

Debian based distros:
=====================

:auto => iface['auto'] || true,
:type => iface['type'] || "static",
:device => iface['device'],
:netmask => iface['netmask'],
:address => iface['address']


RedHat based distros:
=====================

:onboot => iface['onboot'] || yes
:bootproto => iface['bootproto'] || none
:device => iface['device']
:ipaddr => iface['ipaddr']
:gateway => iface['gateway']
:netmask => iface['netmask']
:userctl => iface['userctl'] || no


You can give each node both, the recipe will pick the appropriate array based on ditribution.

Here's an example:
==================

"network_interfaces": {
    "debian": [
        {
            "auto": "true", 
            "netmask": "255.255.255.0", 
            "address": "198.101.133.240", 
            "device": "eth0", 
            "type": "static", 
            "gateway": "198.101.133.1"
        }
    ], 
    "redhat": [
        {
            "userctl": "no", 
            "ipaddr": "198.101.133.240", 
            "gateway": "198.101.133.1", 
            "netmask": "255.255.255.0", 
            "bootproto": "none", 
            "device": "em1", 
            "onboot": "yes"
        }
    ]
}
