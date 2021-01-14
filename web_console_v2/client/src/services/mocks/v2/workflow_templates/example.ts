import {
  JobDependencyType,
  JobType,
  VariableAccessMode,
  VariableComponent,
  WorkflowTemplate,
} from 'typings/workflow';
import { DeepPartial } from 'utility-types';

// Workflow template demo
const get: { data: DeepPartial<WorkflowTemplate>; status: number } = {
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
          type: JobType.RAW_DATA,
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
          type: JobType.RAW_DATA,
          is_federated: true,
          dependencies: [{ source: 'Initiative', type: JobDependencyType.MANUAL }],
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
          type: JobType.NN_MODEL_TRANINING,
          is_federated: true,
          dependencies: [{ source: 'Initiative', type: JobDependencyType.MANUAL }],
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
          type: JobType.RAW_DATA,
          is_federated: true,
          dependencies: [{ source: 'Initiative', type: JobDependencyType.MANUAL }],
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
          type: JobType.NN_MODEL_TRANINING,
          is_federated: true,
          dependencies: [
            { source: 'Raw data upload', type: JobDependencyType.ON_COMPLETE },
            { source: 'Raw data process', type: JobDependencyType.ON_COMPLETE },
            { source: 'Raw data save', type: JobDependencyType.ON_COMPLETE },
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
          type: JobType.TREE_MODEL_EVALUATION,
          is_federated: true,
          dependencies: [{ source: 'Training', type: JobDependencyType.ON_COMPLETE }],
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

export default get;
