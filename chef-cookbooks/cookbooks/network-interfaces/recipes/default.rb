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

    route "0.0.0.0" do
      netmask "0.0.0.0"
      gateway "198.101.133.1"
      device "eth0"
      only_if do
        $iface_digest != Digest::MD5.hexdigest(File.read($ifaces_file))
      end
    end

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
              puts "MATCH: file name: #{iface_file} with ifcfg-#{node_iface['device']}."
              file_hash = Hash.new
              File.open(iface_file, "r") do | file |
                while (line = file.gets)
                  key, value = line.split("=")
                  node_iface.each_pair do | k, v |
                    if not key = "#{k.upcase}"
                      file_hash["#{k}"] = "\"#{v}\""
                    else
                      file_hash["#{key}"] = "#{value}"
                    end
                  end
                end
              end
              file_hash.each_pair do | k, v |
                puts "Key: #{k}, Value: #{v}"
              end
            end
          end
        end
      end
    end
  else
    puts "Not a Linux Distro, you should never see this(unless you are windows, stop being windows)."
end

#if iface_file =~ node_iface['device']
  #rc = Chef::Util::FileEdit.new("#{iface_file}")
  #node_iface.each_pair do | k, v |
    #puts "key: #{k.upcase}, value #{v}"
    #rc.search_file_replace_line(/^#{k.upcase}*$/, "#{k.upcase}=\"#{v}\"")
  #end
  #rc.write_file
#end