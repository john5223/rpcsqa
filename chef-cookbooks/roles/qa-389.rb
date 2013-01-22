name "qa-389"
description "This will create an 389 ldap server for RPCS QA Team"
run_list(
  #"role[qa-base]",
  #"recipe[network-interfaces]",
  "recipe[389::server]"
)
default_attributes(  { "389" => {
                            "rootpw" => "{SSHA}gqx00u6a46YT0zsIC9nQVy2yyHfNjJmO", 
                            "basedn" => "dc=dev,dc=rcbops,dc=me",
                            "server" => "ldap.rcbops",
                            "auth_bindpw" => "{SSHA}gqx00u6a46YT0zsIC9nQVy2yyHfNjJmO",
                            "slapd_type" => "master"
                            }   
                      }
                  )
