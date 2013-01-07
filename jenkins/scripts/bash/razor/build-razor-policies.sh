#!/bin/bash

# If you want to add more os's and features all you have to do is add them to the appropriate arrays
os=("ubuntu")
# Removed until I can get the broker plugin working for centos
#"centos")
feature=("glance-cf" "keystone-ldap" "keystone-389" "nova-quantum")
declare -A model_uuid=( ["ubuntu-glance-cf"]="3kinbHYZ0jLby70DtRPgaa" ["ubuntu-keystone-ldap"]="5dY7YurK5QtGwNpfJckjBU" ["ubuntu-keystone-389"]="6R2zOpT41PfD2fZKs6NdBU" ["ubuntu-nova-quantum"]="6zclclFls4hWxJkWkWRmm4")

# Remove until IU can get the broker plugin working for centos
#["centos-glance-cf"]="7Y3PmB1kNrJoOyV7d790wu" ["centos-keystone-ldap"]="QqoAI6FvGcgwryBdyE7lU" ["centos-keystone-389"]="oD5YleUNeKS33kYXIdl7M" ["centos-nova-quantum"]="1FANBOSvaWaimtz7UVoVYq")

declare -A broker_uuid=( ["chef"]="1mEjanA4Siow2Z8bUe64OS" )

for o in "${os[@]}"; do
	for f in "${feature[@]}"; do
		razor policy add -p linux_deploy -l $o-$f -m ${model_uuid[$o-$f]} -b ${broker_uuid[chef]} -t cpus_12,memsize_24GiB -e true -x 4
	done
done