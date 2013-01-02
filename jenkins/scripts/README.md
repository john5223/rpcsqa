Scripts
=====================
 
 This will be the scripts that Jenkins runs to test our enviroments

 Examples

 # Build Cloud Servers
python ~/workspace/scripts/python/virtualized/environment/nova/build_aio_server.py --url $URL --username $USERNAME --password $PASSWORD --tenant_id $TENANT_ID --num_servers $NUM_SERVERS --server_name "Alamo AIO Test Server" --os_image $OS_IMAGE --server_flavor $SERVER_FLAVOR

# Gather Cloud Servers Info

python ~/workspace/scripts/python/virtualized/environment/nova/get_aio_env.py --username alamo

# Setup Enviroment



# Tear Down Enviroment

python ~/workspace/scripts/python/virtualized/environment/nova/teardown_aio_env.py --url $URL --username $USERNAME --password $PASSWORD --tenant_id $TENANT_ID --server_name "Alamo AIO Test Server"