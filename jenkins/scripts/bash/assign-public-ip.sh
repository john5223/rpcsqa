#!/bin/bash

###########################################################################################
## 	This script will log into a box via the private network and assign it a public ip	 ##
##	It will also unbind the private interface from DHCP (if it is there).				 ##
##	It will then restart networking service and ping www.google.com						 ##
##	Author: Solomon J Wagner															 ##
###########################################################################################

if [ "$#" -eq 0 ]; then
	echo "Usage: assign_public_ip.sh [-h help] -s node_ip -u node_username -p node_password -i node_public_ip -n node_public_netmask -g node_public_gateway -b broadcast_network -d dns_server" >&2
	exit
fi

while getopts "s:u:p:i:n:g:b:d:h" OPTION;
do
	case $OPTION in
		s)	NODE_PRIVATE_IP=$OPTARG
			;;
		u)	NODE_USERNAME=$OPTARG
			;;
		p)	NODE_USER_PASSWD=$OPTARG
			;;
		i)	NODE_PUBLIC_IP=$OPTARG
			;;
		n)	NODE_PUBLIC_NETMASK=$OPTARG
			;;
		g)	NODE_PUBLIC_GATEWAY=$OPTARG
			;;
		b)	NODE_BROADCAST_NETWORK=$OPTARG
			;;
		d)	NODE_DNS_SERVER=$OPTARG
			;;
		h)	echo "Usage: assign_public_ip.sh [-h]" >&2
			echo "	-h   Return this help information" >&2
			echo "	-s   The private IP of the server to run this script remotely on. REQUIRED" >&2
			echo "	-u   The username to run the script as. REQUIRED" >&2
			echo "	-p   The password of the user. REQUIRED" >&2
			echo "	-i   The public ip to assign to the server. REQUIRED" >&2
			echo "	-n   The public netmask to assign to the server. REQUIRED" >&2
			echo "	-g   The public gateway to assign to the server. REQUIRED" >&2
			echo "	-b   The broadcast network to assign to the server. REQUIRED" >&2
			echo "	-d   The dns server to assign to the server. REQUIRED" >&2
			exit
			;;
	esac
done

NODE_NETWORK=`echo $NODE_PUBLIC_IP | sed 's/\([0-9]\{1,3\}\.[0-9]\{1,3\}\.[0-9]\{1,3\}\)\.[0-9]\{1,3\}/\1.0/'`

echo "Writing temporary interfaces file.."
# Build a tmp file for what we want the interfaces file to look like
cat > $NODE_PUBLIC_IP-interfaces << EOF
auto eth0
iface eth0 inet static
	address $NODE_PUBLIC_IP
	netmask $NODE_PUBLIC_NETMASK
	#network $NODE_NETWORK
	#broadcast $NODE_BROADCAST_NETWORK
	gateway $NODE_PUBLIC_GATEWAY
	dns-nameservers $NODE_DNS_SERVER
	dns-search rcb.rackspace.com

auto eth1
iface eth1 inet dhcp
EOF

#-o "UserKnownHostsFile /dev/null"

# pass the tmp interfaces file onto the host
echo "Remoting into the server and setting the interfaces file..."
sshpass -p $NODE_USER_PASSWD scp -o "StrictHostKeyChecking no" $NODE_PUBLIC_IP-interfaces $NODE_USERNAME@$NODE_PRIVATE_IP:/etc/network/interfaces

# remove the tmp-interfaces file
echo "Removing the temporary interfaces file..."
rm $NODE_PUBLIC_IP-interfaces

echo "Restarting Networking"
sshpass -p $NODE_USER_PASSWD ssh -o "StrictHostKeyChecking no" $NODE_USERNAME@$NODE_PRIVATE_IP 'service networking restart'

echo "Adding Gateway for eth0"
sshpass -p $NODE_USER_PASSWD ssh -o "StrictHostKeyChecking no" $NODE_USERNAME@$NODE_PRIVATE_IP 'route add default gw 198.101.133.1 dev eth0'
