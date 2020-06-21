const assert = require('assert');
const ElasticSearchClient = require('../../libs/es');

let es_client;

describe('ElasticSearch Client', () => {
    before(() => {
        es_client = new ElasticSearchClient();
    });

    describe('query log from  elastic search', () => {
        it('should query log from elastic search', async () => {
            const logs = await es_client.queryLog(
                'filebeat-7.0.1-*',
                'test-produce-psi-preprocessor',
                'flapp-operator-6845d4d9d5-wpdqx',
                1592627446768,
                1592713846768)
            assert.ok(logs, Array.isArray(logs))
        });
    });
})