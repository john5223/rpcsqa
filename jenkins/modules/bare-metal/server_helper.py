import time
import sys
from chef import Node
from razor_api import razor_api
from razor_helper import razor_password
from subprocess import check_call, CalledProcessError

razor_ip = '198.101.133.3'
razor = razor_api(razor_ip)

def clone_git_repo(chef_node, github_user, github_pass):
    controller_ip = chef_node['ipaddress']
    root_pass = razor_password(chef_node)

    # Download vm setup script on controller node.
    print "Cloning repo with setup script..."
    rcps_dir = "/opt/rpcs"
    repo = "https://%s:%s@github.com/rsoprivatecloud/scripts" % (github_user,
                                                                 github_pass)
    command = "mkdir -p /opt/rpcs; git clone %s %s" % (repo, rcps_dir)
    download_run = run_remote_ssh_cmd(controller_ip,
                                      'root',
                                      root_pass,
                                      command)
    if not download_run['success']:
        print "Failed to clone script repo on server %s@%s" % (chef_node,
                                                               controller_ip)
        print "Return Code: %s" % download_run['exception'].returncode
        print "Exception: %s" % download_run['exception']
        sys.exit(1)
    else:
        print "Successfully cloned repo with setup script..."

def disable_iptables(chef_node, logfile="STDOUT"):
    ip = chef_node['ipaddress']
    root_pass = razor.get_active_model_pass(chef_node['razor_metadata'].to_dict()['razor_active_model_uuid'])['password']
    return run_remote_ssh_cmd(ip, 'root', root_pass, '/etc/init.d/iptables save; /etc/init.d/iptables stop; /etc/init.d/iptables save')

def install_opencenter(server, install_script, role, server_ip="0.0.0.0"):
    node = Node(server)
    root_pass = razor_password(node)
    print ""
    print ""
    print "*****************************************************"
    print "*****************************************************"
    print "Installing %s..." % role
    print "*****************************************************"
    print "*****************************************************"
    print ""
    print ""
    if node['platform_family'] == "debian":
        run_remote_ssh_cmd(node['ipaddress'],
                           'root',
                           root_pass,
                           'apt-get update -y -qq')
    elif node['platform_family'] == "rhel":
        run_remote_ssh_cmd(node['ipaddress'],
                           'root',
                           root_pass,
                           ('yum update -y -q;'
                            '/etc/init.d/iptables save;'
                            '/etc/init.d/iptables stop'))
    command = "bash <(curl %s) --role=%s --ip=%s" % (install_script,
                                                     role,
                                                     server_ip)
    print command
    ret = run_remote_ssh_cmd(node['ipaddress'], 'root', root_pass, command)
    if not ret['success']:
        print "Failed to install opencenter %s" % type

def install_opencenter_vm(vm_ip, oc_server_ip, install_script, role, user, passwd):
    command = "bash <(curl %s) --role=%s --ip=%s" % (install_script,
                                                     role,
                                                     oc_server_ip)
    install_run = run_remote_ssh_cmd(vm_ip, user, passwd, command)
    if not install_run['success']:
        print "Failed to install OpenCenter %s on VM..." % role
        print "Return Code: %s" % install_run['exception'].returncode
        print "Exception: %s" % install_run['exception']
        sys.exit(1)
    else:
        print "OpenCenter %s successfully installed on vm with ip %s" % (role,
                                                                         vm_ip)

def install_server_vms(controller_node, opencenter_server_ip, chef_server_ip, vm_bridge, vm_bridge_device):
    controller_ip = controller_node['ipaddress']
    root_pass = razor_password(controller_node)

    # Run vm setup script on controller node
    print "Running VM setup script..."
    script = "/opt/rpcs/oc_prepare.sh"
    command = "bash %s %s %s %s %s" % (script,
                                       chef_server_ip,
                                       opencenter_server_ip,
                                       vm_bridge,
                                       vm_bridge_device)
    print "Prepare command to run: %s" % command
    install_run = run_remote_ssh_cmd(controller_ip, 'root', root_pass, command)
    if not install_run['success']:
        print "Failed VM setup script on server %s@%s" % (controller_node,
                                                          controller_ip)
        print "Command ran: %s" % install_run['command']
        print "Return Code: %s" % install_run['exception'].returncode
        print "Exception: %s" % install_run['exception']
        sys.exit(1)
    else:
        print "VM's successfully setup on server %s..." % controller_node

def ping_check_vm(ip_address):
    command = "ping -c 5 %s" % ip_address
    try:
        ret = check_call(command, shell=True)
        return {'success': True, 'return': ret, 'exception': None}
    except CalledProcessError, cpe:
        return {'success': False,
                'return': None,
                'exception': cpe,
                'command': command}

def prepare_vm_host(controller_node):
    controller_ip = controller_node['ipaddress']
    root_pass = razor_password(controller_node)

    if controller_node['platform_family'] == 'debian':
        commands = [("aptitude install -y curl dsh screen vim"
                     "iptables-persistent libvirt-bin python-libvirt"
                     "qemu-kvm guestfish git"),
                    "aptitude update -y",
                    "update-guestfs-appliance",
                    "ssh-keygen -f /root/.ssh/id_rsa -N \"\""]
    else:
        commands = [("yum install -y curl dsh screen vim iptables-persistent"
                     "libvirt-bin python-libvirt qemu-kvm guestfish git"),
                    "yum update -y",
                    "update-guestfs-appliance",
                    "ssh-keygen -f /root/.ssh/id_rsa -N \"\""]

    for command in commands:
        print "************************************"
        print "Prepare command to run: %s" % command
        print "************************************"
        prepare_run = run_remote_ssh_cmd(controller_ip,
                                         'root',
                                         root_pass,
                                         command)

        if not prepare_run['success']:
            print "Failed to run command %s" % command
            print "check the server %s @ ip: %s" % (controller_node,
                                                    controller_ip)
            print "Return Code: %s" % prepare_run['exception'].returncode
            print "Exception: %s" % prepare_run['exception']
            sys.exit(1)

def print_server_info(name):
    node = Node(name)
    return "%s - %s" % (name, node['ipaddress'])

def print_computes_info(computes):
    for compute in computes:
        print "Compute: %s" % print_server_info(compute)

def run_remote_ssh_cmd(server_ip, user, passwd, remote_cmd):
    """
    @param server_ip
    @param user
    @param passwd
    @param remote_cmd
    @return A map based on pass / fail run info
    """
    command = ("sshpass -p %s ssh"
               "-o UserKnownHostsFile=/dev/null"
               "-o StrictHostKeyChecking=no"
               "-o LogLevel=quiet"
               "-l %s %s '%s'") % (passwd,
                                   user,
                                   server_ip,
                                   remote_cmd)
    try:
        ret = check_call(command, shell=True)
        return {'success': True, 'return': ret, 'exception': None}
    except CalledProcessError, cpe:
        return {'success': False,
                'retrun': None,
                'exception': cpe,
                'command': command}

def run_remote_scp_cmd(server_ip, user, passwd, to_copy):
    """
    @param server_ip
    @param user
    @param passwd
    @param to_copy
    @return A map based on pass / fail run info
    """
    command = ("sshpass -p %s scp"
               "-o UserKnownHostsFile=/dev/null"
               "-o StrictHostKeyChecking=no"
               "-o LogLevel=quiet"
               "%s %s@%s:~/") % (passwd,
                                 to_copy,
                                 user,
                                 server_ip)
    try:
        ret = check_call(command, shell=True)
        return {'success': True,
                'return': ret,
                'exception': None}
    except CalledProcessError, cpe:
        return {'success': False,
                'return': None,
                'exception': cpe,
                'command': command}

def run_chef_client(name, logfile="STDOUT"):
    """
    @param name
    @param  logfile
    @return run_remote_ssh_cmd of chef-client
    """
    node = Node(name)
    ip = node.attributes['ipaddress']
    root_pass = razor_password(node)
    return run_remote_ssh_cmd(ip,
                              'root',
                              root_pass,
                              'chef-client --logfile %s' % logfile)

def remove_broker_fail(policy):
    active_models = razor.simple_active_models(policy)
    for active in active_models:
        data = active_models[active]
        if 'broker_fail' in data['current_state']:
            print "!!## -- Removing active model  (broker_fail) -- ##!!"
            root_pass = razor.get_active_model_pass(
                data['am_uuid'])['password']
            ip = data['eth1_ip']
            run = run_remote_ssh_cmd(ip, 'root', root_pass, 'reboot 0')
            if run['success']:
                razor.remove_active_model(data['am_uuid'])
                time.sleep(15)
            else:
                print "Trouble removing broker fail"
                print run
                sys.exit(1)

def remove_chef(name):
    """
    @param name
    """
    run = None
    try:
        node = Node(name)
        root_pass = razor_password(node)
        print "removing chef on %s..." % name
        command = ""
        if node['platform_family'] == "debian":
            command = "apt-get remove --purge -y chef; rm -rf /etc/chef"
        elif node['platform_family'] == "rhel":
            command = 'yum remove -y chef; rm -rf /etc/chef /var/chef'
        run = run_remote_ssh_cmd(node['ipaddress'], 'root', root_pass, command)
    except:
        print "Error removing chef"
        return run

def set_network_interfaces(chef_nodes):
    for n in chef_nodes:
        node = Node(n['name'])
        if "role[qa-base]" in node.run_list:
            node.run_list = ["recipe[network-interfaces]"]
            node.save()
            print "Running network interfaces for %s" % node.name
          
            #Run chef client thrice
            run1 = run_chef_client(node, logfile="/dev/null")
            run2 = run_chef_client(node, logfile="/dev/null")
            run3 = run_chef_client(node, logfile="/dev/null")

            if run1['success'] and run2['success'] and run3['success']:
                print "Done running chef-client"
            else:
                print "Error running chef client for network interfaces"
                print "First run: %s" % run1
                print "Second run: %s" % run2
                print "Final run: %s" % run3
                sys.exit(1)

def set_nodes_environment(chef_node, environment):
    if chef_node.chef_environment != environment:
        chef_node.chef_environment = environment
        chef_node.save()

def update_node(chef_node):
    ip = chef_node['ipaddress']
    root_pass = razor.get_active_model_pass(chef_node['razor_metadata'].to_dict()['razor_active_model_uuid'])['password']
    if chef_node['platform_family'] == "debian":
        run_remote_ssh_cmd(ip, 'root', root_pass, 'apt-get update -y -qq')
    elif chef_node['platform_family'] == "rhel":
        run_remote_ssh_cmd(ip, 'root', root_pass, 'yum update -y -q')
    else:
        print "Platform Family %s is not supported." % chef_node['platform_family']
        sys.exit(1)
