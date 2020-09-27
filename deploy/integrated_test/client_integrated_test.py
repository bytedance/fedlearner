#!/usr/bin/env python3
import argparse
import json
import requests
import datetime


def login(args):
    login_res = requests.post(url=args.url + '/login',
                              data={'username': args.username,
                                    'password': args.password})
    res_json = json.loads(login_res.text)
    if 'error' not in res_json.keys():
        return login_res.cookies
    else:
        raise Exception("Login error: " + res_json["error"])


def request_and_response(args, url, json_data, cookies, name_suffix=''):
    headers = {'Content-type': 'application/json'}
    get_response = requests.get(url=url.rstrip('s') + 's', cookies=cookies)
    get_response = json.loads(get_response.text)['data']
    post = True
    _id = -1
    for obj in get_response:
        if 'name' in obj.keys():
            obj_ = obj
        else:
            obj_ = obj['localdata']
        if obj_['name'] == args.name + name_suffix:
            _id = obj_['id']
            post = False
            break

    if post:
        response = requests.post(url=url, data=json_data, cookies=cookies, headers=headers)
    elif 'raw-data' not in name_suffix:
        response = requests.put(url=url + '/' + str(_id), data=json_data, cookies=cookie, headers=headers)
    else:
        print("Currently modifying existing raw data is not supported.")
        return _id, args.name + name_suffix

    response = json.loads(response.text)
    if 'error' not in response.keys():
        _id = response['data']['id']
        name = response['data']['name']
    else:
        raise Exception('Build/Modify ' + url.split('/')[-1] + ' error: ' + response['error'])
    return _id, name


def build_federation_json(args):
    with open("template_json/template_client_federation.json") as f:
        fed_json = json.load(f)
        fed_json['name'] = args.name
        fed_json['x-federation'] = args.x_federation
        fed_json['trademark'] = args.name
        fed_json['k8s_settings']['grpc_spec']['extraHeaders']['x-federation'] = fed_json['x-federation']
        fed_json = json.dumps(fed_json, separators=(',', ':'))
    return fed_json, ''


def build_raw_data(args, fed_id):
    with open("template_json/template_raw_data.json") as f:
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


def build_data_join_ticket(args, fed_id, raw_name):
    with open("template_json/template_join_ticket.json") as f:
        ticket_json = json.load(f)
        name_suffix = '-join-ticket'
        ticket_json['name'] = args.name + name_suffix
        ticket_json['federation_id'] = fed_id
        ticket_json['sdk_version'] = args.image.split(':')[-1]
        ticket_json['expire_time'] = str(datetime.datetime.now().year + 1) + '-12-31'
        fl_rep_spec = ticket_json['public_params']['spec']['flReplicaSpecs']
        master_containers = fl_rep_spec['Master']['template']['spec']['containers'][0]
        for d in master_containers['env']:
            if d['name'] == 'RAW_DATA_SUB_DIR':
                d['value'] += raw_name
                break
        master_containers['image'] = args.image
        fl_rep_spec['Worker']['template']['spec']['containers'][0]['image'] = args.image
        ticket_json = json.dumps(ticket_json, separators=(',', ':'))
    return ticket_json, name_suffix


def build_train_ticket(args, fed_id):
    with open("template_json/template_client_train_ticket.json") as f:
        ticket_json = json.load(f)
        name_suffix = '-train-ticket'
        ticket_json['name'] = args.name + name_suffix
        ticket_json['federation_id'] = fed_id
        ticket_json['sdk_version'] = args.image.split(':')[-1]
        ticket_json['expire_time'] = str(datetime.datetime.now().year + 1) + '-12-31'
        fl_rep_spec = ticket_json['public_params']['spec']['flReplicaSpecs']
        master_containers = fl_rep_spec['Master']['template']['spec']['containers'][0]
        for d in master_containers['env']:
            if d['name'] == 'DATA_SOURCE':
                d['value'] = args.x_federation + '-join-job'
                break
        master_containers['image'] = args.image
        fl_rep_spec['PS']['template']['spec']['containers'][0]['image'] = args.image
        fl_rep_spec['Worker']['template']['spec']['containers'][0]['image'] = args.image
        ticket_json = json.dumps(ticket_json, separators=(',', ':'))
    return ticket_json, name_suffix


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--name', type=str)
    parser.add_argument('--x-federation', type=str)
    parser.add_argument('--image', type=str)
    parser.add_argument('--url', type=str)
    parser.add_argument('--username', type=str)
    parser.add_argument('--password', type=str)
    parser.add_argument('--api-version')
    args = parser.parse_args()
    args.url = args.url.strip().rstrip('/') + '/api/v' + str(args.api_version)
    cookie = login(args)

    federation_json, suffix = build_federation_json(args)
    federation_id, federation_name = request_and_response(args=args,
                                                          url=args.url + '/federations',
                                                          json_data=federation_json,
                                                          cookies=cookie,
                                                          name_suffix=suffix)

    raw_data_json, suffix = build_raw_data(args, federation_id)
    raw_data_id, raw_data_name = request_and_response(args=args,
                                                      url=args.url + '/raw_data',
                                                      json_data=raw_data_json,
                                                      cookies=cookie,
                                                      name_suffix=suffix)
    requests.post(url=args.url + '/raw_data/' + str(raw_data_id) + '/submit', cookies=cookie)

    join_ticket_json, suffix = build_data_join_ticket(args, federation_id, raw_data_name)
    join_ticket_id, join_ticket_name = request_and_response(args=args,
                                                            url=args.url + '/tickets',
                                                            json_data=join_ticket_json,
                                                            cookies=cookie,
                                                            name_suffix=suffix)

    train_ticket_json, suffix = build_train_ticket(args, federation_id)
    train_ticket_id, train_ticket_name = request_and_response(args=args,
                                                              url=args.url + '/tickets',
                                                              json_data=train_ticket_json,
                                                              cookies=cookie,
                                                              name_suffix=suffix)
    print("Client settings all set. Please wait for server to pull final jobs.")
