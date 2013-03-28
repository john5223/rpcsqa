name "qa-ha-controller2"
description "This will create an OpenStack ha-controller2 for RPCS QA Team"
run_list(
  "recipe[network-interfaces]",
  "role[ha-controller2]"
)