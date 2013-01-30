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
    end

    execute "service networking restart" do
      only_if do
        $iface_digest != Digest::MD5.hexdigest(File.read($ifaces_file))
      end
    end

    ruby_block "gather gateways to add to routing table" do
      block do
        $gateway_hash = Hash.new
        new_ifaces = node['network_interfaces']['debian']
        new_ifaces.each do | iface |
          iface.each_pair do | k, v |
            if k == 'gateway' || k == 'device'
              $gateway_hash["#{k}"] = v
            end
          end
        end
      end
      only_if do
        $iface_digest != Digest::MD5.hexdigest(File.read($ifaces_file))
      end
    end

    ruby_block "adding default routes" do
      block do
        $gateway_hash.each do | gw |
          route "default route for #{gw['gateway']}" do
            target '0.0.0.0'
            netmask '0.0.0.0'
            gateway gw['gateway']
            device gw['device'] 
            action :add
          end
        end
      end
      only_if do
        $iface_digest != Digest::MD5.hexdigest(File.read($ifaces_file))
      end
    end

# RHEL DISTROS
  when "redhat", "centos", "fedora"
    ruby_block "Gather ifcfg files" do
      block do
        # cd into the network-scripts directory and gather all ifcfg files
        iface_scripts_dir = "/etc/sysconfig/network-scripts"
        Dir.chdir("#{iface_scripts_dir}")
        $all_ifcfg_files = Dir.glob("ifcfg-*")
      end
    end

    ruby_block "update ifcfg files" do
      block do
        # Gather the interfaces from the node, for each interface overwrite appropriate interface values
        node_interfaces = node['network_interfaces']['redhat']

        # Save the file names to an array if we change it
        $files_changed = Array.new
        
        node_interfaces.each do | node_iface |
         $all_ifcfg_files.each do | ifcfg_file |
            if ifcfg_file == "ifcfg-#{node_iface['device']}"
              file_hash = Hash.new
              
              # Open file and save all current values in a hash
              File.open(ifcfg_file, "r") do | file |
                while (line = file.gets)
                  key, value = line.split("=")
                  file_hash["#{key}"] = "#{value}"
                end
              end

              # loop through all data bag stuff and update hash as needed
              change = false
              node_iface.each_pair do | k, v |
                if file_hash["#{k.upcase}"].nil? || file_hash["#{k.upcase}"] != "#{v}"
                  puts "Found a diff in #{ifcfg_file}"
                  puts "Current key: #{k.upcase} value: #{file_hash['k']} will be changed to #{v}"
                  file_hash["#{k.upcase}"] = "\"#{v}\"\n"
                  change = true
                end
              end

              # Overwrite file if something was added to the hash
              if change == true
                File.open(ifcfg_file, "w") do | file |
                  file_hash.each_pair do | k, v |
                    line = "#{k}=#{v}"
                    file.write(line)
                  end
                end
                # Add the name of the changed file to the array
                $files_changed << ifcfg_file
              end
            end
          end
        end
      end
    end

    execute "service network restart" do
      only_if do
        $files_changed.length > 0
      end
    end

    ruby_block "gather gateways to add to routing table" do
      block do
        $gateway_hash = Hash.new
        new_ifaces = node['network_interfaces']['redhat']
        new_ifaces.each do | iface |
          iface.each_pair do | k, v |
            if k == 'gateway' || k == 'device'
              $gateway_hash["#{k}"] = v
            end
          end
        end
      end
      only_if do
        $files_changed.length > 0
      end
    end

    ruby_block "adding default routes" do
      block do
        $gateway_hash.each do | gw |
          route "default route for #{gw['gateway']}" do
            target '0.0.0.0'
            netmask '0.0.0.0'
            gateway gw['gateway']
            device gw['device'] 
            action :add
          end
        end
      end
      only_if do
        $files_changed.length > 0
      end
    end

# UNSUPPORTED DISTROS
  else
    # As distributions get added (Windows, SUSE, etc. need to update)
    ruby_block "non supported distribution" do
      block do
        puts "#{node['platform']} is not supported by this cookbook."
      end
      action :nothing
    end
end
