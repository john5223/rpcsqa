#!/usr/bin/python
import os, json, argparse,time, requests
from razor_api import razor_api
from chef import *

parser = argparse.ArgumentParser()
parser.add_argument('--razor_ip', action="store", dest="razor_ip", required=True, help="IP for the Razor server")
parser.add_argument('--policy', action="store", dest="policy", required=True, help="Razor policy to set chef roles for.")
parser.add_argument('--data_bag_location', action="store", dest="data_bag_loc", default="/var/lib/jenkins/rpcsqa/chef-cookbooks/data_bags/razor_node",  required=False, help="Location of chef data bags")
parser.add_argument('--tempest_dir', action="store", dest="tempest_dir", required=True, default="/var/lib/jenkins/tempest/folsom/tempest", help="")

#parser.add_argument('--role', action="store", dest="role", required=True, help="Chef role to run chef-client on")
parser.add_argument('--chef_url', action="store", dest="chef_url", default="http://198.101.133.4:4000", required=False, help="client for chef")
parser.add_argument('--chef_client', action="store", dest="chef_client", default="jenkins", required=False, help="client for chef")
parser.add_argument('--chef_client_pem', action="store", dest="chef_client_pem", default="/var/lib/jenkins/rpcsqa/.chef/jenkins.pem", required=False, help="client pem for chef")
parser.add_argument('--display_only', action="store", dest="display_only", default="true", required=False, help="Display the node information only (will not reboot or teardown am)")
results = parser.parse_args()

def get_chef_name(data):
    try:
        name = "%s%s.%s" % (data['hostname_prefix'], data['bind_number'], data['domain'])
        return name
    except Exception, e:
        return ''
def get_root_pass(data):
    if 'root_password' in data:
        return data['root_password']
    else:
        return ''

#############################################################
#Collect active models that match policy from given input
#############################################################

razor = razor_api(results.razor_ip)
active_models = razor.simple_active_models(results.policy)


if active_models == {}:
    print "'%s' active models: 0 " % (policy)
    print "#################################"
else:
     if 'response' in active_models.keys():
          active_models = active_models['response']
     
     # Gather all of the active models for the policy and get information about them
     for active in active_models:
          data = active_models[active]
          chef_name = get_chef_name(data)
          root_password = get_root_pass(data)

          with ChefAPI(results.chef_url, results.chef_client_pem, results.chef_client):
               node = Node(chef_name)
               if 'role[qa-single-controller]' in node.run_list:
                   try: 
                        ip = node['ipaddress']
                        
                        #print node.attributes.to_dict()
                        
                        eth1_ips = node.attributes['network']['interfaces']['eth1']['addresses'].to_dict().keys()
                        private_ip = [x for x in eth1_ips if x.count('.')>0]
                        
                        print "Private ip: %s "  % private_ip
                        if len(private_ip)>0:
                            private_ip = private_ip[0]
                            url = "http://%s:5000/v2.0" % private_ip
                            print "Keystone url:  %s  " % url
                            
                        
                            token_url = "%s/tokens" % url    
                            #print token_url    
                            auth = {'auth': {'tenantName': 'admin', 'passwordCredentials': {'username': 'admin', 'password': 'ostackdemo'}}}
                            r = requests.post(token_url, data=json.dumps(auth), headers={'Content-type': 'application/json'})
                            
                            ans = json.loads(r.text)
                            if 'access' in ans.keys():
                                token = ans['access']['token']['id']
                                #print token
                                
                                images_url = "http://%s:9292/v2/images" % private_ip
                                #print images_url
                                images = json.loads(requests.get(images_url, headers={'X-Auth-Token': token}).text)
                                
                                for image in images['images']:
                                    if image['name'] == 'cirros-image':
                                        image_id = image['id']
                        
                   except Exception, e:
                       print e
                   
                   
                   tempest_dir = ''
                   try:
                       sample_path = "%s/etc/base.conf" % results.tempest_dir
                       
                       with open(sample_path) as f:
                           sample_config = f.read()
                       
                       #print sample_config 
                       tempest_config = str(sample_config) 
                       tempest_config = tempest_config.replace('http://127.0.0.1:5000/v2.0/',url)
                       tempest_config = tempest_config.replace('{$KEYSTONE_IP}',private_ip)
                       tempest_config = tempest_config.replace('{$IMAGE_ID}',image_id)
                       tempest_config = tempest_config.replace('{$IMAGE_ID_ALT',image_id)
                       print "##################################"
                       print tempest_config
                       print "##################################"
                       
                       tempest_config_path = "%s/etc/%s.conf" % (results.tempest_dir, results.policy)
                       with open(tempest_config_path, 'w') as w:
                            w.write(tempest_config)
                       
                   except Exception, e:
                        print e
