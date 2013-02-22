name "qa-opencenter-server"
description "This will create a opencenter server for the RPCSQA Team"
run_list(
  "recipe[network-interfaces]"
)