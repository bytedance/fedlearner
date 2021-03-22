import requests
from elasticsearch import Elasticsearch

from fedlearner_webconsole.envs import Envs
from fedlearner_webconsole.utils.es_misc import get_es_template, ALIAS_NAME


def _configure_index_alias(es, alias_name):
    # if alias already exists, no need to set write index
    if not es.indices.exists_alias(alias_name):
        # if index with the same name as alias exists, delete it
        if es.indices.exists(alias_name):
            es.indices.delete(alias_name)
        es.indices.create(
            # resolves to alias_name-yyyy.mm.dd-000001 in ES
            f'<{alias_name}-{{now/d}}-000001>',
            body={"aliases": {alias_name: {"is_write_index": True}}}
        )


def _configure_kibana_index_patterns(kibana_addr, index_type):
    if not kibana_addr:
        requests.post(
            url='{}/api/saved_objects/index-pattern/{}'
                .format(kibana_addr, ALIAS_NAME[index_type]),
            json={'attributes': {
                'title': ALIAS_NAME[index_type] + '*',
                'timeFieldName': 'tags.process_time'
                if index_type == 'metrics' else 'tags.event_time'}},
            headers={'kbn-xsrf': 'true',
                     'Content-Type': 'application/json'},
            params={'overwrite': True}
        )


def put_ilm(es, ilm_name, hot_size='50gb', hot_age='10d', delete_age='30d'):
    ilm_body = {
        "policy": {
            "phases": {
                "hot": {
                    "min_age": "0ms",
                    "actions": {
                        "rollover": {
                            "max_size": hot_size,
                            "max_age": hot_age
                        }
                    }
                },
                "delete": {
                    "min_age": delete_age,
                    "actions": {
                        "delete": {}
                    }
                }
            }
        }
    }
    es.ilm.put_lifecycle(ilm_name, body=ilm_body)


def _put_index_template(es, index_type, shards):
    template_name = ALIAS_NAME[index_type] + '-template'
    template_body = get_es_template(index_type, shards=shards)
    es.indices.put_template(template_name, template_body)


if __name__ == '__main__':
    es = Elasticsearch([{'host': Envs.ES_HOST, 'port': Envs.ES_PORT}],
                       http_auth=(Envs.ES_USERNAME, Envs.ES_PASSWORD))
    if int(es.info()['version']['number'].split('.')[0]) == 7:
        es.ilm.start()
        for index_type, alias_name in ALIAS_NAME.items():
            put_ilm(es, 'fedlearner_{}_ilm'.format(index_type))
            _put_index_template(es, index_type, shards=1)
            _configure_index_alias(es, alias_name)
            # Kibana index-patterns initialization
            _configure_kibana_index_patterns(
                Envs.KIBANA_SERVICE_HOST_PORT, index_type
            )
        put_ilm(es, 'filebeat-7.0.1', hot_age='1d')
        # filebeat template should be set during filebeat deployment
        _configure_index_alias(es, 'filebeat-7.0.1')
