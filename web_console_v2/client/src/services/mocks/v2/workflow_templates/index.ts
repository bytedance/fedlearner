import { stringifyWidgetSchemas } from 'shared/formSchema'
import exampleWorkflow from './example'

export const post = {
  data: exampleWorkflow.data,
  status: 200,
}

const fooTpl = stringifyWidgetSchemas(require('./example.json'))
const barTpl = stringifyWidgetSchemas(exampleWorkflow.data as any)
const simpleTpl = {
  id: 1,
  name: 'simple',
  comment: 'simplesimple',
  group_alias: 'test-2',
  config: {
    group_alias: 'test-2',
    is_left: true,
    job_definitions: [
      {
        name: 'Initiative',
        type: 'RAW_DATA',
        is_federated: true,
        variables: [
          {
            name: 'job_name',
            access_mode: 'PEER_WRITABLE',
            widget_schema: '{"component":"Input","type":"string","required":true}',
            value: '',
          },
        ],
        is_manual: false,
        dependencies: [],
        yaml_template: '',
      },
      {
        name: 'Raw data upload',
        type: 'RAW_DATA',
        is_federated: true,
        variables: [
          {
            name: 'job_name2',
            access_mode: 'PEER_WRITABLE',
            widget_schema: '{"component":"Input","type":"string"}',
            value: '',
          },
          {
            name: 'comment2',
            access_mode: 'PRIVATE',
            widget_schema: '{"component":"TextArea","rows":4,"type":"string","required":true}',
            value: '',
          },
        ],
        dependencies: [
          {
            source: 'Initiative',
            type: 3,
          },
        ],
        is_manual: false,
        yaml_template: '',
      },
      {
        name: 'Training',
        type: 'RAW_DATA',
        is_federated: true,
        variables: [
          {
            name: 'job_name2',
            access_mode: 'PEER_READABLE',
            widget_schema: '{"component":"Input","type":"string"}',
            value: '',
          },
        ],
        dependencies: [
          {
            source: 'Raw data upload',
            type: 'ON_COMPLETE',
          },
        ],
        is_manual: false,
        yaml_template: '',
      },
    ],
  },
}

const get = {
  data: {
    data: [simpleTpl, fooTpl, barTpl],
  },
  status: 200,
}

export default get
