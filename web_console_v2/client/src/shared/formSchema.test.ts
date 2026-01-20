import buildFormSchemaFromJobDef, {
  stringifyComplexDictField,
  parseComplexDictField,
  parseVariableToFormValue,
  stringifyVariableValue,
  parseVariableValue,
  JOB_NAME_PREFIX,
  processTypedValue,
  processVariableTypedValue,
} from './formSchema';
import { Job, JobType } from 'typings/job';
import { VariableComponent, VariableValueType } from 'typings/variable';
import { render, cleanup, screen } from '@testing-library/react';
import {
  normalTemplate,
  noTypedValueTemplate,
} from 'services/mocks/v2/workflow_templates/examples';
import {
  withExecutionDetail,
  pendingAcceptAndConfig,
  newlyCreated,
  completed,
} from 'services/mocks/v2/workflows/examples';
import {
  unassignedComponent,
  nameInput,
  memSelect,
  asyncSwitch,
  cpuLimit,
  commentTextArea,
  codeEditor,
  datasetSelect,
  datasetPathSelect,
  featureSelect,
  envsInput,
  stringInput,
  objectInput,
  listInput,
  forceObjectInput,
  forceListInput,
} from 'services/mocks/v2/variables/examples';
import { WorkflowTemplatePayload } from 'typings/workflow';
import { cloneDeep } from 'lodash-es';

const testJobDef: Job = {
  name: 'Test-job',
  job_type: JobType.RAW_DATA,
  is_federated: false,
  dependencies: [],
  variables: [
    unassignedComponent,
    nameInput,
    memSelect,
    asyncSwitch,
    cpuLimit,
    commentTextArea,
    codeEditor,
    datasetSelect,
    datasetPathSelect,
    featureSelect,
    envsInput,
    stringInput,
    objectInput,
    listInput,
    forceObjectInput,
    forceListInput,
  ],
};

describe('Build a form schema with various components (without permissions)', () => {
  const schema = buildFormSchemaFromJobDef(testJobDef);
  const fields = schema.properties![JOB_NAME_PREFIX + testJobDef.name].properties!;

  afterEach(cleanup);

  it('Should turn each variable to schema-property correctly', () => {
    const { some_name, worker_mem, is_async, cpu_limit, comment } = fields;

    expect(some_name.required).toBeFalsy();
    expect(some_name.default).toBe('initial value');
    // if has tooltip, use tooltip as placeholder
    expect(some_name['x-component-props']?.placeholder).toBe('some hints');

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
    expect(label.innerHTML).toContain('some hints');
  });

  describe('Render correct default value', () => {
    it('Input component with string value_type', () => {
      expect(fields.string_input.default).toBe(stringInput.value);
    });
    it('Input component with object value_type', () => {
      expect(fields.object_input.default).toBe(objectInput.value);
      expect(fields.force_object_input.default).toBe(JSON.stringify(forceObjectInput.typed_value));
    });
    it('Input component with list value_type', () => {
      expect(fields.list_input.default).toBe(listInput.value);
      expect(fields.force_list_input.default).toBe(JSON.stringify(forceListInput.typed_value));
    });
  });
});

describe('Build a form schema with permissions', () => {
  const schema = buildFormSchemaFromJobDef(testJobDef, { withPermissions: true });
  const fields = schema.properties![JOB_NAME_PREFIX + testJobDef.name].properties!;

  it('Permission check', () => {
    expect(fields.some_name.readOnly).toBeTruthy();

    expect(fields.is_async.readOnly).toBeFalsy();
    expect(fields.is_async.display).toBeTruthy();

    expect(fields.cpu_limit.display).toBeFalsy();
    expect(fields.worker_mem.display).toBeFalsy();
  });
});

describe('Build a form schema with readonly', () => {
  const schema = buildFormSchemaFromJobDef(testJobDef, { readonly: true });
  const fields = schema.properties![JOB_NAME_PREFIX + testJobDef.name].properties!;

  it('Readonly check', () => {
    expect(
      Object.keys(fields).every((key) => {
        const field = fields[key];
        return field.readOnly === true;
      }),
    ).toBeTruthy();
  });
});

describe('Build a form schema with variablePrefix', () => {
  const variablePrefix = 'prefixName__';
  const schema = buildFormSchemaFromJobDef(testJobDef, { variablePrefix: variablePrefix });
  const fields = schema.properties![JOB_NAME_PREFIX + testJobDef.name].properties!;

  const regx = new RegExp(`^${variablePrefix}`);

  it('VariablePrefix check', () => {
    expect(
      Object.keys(fields).every((key) => {
        return regx.test(key);
      }),
    ).toBeTruthy();
  });
});

describe('Stringify all Widget schemas inside a workflow config before send to server', () => {
  it('stringifyComplexDictField should works fine', () => {
    const stringified = stringifyComplexDictField(normalTemplate as WorkflowTemplatePayload);
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
  it('parseComplexDictField should works fine', () => {
    // Before is string type
    expect(
      withExecutionDetail.config!.variables.every((item) => typeof item.widget_schema === 'string'),
    ).toBeTruthy();
    expect(
      withExecutionDetail.config!.job_definitions.every((job) => {
        return job.variables.every((item) => typeof item.widget_schema === 'string');
      }),
    ).toBeTruthy();

    const parsed = parseComplexDictField(withExecutionDetail);

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

it('parseVariableToFormValue should works fine', () => {
  expect(parseVariableToFormValue({} as any)).toEqual({});
  expect(parseVariableToFormValue(pendingAcceptAndConfig)).toEqual({});
  expect(parseVariableToFormValue(newlyCreated)).toEqual({
    comment2: '3',
    image_version: 'v1.5-rc3',
    job_name: '1',
    job_name2: '4',
  });
  expect(parseVariableToFormValue(withExecutionDetail)).toEqual({
    comment2: '3',
    image_version: 'v1.5-rc3',
    job_name: '1',
    job_name2: '4',
  });
  expect(parseVariableToFormValue(completed)).toEqual({
    comment: '',
    comment2: '',
    cpu_limit: '10',
    image_version: 'v1.5-rc3',
    is_pair: '',
    job_name: '',
    job_type: '1',
    num_partitions: '4',
    participant: '',
    worker_cpu: 1,
  });

  expect(
    parseVariableToFormValue({
      config: {
        variables: [{ name: 'image', value: undefined }],
        job_definitions: [
          {
            variables: [{ name: 'image', value: '123' }],
          },
        ],
      },
    } as any),
  ).toEqual({
    image: '123',
  });

  expect(
    parseVariableToFormValue({
      config: {
        variables: [{ name: 'image', value: '123' }],
        job_definitions: [
          {
            variables: undefined,
          },
          {
            variables: [{ name: 'v1', value: 'v1' }],
          },
        ],
      },
    } as any),
  ).toEqual({
    image: '123',
    v1: 'v1',
  });
});

it('stringifyVariableValue should works fine', () => {
  const test1 = { ...codeEditor, value_type: VariableValueType.CODE };
  expect(typeof test1.value).toBe('object');
  stringifyVariableValue(test1);
  expect(typeof test1.value).toBe('string');
  const test2 = {
    ...codeEditor,
    value_type: VariableValueType.CODE,
    value: JSON.stringify({ 'main.js': 'var a = 1;' }),
  };
  expect(typeof test2.value).toBe('string');
  stringifyVariableValue(test2);
  expect(typeof test2.value).toBe('string');

  const test3 = { ...nameInput, value_type: VariableValueType.STRING, value: 1 };
  expect(typeof test3.value).toBe('number');
  stringifyVariableValue(test3);
  expect(test3.value).toBe('1');
  const test4 = { ...nameInput, value_type: VariableValueType.STRING, value: '1' };
  stringifyVariableValue(test4);
  expect(test4.value).toBe('1');

  const test5 = { ...nameInput, value_type: VariableValueType.BOOLEAN, value: 'true' };
  expect(typeof test5.value).toBe('string');
  stringifyVariableValue(test5);
  expect(test5.value).toBe('true');
  const test6 = { ...nameInput, value_type: VariableValueType.BOOLEAN, value: true };
  expect(typeof test6.value).toBe('boolean');
  stringifyVariableValue(test6);
  expect(test6.value).toBe('true');

  const test7 = { ...envsInput };
  expect(typeof test7.value).toBe('object');
  expect(Array.isArray(test7.value)).toBe(true);
  stringifyVariableValue(test7);
  expect(typeof test1.value).toBe('string');
});

it('parseVariableValue should works fine', () => {
  const test1 = { ...codeEditor, value_type: VariableValueType.CODE };
  expect(typeof test1.value).toBe('object');
  parseVariableValue(test1);
  expect(typeof test1.value).toBe('object');
  const test2 = {
    ...codeEditor,
    value_type: VariableValueType.CODE,
    value: JSON.stringify({ 'main.js': 'var a = 1;' }),
  };
  expect(typeof test2.value).toBe('string');
  parseVariableValue(test2);
  expect(typeof test2.value).toBe('object');

  const test3 = { ...envsInput };
  expect(typeof test3.value).toBe('object');
  parseVariableValue(test3);
  expect(typeof test3.value).toBe('object');
  expect(Array.isArray(test3.value)).toBe(true);
  const test4 = {
    ...envsInput,
    value: JSON.stringify([
      { name: 'n1', value: 'v1' },
      { name: 'n2', value: 'v2' },
    ]),
  };
  expect(typeof test4.value).toBe('string');
  parseVariableValue(test4);
  expect(typeof test4.value).toBe('object');
  expect(Array.isArray(test4.value)).toBe(true);

  const test5 = {
    ...codeEditor,
    value_type: VariableValueType.NUMBER,
    value: '123',
  };
  expect(typeof test5.value).toBe('string');
  parseVariableValue(test5);
  expect(typeof test5.value).toBe('number');
  const test6 = {
    ...codeEditor,
    value_type: VariableValueType.NUMBER,
    value: '',
  };
  expect(typeof test6.value).toBe('string');
  parseVariableValue(test6);
  expect(typeof test6.value).toBe('undefined');
});

it('processVariableTypedValue should works fine', () => {
  const test1 = { ...stringInput, typed_value: undefined, value_type: VariableValueType.STRING };

  expect(typeof test1.value).toBe('string');
  expect(typeof test1.typed_value).toBe('undefined');
  expect(test1.typed_value).not.toBe(test1.value);
  processVariableTypedValue(test1);
  expect(typeof test1.value).toBe('string');
  expect(typeof test1.typed_value).toBe('string');
  expect(test1.typed_value).toBe(test1.value);

  const test2 = {
    ...objectInput,
    typed_value: undefined,
    value_type: VariableValueType.OBJECT,
  };
  expect(typeof test2.value).toBe('string');
  expect(typeof test2.typed_value).toBe('undefined');
  expect(test2.typed_value).not.toBe(test2.value);
  processVariableTypedValue(test2);
  expect(typeof test2.value).toBe('string');

  expect(typeof test2.typed_value).toBe('object');
  expect(test2.typed_value).toEqual(JSON.parse(test2.value));

  const test3 = {
    ...listInput,
    typed_value: undefined,
    value_type: VariableValueType.LIST,
  };
  expect(typeof test3.value).toBe('string');
  expect(typeof test3.typed_value).toBe('undefined');
  expect(test3.typed_value).not.toBe(test3.value);
  processVariableTypedValue(test3);
  expect(typeof test3.value).toBe('string');
  expect(typeof test3.typed_value).toBe('object');
  expect(test3.typed_value).toEqual(JSON.parse(test3.value));
});

it('processTypedValue should works fine', () => {
  let template = cloneDeep(noTypedValueTemplate) as WorkflowTemplatePayload;

  expect(
    template.config.job_definitions.every((job) => {
      return job.variables.every(
        (item) => typeof item.value === 'string' && typeof item.typed_value === 'undefined',
      );
    }),
  ).toBeTruthy();

  template = processTypedValue(template);

  expect(
    template.config.job_definitions.every((job) => {
      return job.variables.every((item) => {
        if (
          item.widget_schema.component === VariableComponent.Input &&
          (item.value_type === VariableValueType.OBJECT ||
            item.value_type === VariableValueType.LIST)
        ) {
          return typeof item.value === 'string' && typeof item.typed_value === 'object';
        }

        return typeof item.typed_value !== 'undefined';
      });
    }),
  ).toBeTruthy();
});
