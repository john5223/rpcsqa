name "qa-base"
description "This will create an all-in-one Openstack cluster for RPCS QA Team"
run_list(
  "role[base]",
  "recipe[razor]",
  "recipe[network-interfaces]"
)