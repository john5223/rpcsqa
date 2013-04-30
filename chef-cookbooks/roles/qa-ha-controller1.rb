name "qa-ha-controller1"
description "This will create an OpenStack ha-controller1 for RPCS QA Team"
run_list(
  "recipe[network-interfaces]",
  "role[ha-controller1]"
)