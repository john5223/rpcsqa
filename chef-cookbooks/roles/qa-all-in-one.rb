name "qa-all-in-one"
description "This will create an all-in-one Openstack cluster for RPCS QA Team"
run_list(
  "role[qa-base]",
  "role[single-controller]",
  "role[single-compute]"
)