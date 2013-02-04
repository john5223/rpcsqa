name "qa-openldap-centos"
description "This will create an openldap server for RPCS QA Team"
run_list(
  "recipe[network-interfaces]",
  "recipe[yum::yum]",
  "recipe[yum::epel]",
  "recipe[openssh]",
  "recipe[openldap::server]"         
)
default_attributes(  { "openldap" => {
                            "rootpw" => "{SSHA}rcZMditrBFedx2lGWSVjMUnWLLz+kEjV", 
                            "basedn" => "dc=dev,dc=rcbops,dc=me",
                            "server" => "ldap.rcbops",
                            "auth_bindpw" => "{SSHA}rcZMditrBFedx2lGWSVjMUnWLLz+kEjV",
                            "slapd_type" => "master"
                            }   
                      }
                  )
