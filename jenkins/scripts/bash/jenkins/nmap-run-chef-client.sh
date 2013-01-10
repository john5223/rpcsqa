#!/bin/bash

# print usage and exit
if [ "$#" -eq 0 ]; then
  echo "Usage: nmap-run-chef-client.sh -p root_pass" >&2
  exit
fi

# Get the root password from the box off the command line
while getopts "p:h" OPTION;
do
  case $OPTION in
    r) ROOT_PASS=$OPTARG
       ;;
    p) POLICY=$OPTARG
       ;;
    h) echo "Usage: nmap_reboot.sh [-h]" >&2
       echo " -h Return this help information" >&2
       echo " -r The root password for the boxes to be rebooted" >&2
       echo " -p The razor policy to run chef-client against"
       exit
       ;; 
  esac
done

# Run nmap to get the boxes that are alive
nmap_results=`nmap -sP -oG alive 10.0.0.0/24 | grep 10.0.0.* | awk '{print $5 $6}'`

# Loop through the alive boxes, grab the ip and then reboot them
i=0
for nmap_ip in ${nmap_results}
do
  if [[ $nmap_ip =~ '10.0.0.' ]]; then
    ip=`echo "$nmap_ip" | grep -o '[0-9]\{1,3\}\.[0-9]\{1,3\}\.[0-9]\{1,3\}\.[0-9]\{1,3\}'`
    if [[ $ip == '10.0.0.1' || $ip == '10.0.0.2' || $ip == '10.0.0.3' ]]; then
      echo "This box is restricted infrastructure, ignore it."
    else
      echo "Running hostname --fqdn on server with ip $ip"
      hostname_result=`sshpass -p $ROOT_PASS ssh -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -o LogLevel=quiet -l root $ip 'hostname -fqdn'`
      if [[ $hostname_result=~$POLICY ]]; then
        echo "Found host that matched policy, $hostname_result with IP: $ip"
        chef_ips[$i]=$ip
      fi
    fi
  fi
done

for ip in $chef_ips
do
  echo "Running chef client on IP: $ip"
  #sshpass -p $ROOT_PASS ssh -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -o LogLevel=quiet -l root $ip 'chef-client'
done