#!/bin/bash

# Set temp file and perm file
template_filename='/var/lib/jenkins/rpcsqa/chef-cookbooks/environments/templates/ubuntu-opencenter.json'
environment_filename='/var/lib/jenkins/rpcsqa/chef-cookbooks/environments/ubuntu-opencenter.json'

## copy the environment file to the proper directory
echo "Copying template to environment..."
cp $template_filename $environment_filename

echo "Set Knife Environment..."
knife environment from file $environment_filename

echo "Done..."