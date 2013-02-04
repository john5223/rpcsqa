name "qa-roush-server"
description "This will create a roush server for the RPCSQA Team"
run_list(
  "recipe[network-interfaces]"
)