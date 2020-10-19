import requests
import json
import datetime


def login(args):
    login_res = requests.post(url=args.url + '/login',
                              data={'username': args.username,
                                    'password': args.password})
    try:
        res_json = json.loads(login_res.content)
    except json.decoder.JSONDecodeError:
        raise Exception('Login responded with 404 error. Is URL wrong?')
    if 'error' not in res_json.keys():
        return login_res.cookies
    else:
        raise Exception("Login error: {}".format(res_json["error"]))


def request_and_response(args, url, json_data, cookies, name_suffix=''):
    headers = {'Content-type': 'application/json'}
    get_response = requests.get(url=url.rstrip('s') + 's', cookies=cookies)
    try:
        get_response = json.loads(get_response.text)['data']
    except json.decoder.JSONDecodeError:
        raise Exception('Error parsing json. Please check if webconsole api changed.')

    post = True
    _id = -1
    for obj in get_response:
        obj_ = obj if 'name' in obj.keys() else obj['localdata']
        if obj_['name'] == args.name + name_suffix:
            _id = obj_['id']
            post = False
            break

    if post:
        response = requests.post(url=url, data=json_data, cookies=cookies, headers=headers)
    elif 'raw-data' not in name_suffix:
        response = requests.put(url=url + '/' + str(_id), data=json_data, cookies=cookies, headers=headers)
    else:
        print("Currently modifying existing raw data is not supported.")
        return _id, args.name + name_suffix

    try:
        response = json.loads(response.text)
    except json.decoder.JSONDecodeError:
        raise Exception('404 error encountered when building/modifying {}. '
                        'Please check whether webconsole api changed.'.format(url.split('/')[-1]))
    if 'error' not in response.keys():
        _id = response['data']['id']
        name = response['data']['name']
    else:
        raise Exception('Build/Modify {} error: {}'.format(url.split('/')[-1], response['error']))
    return _id, name


def build_raw_data(args, fed_id, filepath):
    with open(filepath) as f:
        raw_json = json.load(f)
        name_suffix = '-raw-data'
        raw_json['name'] = args.name + name_suffix
        raw_json['federation_id'] = fed_id
        raw_json['image'] = args.image
        fl_rep_spec = raw_json['context']['yaml_spec']['spec']['flReplicaSpecs']
        fl_rep_spec['Master']['template']['spec']['containers'][0]['image'] = args.image
        fl_rep_spec['Worker']['template']['spec']['containers'][0]['image'] = args.image
        raw_json = json.dumps(raw_json, separators=(',', ':'))
    return raw_json, name_suffix


def build_data_join_ticket(args, fed_id, raw_name, filepath, role):
    with open(filepath) as f:
        ticket_json = json.load(f)
        name_suffix = '-join-ticket'
        ticket_json['name'] = args.name + name_suffix
        ticket_json['federation_id'] = fed_id
        ticket_json['role'] = role
        ticket_json['sdk_version'] = args.image.split(':')[-1]
        ticket_json['expire_time'] = str(datetime.datetime.now().year + 1) + '-12-31'
        for param in ['public_params', 'private_params']:
            for pod in ticket_json[param]['spec']['flReplicaSpecs'].values():
                container = pod['template']['spec']['containers'][0]
                container['image'] = args.image
                for d in container['env']:
                    if d['name'] == 'RAW_DATA_SUB_DIR':
                        d['value'] += raw_name
                        break
        ticket_json = json.dumps(ticket_json, separators=(',', ':'))
    return ticket_json, name_suffix


def build_train_ticket(args, fed_id, filepath, role, client=True):
    with open(filepath) as f:
        ticket_json = json.load(f)
        name_suffix = '-train-ticket'
        ticket_json['name'] = args.name + name_suffix
        ticket_json['federation_id'] = fed_id
        ticket_json['role'] = role
        ticket_json['expire_time'] = str(datetime.datetime.now().year + 1) + '-12-31'
        for param in ['public_params', 'private_params']:
            for pod in ticket_json[param]['spec']['flReplicaSpecs'].values():
                container = pod['template']['spec']['containers'][0]
                container['image'] = args.image
                for d in container['env']:
                    if d['name'] == 'DATA_SOURCE':
                        d['value'] = (args.x_federation if client else args.name) + '-join-job'
                        break
        ticket_json = json.dumps(ticket_json, separators=(',', ':'))
    return ticket_json, name_suffix
