#
# Cookbook Name:: network_interfaces
# Recipe:: default
#
# Copyright 2012, YOUR_COMPANY_NAME
#
# All rights reserved - Do Not Redistribute
#
require 'digest/md5'

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
  variables({:network_interfaces => node['network_interfaces']})
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
  netmask "255.255.255.0"
  gateway "198.101.133.1"
  device "eth0"
end
