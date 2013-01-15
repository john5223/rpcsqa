#!/bin/bash

# If you want to add more os's and features all you have to do is add them to the appropriate arrays
os=("ubuntu" "centos")
feature=("glance-cf" "keystone-ldap" "keystone-389" "nova-quantum")
declare -A image_uuid=( ["ubuntu"]="3bh7YoX4GT7kRFSgagRPm0" ["centos"]="4BW18Km4hWz7UHcNmV4kZA")
declare -A model_templates=( ["ubuntu"]="ubuntu_precise" ["centos"]="centos_6")

for o in "${os[@]}"; do
    for f in "${feature[@]}"; do
        echo "razor model add -t ${model_templates[$o]} -l $o-$f -i ${image_uuid[$o]}"
    done
done