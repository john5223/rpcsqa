name "qa-single-compute"
description "This will create an OpenStack compute for RPCS QA Team"
run_list(
  "recipe[razor]",
  "role[single-compute]"
)