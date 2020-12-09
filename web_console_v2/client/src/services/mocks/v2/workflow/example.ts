import { VariableAccessMode } from 'typings/variables'

// Workflow template demo
const res = {
  data: {
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
            },
          },
          {
            name: 'participant',
            value: 'foobar',
            access_mode: VariableAccessMode.PEER_READABLE,
            widget_schema: {
              component: 'Input',
            },
          },
          {
            name: 'job_type',
            value: 1,
            access_mode: VariableAccessMode.PEER_WRITABLE,
            widget_schema: {
              component: 'Select',
              options: {
                type: 'static',
                source: [1, 2],
              },
              multiple: true,
            },
          },
          {
            name: 'is_pair',
            value: false,
            access_mode: VariableAccessMode.PEER_WRITABLE,
            widget_schema: {
              component: 'Switch',
            },
          },
          {
            name: 'comment',
            value: '',
            access_mode: VariableAccessMode.PEER_WRITABLE,
            widget_schema: {
              component: 'TextArea',
              rows: 4,
            },
          },
          {
            name: 'cpu_limit',
            value: 0,
            access_mode: VariableAccessMode.PEER_WRITABLE,
            widget_schema: {
              component: 'NumberPicker',
              min: 1,
              max: 90,
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
            },
          },
        ],
        dependencies: [
          {
            /** TBD */
          },
        ],
        template: 'demo',
      },
    ],
  },
  status: 200,
}

export default res
