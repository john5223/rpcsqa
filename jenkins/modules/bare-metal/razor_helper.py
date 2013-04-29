from razor_api import razor_api

razor_ip = '198.101.133.3'
razor = razor_api(razor_ip)


def razor_password(node):
    metadata = node.attributes['razor_metadata'].to_dict()
    uuid = metadata['razor_active_model_uuid']
    return razor.get_active_model_pass(uuid)['password']
