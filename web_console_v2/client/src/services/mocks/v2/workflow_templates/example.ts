import { VariableAccessMode, VariableComponent, WorkflowTemplate } from 'typings/workflow'
import { DeepPartial } from 'utility-types'

// Workflow template demo
const get: { data: DeepPartial<WorkflowTemplate>; status: number } = {
  data: {
    id: 1,
    name: 'bar template',
    group_alias: 'foo group',
    config: {
      variables: [], // workflow global variables, TBD
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
                component: VariableComponent.Input,
                type: 'string',
              },
            },
            {
              name: 'participant',
              value: 'foobar',
              access_mode: VariableAccessMode.PEER_READABLE,
              widget_schema: {
                component: VariableComponent.Input,
                type: 'string',
              },
            },
            {
              name: 'job_type',
              value: [1],
              access_mode: VariableAccessMode.PEER_WRITABLE,
              widget_schema: {
                component: VariableComponent.Select,
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
                component: VariableComponent.Switch,
                type: 'boolean',
              },
            },
            {
              name: 'comment',
              value: '',
              access_mode: VariableAccessMode.PEER_WRITABLE,
              widget_schema: {
                component: VariableComponent.TextArea,
                rows: 4,
                type: 'string',
              },
            },
            {
              name: 'cpu_limit',
              value: 0,
              access_mode: VariableAccessMode.PEER_WRITABLE,
              widget_schema: {
                component: VariableComponent.NumberPicker,
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
                component: VariableComponent.Upload,
                accept: '.crt,.pem',
                action: '/api/v2/upload',
                multiple: true,
                type: 'array',
              },
            },
          ],
        },
      ],
    },
  },
  status: 200,
}

export default get
