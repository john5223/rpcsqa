#!/bin/bash

# If you want to add more os's and features all you have to do is add them to the appropriate arrays
os=("ubuntu" "centos")
feature=("glance-cf" "geystone-ldap" "keystone-389" "nova-quantum")
declare -A model_uuid=( ["ubuntu"]="3MVWfA3EruPw3g2OhjR0oO" ["centos"]="1A5ps918A6yxoCvqDfXl6q")
declare -A broker_uuid=( ["chef"]="69wqOa08K9ujByMhPYe2Lk" )

for o in "${os[@]}"; do
	for f in "${feature[@]}"; do
		echo "razor policy add -p linux_deploy -l $o-$f -m ${model_uuid[$o]} -b ${broker_uuid[chef]} -t cpus_12,memsize_24GiB -e true -x 4"
	done
done