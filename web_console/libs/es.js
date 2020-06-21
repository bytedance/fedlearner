// Kubernetes Client
const got = require('got');
const json = require('koa-json');

let config;
try {
    config = require('../server.config');
} catch (err) {
    config = require('../constants').DEFAULT_SERVER_CONFIG;
}

class ElasticSearchClient {
    constructor() {
        // TODO: use HTTPs for production
        const prefixUrl = `http://${process.env.ES_HOST || config.ES_HOST}:${process.env.ES_PORT || config.ES_PORT}`;
        this.client = got.extend({
            prefixUrl,
            responseType: 'json',
        });
    }

    async queryLog(index, keyword, pod_name, start_time, end_time) {
        let query_body = {
            "sort": [
                {
                    "@timestamp": {
                        "order": "asc",
                        "unmapped_type": "boolean"
                    }
                }
            ],
            "_source": ["message"],
            "query": {
                "bool": {
                    "must": [
                        {
                            "query_string": {
                                "query": `\"${keyword}\"`,
                                "analyze_wildcard": true,
                                "default_field": "*"
                            }
                        },
                        {
                            "match_phrase": {
                                "kubernetes.pod.name": {
                                    "query": pod_name
                                }
                            }
                        },
                        {
                            "range": {
                                "@timestamp": {
                                    "gte": start_time,
                                    "lte": end_time,
                                    "format": "epoch_millis"
                                }
                            }
                        }
                    ]
                }
            }
        }

        const { body } = await this.client.post(`${index}/_search`, { json: query_body })
        var logs = new Array();
        for (var key in body.hits.hits) {
            logs.push(body.hits.hits[key]['_source']['message'])
        }
        return logs;
    }
}

module.exports = ElasticSearchClient;