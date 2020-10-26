#!/usr/bin/env python3
import argparse
import json
import requests
from tools import login, request_and_response, build_raw_data, \
    build_data_join_ticket, build_nn_ticket, build_tree_ticket


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
    parser.add_argument('--name',
                        type=str,
                        help='Name for peer federation.')
    parser.add_argument('--x-federation',
                        type=str,
                        help='Name for local federation.')
    parser.add_argument('--image',
                        type=str,
                        help='Image address.')
    parser.add_argument('--data-portal-type',
                        type=str,
                        help='Type of raw data, Streaming(default) or PSI.',
                        choices=['Streaming', 'PSI'],
                        default='Streaming')
    parser.add_argument('--model-type',
                        type=str,
                        help='Type of train model, (nn model) or tree model.',
                        choices=['nn_model', 'tree_model'],
                        default='nn_model')
    parser.add_argument('--rsa-key-path',
                        type=str,
                        help='Path to RSA public key.')
    parser.add_argument('--rsa-key-pem',
                        type=str,
                        help='Either rsa key path or rsa key pem must be given.')
    parser.add_argument('--url',
                        type=str,
                        help='URL to webconsole.')
    parser.add_argument('--username',
                        type=str,
                        help='Username of webconsole.')
    parser.add_argument('--password',
                        type=str,
                        help='Password of webconsole.')
    parser.add_argument('--api-version',
                        help='API version of webconsole.',
                        default=1)
    args = parser.parse_args()
    args.streaming = args.data_portal_type == 'Streaming'
    if not args.streaming:
        args.cmd_args = {'Master': ["/app/deploy/scripts/rsa_psi/run_psi_data_join_master.sh"],
                         'Worker': ["/app/deploy/scripts/rsa_psi/run_psi_data_join_worker.sh"]}
        if args.rsa_key_pem is not None:
            args.psi_extras = [{"name": "RSA_KEY_PEM", "value": args.rsa_key_pem}]
        elif args.rsa_key_path is not None:
            args.psi_extras = [{"name": "RSA_KEY_PATH", "value": args.rsa_key_path}]
        else:
            raise Exception('Either RSA_KEY_PEN or RSA_KEY_PATH must be provided when using PSI.')
        args.psi_extras.append({"name": "SIGN_RPC_TIMEOUT_MS", "value": "128000"})

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
                                                      'template_json/template_streaming_join_ticket.json'
                                                      if args.streaming
                                                      else 'template_json/template_psi_join_ticket.json',
                                                      'Leader' if args.streaming else 'Follower')
    join_ticket_id, join_ticket_name = request_and_response(args=args,
                                                            url=args.url + '/tickets',
                                                            json_data=join_ticket_json,
                                                            cookies=cookie,
                                                            name_suffix=suffix)

    if args.model_type == 'nn_model':
        train_ticket_json, suffix = build_nn_ticket(args, federation_id,
                                                    'template_json/template_nn_ticket.json', 'Follower')
    else:
        train_ticket_json, suffix = build_tree_ticket(args, federation_id,
                                                      'template_json/template_tree_ticket.json', 'Follower')
    train_ticket_id, train_ticket_name = request_and_response(args=args,
                                                              url=args.url + '/tickets',
                                                              json_data=train_ticket_json,
                                                              cookies=cookie,
                                                              name_suffix=suffix)
    print("All set. Please wait for server to pull final jobs.")
