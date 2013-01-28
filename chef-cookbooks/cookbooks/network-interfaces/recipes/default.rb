#
# Cookbook Name:: network_interfaces
# Recipe:: default
#
# Copyright 2012, YOUR_COMPANY_NAME
#
# All rights reserved - Do Not Redistribute
#
require 'digest/md5'

case node['platform']
# DEBIAN DISTROS
  when 'ubuntu', 'debian'
    ruby_block "existing ifaces" do
      block do
        $ifaces_file = "/etc/network/interfaces"
        $ifaces_file_munge = Array.new
        $marker_tpl = "# *** %s OF CHEF MANAGED INTERFACES ***\n"
        # Build an array ifaces_file_munge that has the contents of 
        # /etc/network/interfaces and excludes the chef managed blocks
        File.open($ifaces_file, "r") do | ifaces_file |
          marker = false
          while (line = ifaces_file.gets)
            if line =~ /^#{$marker_tpl.gsub('*', '\*') % ["(START|END)"]}/
              marker = line =~ /START/ ? true : false
              next
            end
            if (marker == false)
              $ifaces_file_munge << line
            end
          end
        end 
        $ifaces_file_munge << $marker_tpl % ['START']
        $iface_digest = Digest::MD5.hexdigest(File.read($ifaces_file))
      end
      action :create
    end

    # create the interfaces file for the node using
    # the interfaces template
    template "/tmp/chef-net-iface" do
      source "interfaces.erb"
      mode 0644
      owner "root"
      group "root"
      variables({:network_interfaces => node['network_interfaces']['debian']})
    end

    # merge new ifaces with the old ones
    ruby_block "munge interface files" do
      block do
        File.open("/tmp/chef-net-iface", "r") do | iface |
          while (line = iface.gets)
            $ifaces_file_munge << line
          end
        end
        File.delete("/tmp/chef-net-iface")
      end
      action :create
    end

    ruby_block "finalize interfaces file" do
      block do
        $ifaces_file_munge << $marker_tpl % ['END']
        File.open($ifaces_file, "w") do | ifaces |
          $ifaces_file_munge.each do | line |
            ifaces.write(line)
          end
        end
      end
      action :create
    end

    execute "service networking restart" do
      only_if do
        $iface_digest != Digest::MD5.hexdigest(File.read($ifaces_file))
      end
    end

    ruby_block "Gather gateways to add to routing table" do
      block do
        $gateway_hash = Hash.new
        new_ifaces = node['network_interfaces']['debian']
        new_ifaces.each do | iface |
          iface.each_pair do | k, v |
            if k == "gateway" || k == 'device'
              $gateway_hash["#{k}"] = v
            end
          end
        end
      end
    end

    ruby_block "Set default routes" do
      block do
        $gateway_hash.each do | gateway |
          # create the config gile
          content = Chef::Provider::Route.config_file_contents(:add, 
                                                               :target => Chef::Provider::Route.MASK[0.0.0.0],
                                                               :netmask => Chef::Provider::Route.MASK[0.0.0.0],
                                                               :gateway => gateway['gateway'],
                                                               :device => gateway['device'])
          end
        end
      end
    end

# RHEL DISTROS
  when "redhat", "centos", "fedora"
    ruby_block "configure ifcfg files" do
      block do
        
        # cd into the network-scripts directory and gather all ifcfg files
        iface_scripts_dir = "/etc/sysconfig/network-scripts"
        Dir.chdir("#{iface_scripts_dir}")
        all_iface_files = Dir.glob("ifcfg-*")

        # Gather the interfaces from the node, for each interface overwrite appropriate interface values
        node_interfaces = node['network_interfaces']['redhat']
        node_interfaces.each do | node_iface |
          all_iface_files.each do | iface_file |
            if iface_file == "ifcfg-#{node_iface['device']}"
              file_hash = Hash.new
              
              # Open file and save all current values in a hash
              File.open(iface_file, "r") do | file |
                while (line = file.gets)
                  key, value = line.split("=")
                  file_hash["#{key}"] = "#{value}"
                end
              end

              # loop through all data bag stuff and update hash as needed
              node_iface.each_pair do | k, v |
                file_hash["#{k.upcase}"] = "\"#{v}\"\n"
              end

              # Overwrite file
              File.open(iface_file, "w") do | file |
                file_hash.each_pair do | k, v |
                  line = "#{k}=#{v}"
                  file.write(line)
                end
              end
            end
          end
        end
      end
      action :create
    end

# UNSUPPORTED DISTROS
  else
    # As distributions get added (Windows, SUSE, etc. need to update)
    ruby_block "Non Supported Distribution" do
      block do
        puts "#{node['platform']} is not supported by this cookbook."
      end
      action :nothing
    end
end
