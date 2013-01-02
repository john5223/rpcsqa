#!/bin/bash

###################################################################################
## This is a script that is run locally to prepare a server for installing alamo ##
## Author : Solomon Wagner                                                       ##
################################################################################### 

#check to make sure user can be root
if [ `whoami` != "root" ]; then
    echo "Can only run script as root"; exit;
fi

# Image URLS
# Might make the parameters in the future
CIRROS_IMAGE_NAME="cirros-0.3.0-x86_64-uec.tar.gz"
CIRROS_URL="https://launchpadlibrarian.net/83305869/${CIRROS_IMAGE_NAME}"
PRECISE_IMAGE_NAME="precise-server-cloudimg-amd64.tar.gz"
PRECISE_URL="http://cloud-images.ubuntu.com/precise/current/${PRECISE_IMAGE_NAME}"
CHEF_IMAGE_NAME="chef-server.qcow2"
CHEF_IMAGE_HOST=${CHEF_IMAGE_HOST:-c390813.r13.cf1.rackcdn.com}
CHEF_IMAGE_URL="http://${CHEF_IMAGE_HOST}/${CHEF_IMAGE_NAME}"

# Our File Server URLS
FILE_SERVER_URL="http://198.61.203.76/alamo"
POST_INSTALL_LOCATION="post-install.sh"
FUNCTIONS_LOCATION="functions.sh"
RPCS_CFG_LOCATION="${HOSTNAME}-rpcs.cfg"

echo "Installing Ubuntu Packages needed to run alamo..."
apt-get update
apt-get install -y openssh-server build-essential libvirt-bin qemu-kvm sshpass pwgen dialog curl
echo "...Done"

echo "Updating packages..."
apt-get update
apt-get -y upgrade
echo "...Done"

## CREATE NEEDED DIRECTORIES
# make the /opt/rpcs directory and move into it
echo "Making /opt/rpcs directory..."
mkdir -p /opt/rpcs
echo "...Done"

echo "Moving post-install.sh to /opt/rpcs..."
mv ./post-install.sh /opt/rpcs 
echo "...Done"

echo "Moving functions.sh to /opt/rpcs..."
mv ./functions.sh /opt/rpcs 
echo "...Done"

echo "Moving status.sh to /opt/rpcs..."
mv ./status.sh /opt/rpcs 
echo "...Done"

echo "Moving status.rb to /opt/rpcs..."
mv ./status.rb /opt/rpcs 
echo "...Done"

echo "Moving late_command.sh to /opt/rpcs..."
mv ./late_command.sh /opt/rpcs 
echo "...Done"

#Get ip address for eth0 (hopefully public ip)
ip=`ifconfig eth0 | grep 'inet addr:' | cut -d: -f2 | awk '{ print $1}'`
echo "eth0 ip address: $ip"

echo "Copying $ip-rpcs.cfg to rpcs.cfg..."
cp ./$ip-rpcs.cfg rpcs.cfg
echo "...Done"

echo "Moving rpcs.cfg into /opt/rpcs directory..."
mv ./rpcs.cfg /opt/rpcs
echo "...Done"

# Download the chef-server image	  	
if [ `ls /opt/rpcs | grep ${CHEF_IMAGE_NAME}` = $CHEF_IMAGE_NAME ] || [ `ls | grep ${CHEF_IMAGE_NAME}` = $CHEF_IMAGE_NAME ]; then  	
	echo "${CHEF_IMAGE_NAME} already downloaded"	  	
else
	echo "Downloading ${CHEF_IMAGE_NAME}..."
	# I need to figure out how to get the chef-server.qcow2 onto the box via a host inside the rack
	echo "...Done"
fi

if [ ! -e /opt/rpcs/chef-server.qcow2 ]; then
	echo "Copying ${CHEF_IMAGE_NAME} into /opt/rpcs"
	cp ./${CHEF_IMAGE_NAME} /opt/rpcs
fi

echo "Move into /opt/rpcs"
cd /opt/rpcs
pwd
echo "...Done"

# Get the hostname of the server
echo "HOSTNAME : ${HOSTNAME}"

# Download the cirros image
if [ `ls | grep ${CIRROS_IMAGE_NAME}` = $CIRROS_IMAGE_NAME ]; then
	echo "${CIRROS_IMAGE_NAME} already downloaded"
else
	echo "Downloading ${CIRROS_IMAGE_NAME}..."
	wget ${CIRROS_URL}
	echo "...Done"
fi

# Chmod the Cirros Image gz to be executable
echo "Chmoding 0755 ${CIRROS_IMAGE_NAME}..."
chmod 0755 ${CIRROS_IMAGE_NAME}
echo "...Done"

echo 
# Download the precise image
if [ `ls | grep ${PRECISE_IMAGE_NAME}` = $PRECISE_IMAGE_NAME ]; then
	echo "${PRECISE_IMAGE_NAME} already downloaded"
else
	echo "Downloading ${PRECISE_IMAGE_NAME}..."
	wget ${PRECISE_URL}
	echo "...Done"
fi

# Chmod the Precise Image gz to be executable
echo "Chmoding 0755 ${PRECISE_IMAGE_NAME}..."
chmod 0755 ${PRECISE_IMAGE_NAME}
echo "...Done"

# Chmod the chef-server image to be executable
echo "Chmoding 0755 ${CHEF_IMAGE_NAME}..."
chmod 0755 ${CHEF_IMAGE_NAME}
echo "...Done"

# creating a chef-server.qcow2.pristine file to make the post-install.sh ignore the wget
echo "Touching fake chef-server.qcow2.pristine file..."
touch chef-server.qcow2.pristine
echo "...Done"

# Once we have all we need, run the post-install.sh script
echo "CHMODing post-install.sh..."
chmod 0755 post-install.sh
echo "...Done"