#!/usr/bin/env python3
import argparse
import json
import requests
from tools import login, request_and_response, build_raw_data, build_data_join_ticket, build_train_ticket


def build_federation_json(args):
    with open("template_json/template_client_federation.json") as f:
        fed_json = json.load(f)
        fed_json['name'] = args.name
        fed_json['x-federation'] = args.x_federation
        fed_json['trademark'] = args.name
        fed_json['k8s_settings']['grpc_spec']['extraHeaders']['x-federation'] = fed_json['x-federation']
        fed_json = json.dumps(fed_json, separators=(',', ':'))
    return fed_json, ''


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

    raw_data_json, suffix = build_raw_data(args, federation_id, 'template_json/template_raw_data.json')
    raw_data_id, raw_data_name = request_and_response(args=args,
                                                      url=args.url + '/raw_data',
                                                      json_data=raw_data_json,
                                                      cookies=cookie,
                                                      name_suffix=suffix)
    requests.post(url=args.url + '/raw_data/' + str(raw_data_id) + '/submit', cookies=cookie)

    join_ticket_json, suffix = build_data_join_ticket(args, federation_id, raw_data_name,
                                                      'template_json/template_join_ticket.json', 'Leader')
    join_ticket_id, join_ticket_name = request_and_response(args=args,
                                                            url=args.url + '/tickets',
                                                            json_data=join_ticket_json,
                                                            cookies=cookie,
                                                            name_suffix=suffix)

    train_ticket_json, suffix = build_train_ticket(args, federation_id,
                                                   'template_json/template_train_ticket.json', 'Follower')
    train_ticket_id, train_ticket_name = request_and_response(args=args,
                                                              url=args.url + '/tickets',
                                                              json_data=train_ticket_json,
                                                              cookies=cookie,
                                                              name_suffix=suffix)
    print("All set. Please wait for server to pull final jobs.")
