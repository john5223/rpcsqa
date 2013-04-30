import sys
import time
from chef import Search, Node, Client
from razor_api import razor_api
from server_helper import run_remote_ssh_cmd


razor_ip = '198.101.133.3'
razor = razor_api(razor_ip)


def build_computes(computes):
    # Run computes
    print "Making the compute nodes..."
    for compute in computes:
        compute_node = Node(compute)
        compute_node['in_use'] = "compute"
        compute_node.run_list = ["role[qa-single-compute]"]
        compute_node.save()

        print "Updating server...this may take some time"
        update_node(compute_node)

        if compute_node['platform_family'] == 'rhel':
            print "Platform is RHEL family, disabling iptables"
            disable_iptables(compute_node)

        # Run chef client twice
        print "Running chef-client on compute node: %s, this may take some time..." % compute
        run1 = run_chef_client(compute_node)
        if run1['success']:
            print "First chef-client run successful...starting second run..."
            run2 = run_chef_client(compute_node)
            if run2['success']:
                print "Second chef-client run successful..."
            else:
                print "Error running chef-client for compute %s" % compute
                print run2
                sys.exit(1)
        else:
            print "Error running chef-client for compute %s" % compute
            print run1
            sys.exit(1)


def build_controller(controller, ha=False, ha_num=0):
    controller_node = Node(controller)

    # Check for ha
    if ha:
        print "Making %s the ha-controller%s node" % (controller, ha_num)
        controller_node['in_use'] = "ha-controller%s" % ha_num
        controller_node.run_list = ["role[qa-ha-controller%s]" % ha_num]
    else:
        print "Making %s the controller node" % controller
        controller_node['in_use'] = "controller"
        controller_node.run_list = ["role[qa-single-controller]"]
    # save node
    controller_node.save()

    print "Updating server...this may take some time"
    update_node(controller_node)

    if controller_node['platform_family'] == 'rhel':
        print "Platform is RHEL family, disabling iptables"
        disable_iptables(controller_node)

    # Run chef-client twice
    print "Running chef-client for controller node...this may take some time..."
    run1 = run_chef_client(controller_node)
    if run1['success']:
        print "First chef-client run successful...starting second run..."
        run2 = run_chef_client(controller_node)
        if run2['success']:
            print "Second chef-client run successful..."
        else:
            print "Error running chef-client for controller %s" % controller
            print run2
            sys.exit(1)
    else:
        print "Error running chef-client for controller %s" % controller
        print run1
        sys.exit(1)


def build_dir_server(dir_server):
    # We dont support 389 yet, so exit if it is not ldap
    if results.dir_version != 'openldap':
        print "%s as a directory service is not yet supported...exiting" % results.dir_version
        sys.exit(1)

    # Build directory service node
    dir_node = Node(dir_server)
    ip = dir_node['ipaddress']
    root_pass = razor.get_active_model_pass(dir_node['razor_metadata'].to_dict()['razor_active_model_uuid'])['password']
    dir_node['in_use'] = 'directory-server'
    dir_node.run_list = ["role[qa-%s-%s]" % (results.dir_version, results.os)]
    dir_node.save()

    print "Updating server...this may take some time"
    update_node(dir_node)

    # if redhat platform, disable iptables
    if dir_node['platform_family'] == 'rhel':
        print "Platform is RHEL family, disabling iptables"
        disable_iptables(dir_node)

    # Run chef-client twice
    print "Running chef-client for directory service node...this may take some time..."
    run1 = run_chef_client(dir_node)
    if run1['success']:
        print "First chef-client run successful...starting second run..."
        run2 = run_chef_client(dir_node)
        if run2['success']:
            print "Second chef-client run successful..."
        else:
            print "Error running chef-client for directory node %s" % dir_node
            print run2
            sys.exit(1)
    else:
        print "Error running chef-client for directory node %s" % dir_node
        print run1
        sys.exit(1)

    # Directory service is set up, need to import config
    if run1['success'] and run2['success']:
        if results.dir_version == 'openldap':
            scp_run = run_remote_scp_cmd(ip, 'root', root_pass, '/var/lib/jenkins/source_files/ldif/*.ldif')
            if scp_run['success']:
                ssh_run = run_remote_ssh_cmd(ip, 'root', root_pass, 'ldapadd -x -D \"cn=admin,dc=dev,dc=rcbops,dc=me\" -f base.ldif -w@privatecloud')
        elif results.dir_version == '389':
            # Once we support 389, code here to import needed config files
            print "389 is not yet supported..."
            sys.exit(1)
        else:
            print "%s is not supported...exiting" % results.dir_version
            sys.exit(1)

    if scp_run['success'] and ssh_run['success']:
        print "Directory Service: %s successfully set up..." % results.dir_version
    else:
        print "Failed to set-up Directory Service: %s..." % results.dir_version
        sys.exit(1)


def check_cluster_size(chef_nodes, size):
    if len(chef_nodes) < size:
        print "*****************************************************"
        print "Not enough nodes for the cluster_size given: %s " % cluster_size
        print "*****************************************************"
        sys.exit(1)


def clear_pool(chef_nodes, environment):
    for n in chef_nodes:
        name = n['name']
        node = Node(name)
        if node.chef_environment == environment:
            if "recipe[network-interfaces]" not in node.run_list:
                erase_node(name)
            else:
                node.chef_environment = "_default"
                node.save()


def cleanup_environment(chef_environment):
    """
    @param chef_environment
    """
    nodes = Search('node').query("chef_environment:%s AND NOT in_use:0") % \
        chef_environment
    for n in nodes:
        erase_node(n)


def environment_has_controller(environment):
    # Load Environment
    nodes = Search('node').query("chef_environment:%s" % environment)
    roles = ['role[qa-single-controller]', 'role[qa-ha-controller1]', 'role[qa-ha-controller2]']
    for node in nodes:
        chef_node = Node(node['name'])
        if any(x in chef_node.run_list for x in roles):
            return True
        else:
            return False


def gather_nodes(chef_nodes, environment, cluster_size):
    ret_nodes = []
    count = 0

    # Take a node from the default environment that has its network interfaces set.
    for n in chef_nodes:
        name = n['name']
        node = Node(name)
        if ((node.chef_environment == "_default" or node.chef_environment == environment) and "recipe[network-interfaces]" in node.run_list):
            node['in_use'] = 1
            set_nodes_environment(node, environment)
            ret_nodes.append(name)          
            print "Taking node: %s" % name
            count += 1

            if count >= cluster_size:
                break

    if count < cluster_size:
        print "Not enough available nodes for requested cluster size of %s, try again later..." % cluster_size
        sys.exit(1)

    return ret_nodes


def erase_node(name):
    """
    @param name
    """
    print "Deleting: %s" % (name)
    node = Node(name)
    am_uuid = node['razor_metadata'].to_dict()['razor_active_model_uuid']
    run = run_remote_ssh_cmd(node['ipaddress'],
                             'root',
                             razor.get_active_model_pass(am_uuid)['password'],
                             "reboot 0")
    if not run['success']:
        print "Error rebooting server %s " % node['ipaddress']
        # TODO: return failure
        sys.exit(1)
    #Knife node remove; knife client remove
    Client(name).delete()
    Node(name).delete()
    #Remove active model
    razor.remove_active_model(am_uuid)
    time.sleep(15)
