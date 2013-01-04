#!/bin/bash

# print usage and exit
if [ "$#" -eq 0 ]; then
        echo "Usage: ping_reboot_all.sh -p root_pass" >&2
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

# ping all ips in range and reboot the good ones
for i in {4..254}
do
        ip=10.0.0.$i
        results=`ping -c 2 10.0.0.$i`
        echo -e "\n!!## -- PING RESULTS FOR IP: $ip, with len(results): ${#results}-- ##!!"
        echo $results

        if [[ ${#results} > 300 ]]; then
                echo "!!## -- Rebooting box with ip: $ip -- ##!!"
                sshpass -p $ROOT_PASS ssh -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -l root $ip 'reboot'
        else
                echo "!!## -- Nothing @ $ip to reboot -- ##!!"
        fi
done