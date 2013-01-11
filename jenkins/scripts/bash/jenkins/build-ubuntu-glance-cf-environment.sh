#!/bin/bash

# print usage and exit
if [ "$#" -eq 0 ]; then
  echo "Usage: build-ubuntu-glance-cf-environment.sh [-h help] -i tenant_id -n tenant_name -p tenant_password" >&2
  exit
fi

# Get the root password from the box off the command line
while getopts "i:n:p:h" OPTION;
do
  case $OPTION in
    i) TENANT_ID=$OPTARG
       ;;
    n) TENANT_NAME=$OPTARG
       ;;
    p) TENANT_PASSWORD=$OPTARG
       ;;
    h) echo "Usage: nmap_reboot.sh [-h]" >&2
       echo " -h Return this help information" >&2
       echo " -r The root password for the boxes to be rebooted" >&2
       echo " -p The razor policy to run chef-client against" >&2
       exit
       ;;
  esac
done

template_filename='/var/lib/jenkins/rpcsqa/chef-cookbooks/environments/templates/ubuntu-glance-cf.json'
environment_filename='/var/lib/jenkins/rpcsqa/chef-cookbooks/environments/ubuntu-glance-cf.json'
filelines=`cat $filename`

## copy the environment file to the proper directory
echo "Copying template to environment..."
cp $template_filename $environment_filename

## replace the lines we are looking for
echo "Replacing template values with real values..."
sed -i 's/<TENANT_ID>/$TENANT_ID/g' $environment_filename
sed -i 's/<TENANT_NAME>/$TENANT_NAME/g' $environment_filename
sed -i 's/<TENANT_PASSWORD>/$TENANT_PASSWORD/g' $environment_filename

echo "Done..."