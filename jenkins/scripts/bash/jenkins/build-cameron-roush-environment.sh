#!/bin/bash

# Set temp file and perm file
template_filename='/var/lib/jenkins/rpcsqa/chef-cookbooks/environments/templates/cameron-roush.json'
environment_filename='/var/lib/jenkins/rpcsqa/chef-cookbooks/environments/cameron-roush.json'

## copy the environment file to the proper directory
echo "Copying template to environment..."
cp $template_filename $environment_filename

echo "Set Knife Environment..."
knife environment from file $environment_filename

echo "Done..."