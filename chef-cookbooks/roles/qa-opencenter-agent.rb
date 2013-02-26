name "qa-opencenter-agent"
description "This will create a opencenter agent for the RPCSQA Team"
run_list(
  "recipe[network-interfaces]"
)