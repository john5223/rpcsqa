name "qa-single-api"
description "This will create an OpenStack API server for failover for our RPCSQA environment"
run_list(
  "recipe[network-interfaces]",
  "role[base]"
)