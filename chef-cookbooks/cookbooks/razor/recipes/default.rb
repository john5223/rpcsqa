#
# Cookbook Name:: razor
# Recipe:: default
#
# Copyright 2012, Rackspace US Inc.
#
# All rights reserved - Do Not Redistribute
#

ruby_block "set node info from data bag" do
	block do
		ethers = Array.new
		node.network.interfaces.each do |(k,v)|
			v[:addresses].each do |(k2,v2)|
				ethers << k2.gsub(":","").upcase if v2[:family] == "lladdr"
			end
		end
		uuid = ethers.sort.join("_")
		enviroment_variables = data_bag_item("razor_node", uuid) if uuid != ""
		if enviroment_variables != []
			enviroment_variables.each {|(k,v)| node.set[k] = v}
			node.save
		end
	end
end
