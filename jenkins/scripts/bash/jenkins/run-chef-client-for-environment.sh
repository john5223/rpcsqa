#/bin/bash

# Run all chef-clients for a environment

CHEF_ENVIRONMENT="ubuntu-glance-cf"

for i in `knife search node "chef_environment:${CHEF_ENVIRONMENT}" | grep IP | awk '{print $2}'`; do sshpass -p aGo0hItAbeneO9NiaHsMi3FraoMtU2Hy ssh -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -o LogLevel=quiet -l root $i 'chef-client'; done;
