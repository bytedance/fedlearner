import { JobType, WorkflowTemplate } from 'typings/workflow';
import { Variable, VariableAccessMode, VariableComponent } from 'typings/variable';
import { DeepPartial } from 'utility-types';

export const gloabalVariables: Variable[] = [
  {
    name: 'image_version',
    value: 'v1.5-rc3',
    access_mode: VariableAccessMode.PEER_READABLE,
    widget_schema: {
      required: true,
    },
  },
  {
    name: 'num_partitions',
    value: '4',
    access_mode: VariableAccessMode.PEER_READABLE,
    widget_schema: '' as any,
  },
  {
    name: 'worker_cpu',
    value: 1,
    access_mode: VariableAccessMode.PRIVATE,
    widget_schema: {
      component: VariableComponent.Select,
      type: 'number',
      required: true,
      options: {
        type: 'static',
        source: [
          { value: 1, label: '1Gi' },
          { value: 2, label: '2Gi' },
        ],
      },
    },
  },
];

export const normalTemplate: { data: DeepPartial<WorkflowTemplate>; status: number } = {
  data: {
    id: 2,
    name: 'Test template',
    group_alias: 'foo group',
    is_left: true,
    config: {
      group_alias: 'foo group',
      variables: gloabalVariables,
      job_definitions: [
        {
          name: 'Initiative',
          job_type: JobType.RAW_DATA,
          is_federated: true,
          dependencies: [],
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
              value: '',
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
          ],
        },
        {
          name: 'Raw data upload',
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
          name: 'Finish/clear',
          job_type: JobType.TREE_MODEL_EVALUATION,
          is_federated: true,
          dependencies: [{ source: 'Training' }],
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
      variables: [],
      job_definitions: [
        {
          name: 'Initiative',
          job_type: JobType.RAW_DATA,
          is_federated: true,
          dependencies: [],
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
          name: 'Raw data process',
          job_type: JobType.NN_MODEL_TRANINING,
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
      variables: [],
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
