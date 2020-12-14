import { VariableAccessMode } from 'typings/workflow'

// Workflow template demo
const res = {
  data: {
    vaiables: [], // workflow global variables, TBD
    jobs: [
      {
        name: 'Raw Data process',
        type: 1,
        is_federated: true,
        variables: [
          {
            name: 'job_name',
            value: '',
            access_mode: VariableAccessMode.PEER_WRITABLE,
            widget_schema: {
              component: 'Input',
              type: 'string',
            },
          },
          {
            name: 'participant',
            value: 'foobar',
            access_mode: VariableAccessMode.PEER_READABLE,
            widget_schema: {
              component: 'Input',
              type: 'string',
            },
          },
          {
            name: 'job_type',
            value: [1],
            access_mode: VariableAccessMode.PEER_WRITABLE,
            widget_schema: {
              component: 'Select',
              options: {
                type: 'static',
                source: [1, 2],
              },
              multiple: true,
              type: 'number',
            },
          },
          {
            name: 'is_pair',
            value: false,
            access_mode: VariableAccessMode.PEER_WRITABLE,
            widget_schema: {
              component: 'Switch',
              type: 'boolean',
            },
          },
          {
            name: 'comment',
            value: '',
            access_mode: VariableAccessMode.PEER_WRITABLE,
            widget_schema: {
              component: 'TextArea',
              rows: 4,
              type: 'string',
            },
          },
          {
            name: 'cpu_limit',
            value: 0,
            access_mode: VariableAccessMode.PEER_WRITABLE,
            widget_schema: {
              component: 'NumberPicker',
              min: 1,
              max: 80,
              type: 'number',
            },
          },
          {
            name: 'certification',
            value: null,
            access_mode: VariableAccessMode.PEER_WRITABLE,
            widget_schema: {
              component: 'Upload',
              accept: '.crt,.pem',
              action: '/api/v2/upload',
              multiple: true,
              type: 'array',
            },
          },
        ],
        dependencies: [
          {
            // TBD
          },
        ],
        template: 'demo',
      },
    ],
  },
  status: 200,
}

export default res
