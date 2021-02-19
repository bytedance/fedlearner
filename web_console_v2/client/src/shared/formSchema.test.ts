import buildFormSchemaFromJobDef, {
  stringifyWidgetSchemas,
  parseWidgetSchemas,
} from './formSchema';
import { Job, JobType } from 'typings/job';
import { Variable, VariableAccessMode, VariableComponent } from 'typings/variable';
import { render, cleanup, screen } from '@testing-library/react';
import { normalTemplate } from 'services/mocks/v2/workflow_templates/examples';
import { withExecutionDetail } from 'services/mocks/v2/workflows/examples';
import { WorkflowTemplatePayload } from 'typings/workflow';

const unassignedComponent: Variable = {
  name: 'component_unassigned',
  value: '',
  access_mode: VariableAccessMode.PEER_READABLE,
  widget_schema: {},
};

const nameInput: Variable = {
  name: 'some_name',
  value: 'initial value',
  access_mode: VariableAccessMode.PEER_READABLE,
  widget_schema: {
    component: VariableComponent.Input,
    type: 'string',
    tooltip: 'some hints',
  },
};

const memSelect: Variable = {
  name: 'worker_mem',
  value: 2,
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
    placeholder: '请选择内存',
  },
};

const asyncSwitch: Variable = {
  name: 'is_async',
  value: false,
  access_mode: VariableAccessMode.PEER_WRITABLE,
  widget_schema: {
    component: VariableComponent.Switch,
    label: '是否异步',
    type: 'boolean',
    checkedChildren: 'Async mode',
    unCheckedChildren: 'Synchronous mode',
  },
};

const cpuLimit: Variable = {
  name: 'cpu_limit',
  value: false,
  access_mode: VariableAccessMode.PRIVATE,
  widget_schema: {
    component: VariableComponent.NumberPicker,
    type: 'number',
    min: 10,
    max: 100,
  },
};

const commentTextArea: Variable = {
  name: 'comment',
  value: '',
  access_mode: VariableAccessMode.PEER_WRITABLE,
  widget_schema: {
    component: VariableComponent.TextArea,
    type: 'string',
    rows: 6,
    showCount: true,
    placeholder: '备注',
  },
};

const testJobDef: Job = {
  name: 'Test job',
  job_type: JobType.RAW_DATA,
  is_federated: false,
  dependencies: [],
  variables: [unassignedComponent, nameInput, memSelect, asyncSwitch, cpuLimit, commentTextArea],
};

describe('Build a form schema with various components (without permissions)', () => {
  const schema = buildFormSchemaFromJobDef(testJobDef);
  const fields = schema.properties!;

  afterEach(cleanup);

  it('Should turn each variable to schema-property correctly', () => {
    const { some_name, worker_mem, is_async, cpu_limit, comment } = fields;

    expect(some_name.required).toBeFalsy();
    expect(some_name.default).toBe('initial value');
    // auto generate a simple placeholder
    expect(some_name['x-component-props']?.placeholder).toBe('请输入 some_name');

    expect(worker_mem.required).toBeTruthy();
    expect(worker_mem.default).toBe(2);
    expect(worker_mem.enum).toEqual([
      { value: 1, label: '1Gi' },
      { value: 2, label: '2Gi' },
    ]);
    expect(worker_mem.display).toBeTruthy();

    expect(is_async['x-component-props']?.checkedChildren).toBe('Async mode');

    expect(cpu_limit['x-component-props']?.max).toBe(100);
    // placeholder from variablePresets
    expect(cpu_limit['x-component-props']?.placeholder).toBe('请输入CPU最大使用率');

    expect(comment['x-component-props']?.placeholder).toBe('备注');
    expect(comment['x-component-props']?.rows).toBe(6);
    expect(comment['x-component-props']?.showCount).toBeTruthy();
  });

  it('Using Input as default variable component', () => {
    expect(fields.component_unassigned['x-component']).toBe(VariableComponent.Input);
  });

  it("Server-side's config is always priority to presets", () => {
    expect(fields.worker_mem['x-component-props']?.placeholder).toBe('请选择内存');
  });

  it('If the label is given, use it instead of name as Variable label', () => {
    render(fields.is_async.title as any);
    const label = screen.getByRole('label');
    expect(label.textContent).toBe('是否异步');
  });

  it('Give the label without tooltip', () => {
    render(fields.worker_mem.title as any);
    const label = screen.getByRole('label');
    expect(label.textContent).toContain('worker_mem');
  });

  it('Give the label with tooltip', () => {
    render(fields.some_name.title as any);
    const label = screen.getByRole('label');
    expect(label.innerHTML).toContain('anticon-question-circle');
  });
});

describe('Build a form schema with permissions', () => {
  const schema = buildFormSchemaFromJobDef(testJobDef, { withPermissions: true });
  const fields = schema.properties!;

  it('Permission check', () => {
    expect(fields.some_name.readOnly).toBeTruthy();

    expect(fields.is_async.readOnly).toBeFalsy();
    expect(fields.is_async.display).toBeTruthy();

    expect(fields.cpu_limit.display).toBeFalsy();
    expect(fields.worker_mem.display).toBeFalsy();
  });
});

describe('Stringify all Widget schemas inside a workflow config before send to server', () => {
  it('stringifyWidgetSchemas should works fine', () => {
    const stringified = stringifyWidgetSchemas(normalTemplate.data as WorkflowTemplatePayload);

    expect(
      stringified.config.variables.every((item) => typeof item.widget_schema === 'string'),
    ).toBeTruthy();

    expect(
      stringified.config.job_definitions.every((job) => {
        return job.variables.every((item) => typeof item.widget_schema === 'string');
      }),
    ).toBeTruthy();
  });
});

describe('Parse all Widget schemas inside a workflow config from server side', () => {
  it('parseWidgetSchemas should works fine', () => {
    // Before is string type
    expect(
      withExecutionDetail.config!.variables.every((item) => typeof item.widget_schema === 'string'),
    ).toBeTruthy();
    expect(
      withExecutionDetail.config!.job_definitions.every((job) => {
        return job.variables.every((item) => typeof item.widget_schema === 'string');
      }),
    ).toBeTruthy();

    const parsed = parseWidgetSchemas(withExecutionDetail);

    expect(
      parsed.config!.variables.every((item) => typeof item.widget_schema === 'object'),
    ).toBeTruthy();

    expect(
      parsed.config!.job_definitions.every((job) => {
        return job.variables.every((item) => typeof item.widget_schema === 'object');
      }),
    ).toBeTruthy();
  });
});
