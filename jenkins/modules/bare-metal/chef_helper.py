from chef import *

def cleanup_environment(chef_environment):
    nodes = Search('node').query("chef_environment:%s AND NOT in_use:0") % chef_environment
    for n in nodes:
        erase_node(n)

