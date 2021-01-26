import { JobType, VariableAccessMode, VariableComponent, WorkflowTemplate } from 'typings/workflow';
import { DeepPartial } from 'utility-types';

// Workflow template demo
const exampleTemplate: { data: DeepPartial<WorkflowTemplate>; status: number } = {
  data: {
    id: 2,
    name: 'bar template',
    group_alias: 'foo group',
    is_left: true,
    config: {
      group_alias: 'foo group',
      variables: [], // workflow global variables, TBD
      job_definitions: [
        {
          name: 'Initiative',
          job_type: JobType.RAW_DATA,
          is_federated: true,
          variables: [
            {
              name: 'job_name',
              value: '',
              access_mode: VariableAccessMode.PEER_WRITABLE,
              widget_schema: {
                component: VariableComponent.Input,
                type: 'string',
                required: true,
              },
            },
            {
              name: 'participant',
              value: 'foobar',
              access_mode: VariableAccessMode.PEER_READABLE,
              widget_schema: {
                component: VariableComponent.Input,
                type: 'string',
                required: true,
              },
            },
            {
              name: 'job_type',
              value: '1',
              access_mode: VariableAccessMode.PEER_READABLE,
              widget_schema: {
                component: VariableComponent.Select,
                options: {
                  type: 'static',
                  source: [1, 2],
                },
                multiple: true,
                type: 'number',
                required: true,
              },
            },
            {
              name: 'is_pair',
              value: '',
              access_mode: VariableAccessMode.PRIVATE,
              widget_schema: {
                component: VariableComponent.Switch,
                type: 'boolean',
              },
            },
            {
              name: 'comment',
              value: '',
              access_mode: VariableAccessMode.PEER_READABLE,
              widget_schema: {
                component: VariableComponent.TextArea,
                rows: 4,
                type: 'string',
              },
            },
            {
              name: 'cpu_limit',
              value: '10',
              access_mode: VariableAccessMode.PRIVATE,
              widget_schema: {
                component: VariableComponent.NumberPicker,
                min: 1,
                max: 80,
                type: 'number',
              },
            },
            {
              name: 'certification',
              value: '',
              access_mode: VariableAccessMode.PEER_WRITABLE,
              widget_schema: {
                component: VariableComponent.Upload,
                accept: '.crt,.pem',
                action: '/api/v2/upload',
                type: 'array',
              },
            },
          ],
        },
        {
          name: 'Raw data upload',
          job_type: JobType.RAW_DATA,
          is_federated: true,
          dependencies: [{ source: 'Initiative' }],
          variables: [
            {
              name: 'job_name2',
              value: '',
              access_mode: VariableAccessMode.PEER_WRITABLE,
              widget_schema: {
                component: VariableComponent.Input,
                type: 'string',
              },
            },
            {
              name: 'comment2',
              value: '',
              access_mode: VariableAccessMode.PRIVATE,
              widget_schema: {
                component: VariableComponent.TextArea,
                rows: 4,
                type: 'string',
                required: true,
              },
            },
          ],
        },

        {
          name: 'Raw data process',
          job_type: JobType.NN_MODEL_TRANINING,
          is_federated: true,
          dependencies: [{ source: 'Initiative' }],
          variables: [
            {
              name: 'job_name3',
              value: '',
              access_mode: VariableAccessMode.PEER_WRITABLE,
              widget_schema: {
                component: VariableComponent.Input,
                type: 'string',
                required: true,
              },
            },
          ],
        },
        {
          name: 'Raw data save',
          job_type: JobType.RAW_DATA,
          is_federated: true,
          dependencies: [{ source: 'Initiative' }],
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
          ],
        },
        {
          name: 'Training',
          job_type: JobType.NN_MODEL_TRANINING,
          is_federated: true,
          dependencies: [
            { source: 'Raw data upload' },
            { source: 'Raw data process' },
            { source: 'Raw data save' },
          ],
          variables: [
            {
              name: 'job_name2',
              value: '',
              access_mode: VariableAccessMode.PEER_WRITABLE,
              widget_schema: {
                component: VariableComponent.Input,
                type: 'string',
              },
            },
          ],
        },
        {
          name: 'Finish/clear',
          job_type: JobType.TREE_MODEL_EVALUATION,
          is_federated: true,
          dependencies: [{ source: 'Training' }],
          variables: [
            {
              name: 'job_name6',
              value: '',
              access_mode: VariableAccessMode.PEER_WRITABLE,
              widget_schema: {
                component: VariableComponent.Input,
                type: 'string',
              },
            },
          ],
        },
      ],
    },
  },
  status: 200,
};

export const complexDepsTemplate: { data: DeepPartial<WorkflowTemplate>; status: number } = {
  data: {
    id: 10,
    name: 'Complex deps template',
    group_alias: 'c-group',
    is_left: true,
    config: {
      group_alias: 'c-group',
      job_definitions: [
        {
          name: 'Initiative',
          job_type: JobType.RAW_DATA,
          is_federated: true,
          variables: [
            {
              name: 'job_name',
              value: '',
              access_mode: VariableAccessMode.PEER_WRITABLE,
              widget_schema: {
                component: VariableComponent.Input,
                type: 'string',
                required: true,
              },
            },
          ],
        },
        {
          name: 'Raw data upload',
          job_type: JobType.RAW_DATA,
          is_federated: true,
          dependencies: [{ source: 'Initiative' }],
          variables: [
            {
              name: 'job_name2',
              value: '',
              access_mode: VariableAccessMode.PEER_WRITABLE,
              widget_schema: {
                component: VariableComponent.Input,
                type: 'string',
              },
            },
          ],
        },

        {
          name: 'Raw data process',
          job_type: JobType.NN_MODEL_TRANINING,
          is_federated: true,
          dependencies: [{ source: 'Initiative' }],
          variables: [
            {
              name: 'job_name3',
              value: '',
              access_mode: VariableAccessMode.PEER_WRITABLE,
              widget_schema: {
                component: VariableComponent.Input,
                type: 'string',
                required: true,
              },
            },
          ],
        },
        {
          name: 'Raw data save',
          job_type: JobType.RAW_DATA,
          is_federated: true,
          dependencies: [{ source: 'Initiative' }],
          variables: [],
        },
        {
          name: 'Training',
          job_type: JobType.NN_MODEL_TRANINING,
          is_federated: true,
          dependencies: [{ source: 'Raw data upload' }, { source: 'Raw data process' }],
          variables: [
            {
              name: 'job_name2',
              value: '',
              access_mode: VariableAccessMode.PEER_WRITABLE,
              widget_schema: {
                component: VariableComponent.Input,
                type: 'string',
              },
            },
          ],
        },
        {
          name: 'Finish/clear',
          job_type: JobType.TREE_MODEL_EVALUATION,
          is_federated: true,
          dependencies: [{ source: 'Training' }, { source: 'Raw data save' }],
          variables: [
            {
              name: 'job_name6',
              value: '',
              access_mode: VariableAccessMode.PEER_WRITABLE,
              widget_schema: {
                component: VariableComponent.Input,
                type: 'string',
              },
            },
          ],
        },
      ],
    },
  },
  status: 200,
};

export const xShapeTemplate: { data: DeepPartial<WorkflowTemplate> } = {
  data: {
    id: 10,
    name: 'X Shape template',
    group_alias: 'x-group',
    is_left: true,
    config: {
      group_alias: 'x-group',
      job_definitions: [
        {
          name: '1-1',
          job_type: JobType.RAW_DATA,
          is_federated: true,
          variables: [],
        },
        {
          name: '1-2',
          job_type: JobType.RAW_DATA,
          is_federated: true,
          variables: [],
        },
        {
          name: '2-1',
          job_type: JobType.RAW_DATA,
          is_federated: true,
          dependencies: [{ source: '1-2' }],
          variables: [],
        },
        {
          name: '2-2',
          job_type: JobType.RAW_DATA,
          is_federated: true,
          dependencies: [{ source: '1-1' }],
          variables: [],
        },
      ],
    },
  },
};
export default exampleTemplate;
