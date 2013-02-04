name "qa-389-ubuntu"
description "This will create an 389 ldap server for RPCS QA Team"
run_list(
  "recipe[network-interfaces]",
  "recipe[yum::epel]",
  "recipe[389::server]"
)
default_attributes(  { "389" => {
                            "rootpw" => "{SSHA}gqx00u6a46YT0zsIC9nQVy2yyHfNjJmO", 
                            "basedn" => "dc=dev,dc=rcbops,dc=me"
                            }   
                      }
                  )
