from opencenterclient.client import OpenCenterEndpoint
from chef import Search, Node
import sys


def openstack_endpoints(chef, name='test', os='ubuntu'):
    # Make sure environment exists
    env = "%s-%s-opencenter" % (name, os)
    if not Search("environment").query("name:%s" % env):
        print "environment %s not found" % env
        sys.exit(1)
    query = "in_use:\"server\" AND chef_environment:%s" % env
    opencenter_server = next(Node(node['name']) for node in
                             Search('node').query(query))
    ep_url = "https://%s:8443" % opencenter_server['ipaddress']
    ep = OpenCenterEndpoint(ep_url,
                            user="admin",
                            password="password")
    infrastructure_nodes = ep.nodes.filter('name = "Infrastructure"')
    for node_id in infrastructure_nodes.keys():
        ha = infrastructure_nodes[node_id].facts["ha_infra"]
        endpoint = None
        if ha:
            endpoint = infrastructure_nodes[node_id].facts["nova_api_vip"]
        else:
            name = next(node.name for node in ep.nodes
                        if "nova-controller" in node.facts["backends"])
            endpoint = Node(name)['ipaddress']
        yield endpoint
        
