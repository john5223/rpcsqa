name "qa-single-controller"
description "This will create an OpenStack controller for RPCS QA Team"
run_list(
  "recipe[network-interfaces]",
  "role[single-controller]"
)