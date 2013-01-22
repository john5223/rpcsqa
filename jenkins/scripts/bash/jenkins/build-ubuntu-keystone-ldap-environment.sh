#!/bin/bash

# Source the file that has our environment variables
#source ~/source_files/CLOUD_FILES_AUTH.sh

template_filename='/var/lib/jenkins/rpcsqa/chef-cookbooks/environments/templates/ubuntu-keystone-ldap.json'
environment_filename='/var/lib/jenkins/rpcsqa/chef-cookbooks/environments/ubuntu-keystone-ldap.json'
filelines=`cat $filename`

## copy the environment file to the proper directory
echo "Copying template to environment..."
cp $template_filename $environment_filename

echo "Set Knife Environment..."
knife environment from file $environment_filename

echo "Done..."