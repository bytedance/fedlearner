#!/usr/bin/env python3
import argparse
import base64
import json
import time
from http import HTTPStatus

import requests


def login(base_url, username, password):
    login_url = base_url + '/auth/signin'
    print(login_url)
    password = base64.b64encode(password.encode()).decode()
    print(password)
    response = requests.post(
        login_url,
        data={
            'username': username,
            'password': password
        }
    )
    if response.status_code != HTTPStatus.OK:
        print(response)
        return None
    response = json.loads(response.content)
    if 'data' not in response:
        return None
    token = response['data'].get('access_token')
    return token
    #return json.loads(response.data).get('data')


def read_spark_json():
    # with open("template_json/spark.json") as f:
    #     fed_json = json.load(f)
    #     fed_json = json.dumps(fed_json)
    # return fed_json
    return {
        "name": "lq-test",
        "py_files": ["hdfs://haruna/user/liuqi.nolan/data/output4/raw_data/lq-test/upload/deps.zip"],
        "image_url": "hub.byted.org/fedlearner/fedlearner_dataflow:787375b9940105a0ca11cff5b3f6c7f7",
        "driver_config": {"cores": 4, "memory": "5g"},
        "executor_config": {"cores": 2, "memory": "5g", "instances": 32},
        "command": ["--config", "hdfs://haruna/user/liuqi.nolan/data/output4/raw_data/lq-test/upload/raw_data_0.config"],
        "main_application": "hdfs://haruna/user/liuqi.nolan/data/output4/raw_data/lq-test/upload/raw_data.py"
    }



if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--url',
                        type=str,
                        help='URL to webconsole.',
                        default='http://fl-v2.bytedance.net')
    parser.add_argument('--username',
                        type=str,
                        help='Username of webconsole.',
                        default='ada')
    parser.add_argument('--password',
                        type=str,
                        help='Password of webconsole.',
                        default='fl@12345.')
    parser.add_argument('--api-version',
                        help='API version of webconsole.',
                        default=2)
    args = parser.parse_args()

    args.url = args.url.strip().rstrip('/') + '/api/v' + str(args.api_version)
    spark_url = args.url + "/sparkapps"
    access_token = login(args.url, args.username, args.password)
    if access_token:
        print(access_token)
        print("login succeeded")
    else:
        print("login failed")
        exit(-1)
    spark_job_json = read_spark_json()
    print(spark_job_json)
    headers = {
        'Authorization': f'Bearer {access_token}'
    }
    print(spark_url)
    # response = requests.post(url=spark_url,
    #                          json=spark_job_json,
    #                          headers=headers)
    #
    # try:
    #     response = json.loads(response.text)
    #     print(response)
    # except json.decoder.JSONDecodeError:
    #     print('Json data to be sent:', spark_job_json)
    #     raise Exception('404 error encountered when building/modifying {}. '
    #                     'Please check whether webconsole api '
    #                     'changed.'.format(spark_url.split('/')[-1]))

    spark_get_url = spark_url + "/raw-data-lq-test-0"
    response = requests.get(url=spark_get_url, headers=headers)
    try:
        response = json.loads(response.text)
        print("get response", response)
    except json.decoder.JSONDecodeError:
        print('Json data to be sent:', spark_job_json)
        raise Exception('404 error encountered when building/modifying {}. '
                        'Please check whether webconsole api '
                        'changed.'.format(spark_url.split('/')[-1]))

    # time.sleep(20)
    # response = requests.delete(spark_job_url, headers=headers)
    # response = json.loads(response.text)
    # print("delete response", response)
