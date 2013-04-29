from chef import *
from razor_api import razor_api
from subprocess import check_call, CalledProcessError

razor_ip = '198.101.133.3'
razor = razor_api(razor_ip)

"""
@param server_ip
@param user
@param passwd
@param remote_cmd
@return A map based on pass / fail run info
"""
def run_remote_ssh_cmd(server_ip, user, passwd, remote_cmd):
    """Runs a command over an ssh connection"""
    command = "sshpass -p %s ssh -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -o LogLevel=quiet -l %s %s '%s'" % (passwd, user, server_ip, remote_cmd)
    try:
        ret = check_call(command, shell=True)
        return {'success': True, 'return': ret, 'exception': None}
    except CalledProcessError, cpe:
        return {'success': False,
                'retrun': None,
                'exception': cpe,
                'command': command}


"""
@param server_ip
@param user
@param passwd
@param to_copy
@return A map based on pass / fail run info
"""
def run_remote_scp_cmd(server_ip, user, passwd, to_copy):
    command = "sshpass -p %s scp -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no \
    -o LogLevel=quiet %s %s@%s:~/" % (password, to_copy, user, server_ip)
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

"""
@param name
@param  logfile
@return run_remote_ssh_cmd of chef-client
"""
def run_chef_client(name, logfile="STDOUT"):
    node = Node(name)    
    ip = node.attributes['ipaddress']
    root_pass = razor.get_active_model_pass(
        node.attributes['razor_metadata'].to_dict()['razor_active_model_uuid'])['password']
    return run_remote_ssh_cmd(ip, 'root', root_pass, 'chef-client --logfile %s' % logfile)

""" 
@param name
"""
def remove_chef(name):
    try:
        node = Node(name)
        am_uuid = node['razor_metadata'].to_dict()['razor_active_model_uuid']
        root_pass = razor.get_active_model_pass(am_uuid)['password']        
        print "removing chef on %s..." % name
        command = ""
        if node['platform_family'] == "debian":
            command = "apt-get remove --purge -y chef; rm -rf /etc/chef"
        elif node['platform_family'] == "rhel":
            command = 'yum remove -y chef; rm -rf /etc/chef /var/chef'  
        #print command          
        run = run_remote_ssh_cmd(node['ipaddress'], 'root', root_pass, command)
    except:
        print "Error removing chef"
        sys.exit(1)

"""
@param name
"""
def erase_node(name):
    print "Deleting: %s" % (name)
    node = Node(name)  
    am_uuid = node['razor_metadata'].to_dict()['razor_active_model_uuid']
    run = run_remote_ssh_cmd(node['ipaddress'], 'root', razor.get_active_model_pass(am_uuid)['password'], "reboot 0")
    if not run['success']:
        print "Error rebooting server %s " % node['ipaddress']
        sys.exit(1)        
    #Knife node remove; knife client remove
    Client(name).delete()
    Node(name).delete()                
    #Remove active model          
    razor.remove_active_model(am_uuid)                            
    time.sleep(15)