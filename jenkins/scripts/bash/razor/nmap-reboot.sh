#!/bin/bash

# print usage and exit
if [ "$#" -eq 0 ]; then
        echo "Usage: namp_reboot.sh -p root_pass" >&2
        exit
fi

# Get the root password from the box off the command line
while getopts "p:h" OPTION;
do
        case $OPTION in
                p) ROOT_PASS=$OPTARG
                   ;;
                h) echo "Usage: nmap_reboot.sh [-h]" >&2
                   echo " -h Return this help information" >&2
                   echo " -p The root password for the boxes to be rebooted" >&2
                   exit
                   ;;
        esac
done

# Run nmap to get the boxes that are alive
results=`nmap -sP -oG alive 10.0.0.0/24 | grep 10.0.0.* | awk '{print $5 $6}'`

# Loop through the alive boxes, grab the ip and then reboot them
for item in ${results}
do
        if [[ $item =~ '10.0.0.' ]]; then
                ip=`echo "$item" | grep -o '[0-9]\{1,3\}\.[0-9]\{1,3\}\.[0-9]\{1,3\}\.[0-9]\{1,3\}'`
                echo $ip
                if [[ $ip == '10.0.0.1' ]]; then
                        echo "This box is restricted infrastructure, ignore it."
                else
                        echo "Rebooting machine with ip $ip"
                        sshpass -p $ROOT_PASS ssh -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -o LogLevel=quiet -l root $ip 'reboot'
                fi
        fi
done
