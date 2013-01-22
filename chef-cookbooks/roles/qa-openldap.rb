name "qa-openldap"
description "This will create an openldap server for RPCS QA Team"
run_list(
  "recipe[razor]",
  "recipe[network-interfaces]",
  "recipe[openldap::server]"
)
default_attributes(  { "openldap" => {
                            "rootpw" => "{SSHA}gqx00u6a46YT0zsIC9nQVy2yyHfNjJmO", 
                            "basedn" => "dc=dev,dc=rcbops,dc=me",
                            "server" => "ldap.rcbops",
                            "auth_bindpw" => "{SSHA}gqx00u6a46YT0zsIC9nQVy2yyHfNjJmO",
                            "slapd_type" => "master"
                            }   
                      }
                  )
