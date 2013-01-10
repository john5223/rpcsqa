name "qa-base"
description "This will create an all-in-one Openstack cluster for RPCS QA Team"
run_list(
  "recipe[razor]"
)