name "qa-openldap"
description "This will create an openldap server for RPCS QA Team"
run_list(
  "role[qa-base]",
  "recipe[openldap::server]"
)