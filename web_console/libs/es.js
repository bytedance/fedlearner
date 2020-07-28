/**
 * Elastic Search Client
 */

const ky = require('ky-universal');

const getConfig = require('../utils/get_confg');

const config = getConfig({
  ES_HOST: process.env.ES_HOST,
  ES_PORT: process.env.ES_PORT,
});

class ElasticSearchClient {
  constructor() {
    const prefixUrl = `http://${config.ES_HOST}:${config.ES_PORT}`;
    this.client = ky.create({ prefixUrl });
  }

  async queryLog(index, keyword, pod_name, start_time, end_time, match_phrase) {
    let query_body = {
      "version": true,
      "size": 50000,
      "sort": [
        {
          "log.offset": {
            "order": "desc"
          }
        }
      ],
      "_source": ["message"],
      "query": {
        "bool": {
          "must": (
            keyword
              ? [{
                "query_string": {
                  "query": `\"${keyword}\"`,
                  "analyze_wildcard": true,
                  "default_field": "*"
                }
              }]
              : []
          ).concat([
            match_phrase
              ? match_phrase
              : {
                "prefix": {
                  "kubernetes.pod.name": pod_name
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
          ])
        }
      }
    }

    const response = await this.client.post(`${index}/_search`, { json: query_body });
    const body = await response.json();
    return Object.keys(body.hits.hits).map(x => body.hits.hits[x]['_source']['message']);
  }
}

module.exports = new ElasticSearchClient();
