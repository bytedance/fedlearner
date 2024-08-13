import React from 'react';
import {
  RevisionDetail,
  Workflow,
  WorkflowAcceptPayload,
  WorkflowExecutionDetails,
  WorkflowForkPayload,
  WorkflowInitiatePayload,
  WorkflowTemplate,
  WorkflowTemplatePayload,
} from 'typings/workflow';
import {
  Variable,
  VariableAccessMode,
  VariableComponent,
  VariableValueType,
} from 'typings/variable';
import { FormilySchema } from 'typings/formily';
import { cloneDeep, merge } from 'lodash-es';
import variablePresets, { VariablePresets } from './variablePresets';
import { FC } from 'react';
import {
  JobDefinitionForm,
  VariableDefinitionForm,
} from 'views/WorkflowTemplates/TemplateForm/stores';
import { Job } from 'typings/job';
import { parseValueFromString } from 'shared/helpers';

const __IS_JEST__ = typeof jest !== 'undefined';

const FakeVariableLabel: FC<any> = ({ label, tooltip }: any) => {
  return (
    // eslint-disable-next-line jsx-a11y/aria-role
    <label role="label">
      {label}
      {tooltip && <small>{tooltip}</small>}
    </label>
  );
};

const VariableLabel = __IS_JEST__
  ? FakeVariableLabel
  : /* istanbul ignore next */ require('components/VariableLabel').default;

// ------- Build form Formily schema --------
type BuildOptions = {
  withPermissions?: boolean;
  readonly?: boolean;
  labelAlign?: Position;
  variablePrefix?: string;
};

// Make option variables name end with __OPTION
// for better recognition
let withPermissions__OPTION = false;
let readonly__OPTION = false;
let variablePrefix__OPTION = '';

function _enableOptions(options?: BuildOptions) {
  if (!options) return;

  withPermissions__OPTION = !!options.withPermissions;
  readonly__OPTION = !!options.readonly;
  variablePrefix__OPTION = options.variablePrefix || '';
}
function _resetOptions() {
  withPermissions__OPTION = false;
  readonly__OPTION = false;
  variablePrefix__OPTION = '';
}

export const JOB_NAME_PREFIX = '___';

/**
 * Give a job definition with varables inside, return a formily form-schema,
 * during progress we will merge client side variable presets with inputs
 * learn more at ./variablePresets.ts
 */
export default function buildFormSchemaFromJobDef(
  job: { variables: Variable[]; name: string },
  options?: BuildOptions,
): FormilySchema {
  const { variables, name } = cloneDeep(job);

  const jobName = `${JOB_NAME_PREFIX}${name}`; // Avoid duplicate names with job variables

  const schema: FormilySchema = {
    type: 'object',
    title: jobName,
    properties: {
      [jobName]: {
        type: 'void',
        'x-component': 'FormLayout',
        'x-component-props': {
          labelAlign: options?.labelAlign ?? 'left',
          labelCol: 8,
          wrapperCol: 16,
          // wrapperWidth: 'max-content',
        },
        properties: {},
      },
    },
  };

  return variables.reduce((schema, current, index) => {
    const worker =
      componentToWorkersMap[current.widget_schema?.component || VariableComponent.Input] ||
      /* istanbul ignore next */
      createInput;

    current.widget_schema = _mergeVariableSchemaWithPresets(current, variablePresets);
    current.widget_schema.index = index;

    _enableOptions(options);

    Object.assign(schema.properties![jobName].properties, worker(current));

    _resetOptions();

    return schema;
  }, schema);
}

//---- Variable to Schema private helpers --------

function _getPermissions(variable: Variable) {
  const { access_mode, widget_schema } = variable;
  const display = !widget_schema.hidden;
  const readOnly = widget_schema.readOnly ?? false;
  const permissionControl = withPermissions__OPTION;

  return {
    readOnly: readonly__OPTION
      ? true
      : permissionControl
      ? access_mode === VariableAccessMode.PEER_READABLE
      : readOnly,
    display: permissionControl ? access_mode !== VariableAccessMode.PRIVATE : display,
  };
}

function _getDatas({ value, widget_schema: { type, enum: enums } }: Variable, forceValue?: any) {
  return {
    type,
    default: forceValue ?? value,
    enum: enums,
  };
}

function _getUIs({
  name,
  access_mode,
  widget_schema: { size, placeholder, index, label, tooltip, description },
}: Variable) {
  return {
    title: label
      ? VariableLabel({ label, tooltip, accessMode: access_mode })
      : VariableLabel({ label: name, tooltip, accessMode: access_mode }),
    description,
    'x-index': index,
    'x-decorator': 'FormItem',
    'x-decorator-props': {
      colon: true,
      tooltip: null,
    },
    'x-component-props': {
      size,
      placeholder: placeholder || tooltip || `请输入 ${name}`,
    },
  };
}

function _getValidations({ widget_schema: { pattern, rules, required } }: Variable) {
  return {
    required,
    pattern,
    'x-validator': rules,
  };
}

//---- Form Schema Workers --------
export function createInput(variable: Variable): FormilySchema {
  const {
    name,
    widget_schema: { prefix, suffix, maxLength },
    value_type,
    value,
  } = variable;

  let forceValue = value;
  if (
    value_type &&
    [VariableValueType.CODE, VariableValueType.LIST, VariableValueType.OBJECT].includes(
      value_type,
    ) &&
    typeof variable.value === 'object'
  ) {
    forceValue = JSON.stringify(value);
  }

  return {
    [variablePrefix__OPTION + name]: merge(
      _getUIs(variable),
      _getDatas(variable, forceValue),
      _getPermissions(variable),
      // TODO: JSON Check
      _getValidations(variable),
      {
        'x-component': VariableComponent.Input,
        'x-component-props': {
          prefix,
          suffix,
          maxLength,
          allowClear: true,
        },
      },
    ),
  };
}

export function createTextArea(variable: Variable): FormilySchema {
  const {
    name,
    widget_schema: { rows, showCount, maxLength },
  } = variable;

  return {
    [variablePrefix__OPTION + name]: merge(
      _getUIs(variable),
      _getDatas(variable),
      _getPermissions(variable),
      _getValidations(variable),
      {
        'x-component': VariableComponent.TextArea,
        'x-component-props': {
          rows,
          showCount,
          maxLength,
        },
      },
    ),
  };
}

export function createSelect(variable: Variable): FormilySchema {
  const {
    name,
    widget_schema: { options, filterOption, multiple },
  } = variable;

  return {
    [variablePrefix__OPTION + name]: merge(
      _getUIs(variable),
      _getDatas(variable),
      _getPermissions(variable),
      _getValidations(variable),
      {
        enum: options?.source || /* istanbul ignore next: no need to test empty array */ [],
        'x-component': VariableComponent.Select,
        'x-component-props': {
          allowClear: true,
          filterOption: filterOption,
          mode: multiple ? /* istanbul ignore next */ 'multiple' : null,
        },
      },
    ),
  };
}

export function createSwitch(variable: Variable): FormilySchema {
  const {
    name,
    widget_schema: { checkedChildren, unCheckedChildren },
  } = variable;

  return {
    [variablePrefix__OPTION + name]: merge(
      _getUIs(variable),
      _getDatas(variable),
      _getPermissions(variable),
      _getValidations(variable),
      {
        'x-component': VariableComponent.Switch,
        'x-component-props': {
          checkedChildren,
          unCheckedChildren,
        },
      },
    ),
  };
}

/* istanbul ignore next: almost same as select */
export function createCheckbox(variable: Variable): FormilySchema {
  const {
    name,
    widget_schema: { options },
  } = variable;

  return {
    [variablePrefix__OPTION + name]: merge(
      _getUIs(variable),
      _getDatas(variable),
      _getPermissions(variable),
      _getValidations(variable),
      {
        enum: options?.source || [],
        'x-component': VariableComponent.Checkbox,
      },
    ),
  };
}

/* istanbul ignore next: almost same as select */
export function createRadio(variable: Variable): FormilySchema {
  const {
    name,
    widget_schema: { options },
  } = variable;

  return {
    [variablePrefix__OPTION + name]: merge(
      _getUIs(variable),
      _getDatas(variable),
      _getPermissions(variable),
      _getValidations(variable),
      {
        enum: options?.source || [],
        'x-component': VariableComponent.Radio,
      },
    ),
  };
}

export function createNumberPicker(variable: Variable): FormilySchema {
  const {
    name,
    widget_schema: { min, max },
  } = variable;

  return {
    [variablePrefix__OPTION + name]: merge(
      _getUIs(variable),
      _getDatas(variable),
      _getPermissions(variable),
      _getValidations(variable),
      {
        minimum: min,
        maximum: max,
        'x-component': VariableComponent.NumberPicker,
        'x-component-props': {
          min,
          max,
          parser: /* istanbul ignore next */ (v: string) => v,
          formatter: /* istanbul ignore next */ (value: number) => `${value}`,
        },
      },
    ),
  };
}

export function createCpuInput(variable: Variable): FormilySchema {
  const {
    name,
    widget_schema: { min, max },
  } = variable;
  const minVal = min || 1000;
  const maxVal = max || Number.MAX_SAFE_INTEGER;

  return {
    [variablePrefix__OPTION + name]: merge(
      _getUIs(variable),
      _getDatas(variable),
      _getPermissions(variable),
      _getValidations(variable),
      {
        // minimum: minVal,
        // maximum: maxVal,
        'x-component': VariableComponent.CPU,
        'x-component-props': {
          min: minVal,
          max: maxVal,
        },
      },
    ),
  };
}
export function createMemInput(variable: Variable): FormilySchema {
  const {
    name,
    widget_schema: { min, max },
  } = variable;
  const minVal = min || 1;
  const maxVal = max || 100;

  return {
    [variablePrefix__OPTION + name]: merge(
      _getUIs(variable),
      _getDatas(variable),
      _getPermissions(variable),
      _getValidations(variable),
      {
        minimum: minVal,
        maximum: maxVal,
        'x-component': VariableComponent.MEM,
        'x-component-props': {
          min: minVal,
          max: maxVal,
        },
      },
    ),
  };
}

export function createModelCodesEditor(variable: Variable): FormilySchema {
  const { name } = variable;

  return {
    [variablePrefix__OPTION + name]: merge(
      _getUIs(variable),
      _getDatas(variable),
      _getPermissions(variable),
      _getValidations(variable),
      {
        'x-component': VariableComponent.Code,
      },
    ),
  };
}
export function createJSONEditor(variable: Variable): FormilySchema {
  const { name } = variable;

  return {
    [variablePrefix__OPTION + name]: merge(
      _getUIs(variable),
      _getDatas(variable),
      _getPermissions(variable),
      _getValidations(variable),
      {
        'x-component': VariableComponent.JSON,
        'x-component-props': {
          language: 'json',
        },
      },
    ),
  };
}

export function createDatasetSelect(variable: Variable): FormilySchema {
  const { name } = variable;

  return {
    [variablePrefix__OPTION + name]: merge(
      _getUIs(variable),
      _getDatas(variable),
      _getPermissions(variable),
      _getValidations(variable),
      {
        'x-component': VariableComponent.Dataset,
      },
    ),
  };
}

export function createDatasePathSelect(variable: Variable): FormilySchema {
  const { name } = variable;

  return {
    [variablePrefix__OPTION + name]: merge(
      _getUIs(variable),
      _getDatas(variable),
      _getPermissions(variable),
      _getValidations(variable),
      {
        'x-component': VariableComponent.DatasetPath,
      },
    ),
  };
}

export function createFeatureSelect(variable: Variable): FormilySchema {
  const { name } = variable;

  return {
    [variablePrefix__OPTION + name]: merge(
      _getUIs(variable),
      _getDatas(variable),
      _getPermissions(variable),
      _getValidations(variable),
      {
        'x-component': VariableComponent.FeatureSelect,
      },
    ),
  };
}

export function createEnvsInput(variable: Variable): FormilySchema {
  const {
    name,
    widget_schema: { required },
  } = variable;
  return {
    [variablePrefix__OPTION + name]: merge(
      _getUIs(variable),
      _getDatas(variable),
      _getPermissions(variable),
      _getValidations(variable),
      {
        type: 'array',
        'x-component': 'ArrayItems',
        items: {
          type: 'object',
          properties: {
            NO_NAME_FIELD_$0: {
              type: 'void',
              'x-component': 'Space',
              properties: {
                name: {
                  key: 'name',
                  type: 'string',
                  title: 'name',
                  'x-component': 'Input',
                  'x-decorator': 'FormItem',
                  required,
                },
                value: {
                  key: 'value',
                  type: 'string',
                  title: 'value',
                  'x-component': 'Input',
                  'x-decorator': 'FormItem',
                  required,
                },
                remove: {
                  type: 'void',
                  'x-decorator': 'FormItem',
                  'x-component': 'ArrayItems.Remove',
                },
              },
            },
          },
        },
        properties: {
          add: {
            type: 'void',
            title: '添加参数',
            'x-component': 'ArrayItems.Addition',
          },
        },
      },
    ),
  };
}

export function createAlgorithmSelect(variable: Variable): FormilySchema {
  const { name } = variable;

  return {
    [variablePrefix__OPTION + name]: merge(
      _getUIs(variable),
      _getDatas(variable),
      _getPermissions(variable),
      _getValidations(variable),
      {
        'x-component': VariableComponent.AlgorithmSelect,
        'x-component-props': {
          containerStyle: { width: '100%' },
        },
      },
    ),
  };
}

// ---- Component to Worker map --------
const componentToWorkersMap: { [key: string]: (v: Variable) => FormilySchema } = {
  [VariableComponent.Input]: createInput,
  [VariableComponent.Checkbox]: createCheckbox,
  [VariableComponent.TextArea]: createTextArea,
  [VariableComponent.Switch]: createSwitch,
  [VariableComponent.Select]: createSelect,
  [VariableComponent.Radio]: createRadio,
  [VariableComponent.NumberPicker]: createNumberPicker,
  [VariableComponent.CPU]: createCpuInput,
  [VariableComponent.MEM]: createMemInput,
  [VariableComponent.Code]: createModelCodesEditor,
  [VariableComponent.JSON]: createJSONEditor,
  [VariableComponent.DatasetPath]: createDatasePathSelect,
  [VariableComponent.Dataset]: createDatasetSelect,
  [VariableComponent.FeatureSelect]: createFeatureSelect,
  [VariableComponent.EnvsInput]: createEnvsInput,
  [VariableComponent.AlgorithmSelect]: createAlgorithmSelect,
};

// ---------- Widget schemas stringify, parse -----------

export function stringifyVariableValue(variable: Variable) {
  if (
    [VariableValueType.CODE, VariableValueType.LIST, VariableValueType.OBJECT].includes(
      variable.value_type!,
    ) &&
    typeof variable.value === 'object'
  ) {
    variable.value = JSON.stringify(variable.value);
  }
  // Otherwise, type is STRING/NUMBER/BOOLEAN
  if (typeof variable.value !== 'string') {
    variable.value = String(variable.value);
  }
}

export function parseVariableValue(variable: Variable) {
  if (
    [VariableValueType.CODE, VariableValueType.LIST, VariableValueType.OBJECT].includes(
      variable.value_type!,
    ) &&
    typeof variable.value !== 'object'
  ) {
    try {
      variable.value = JSON.parse(variable.value);
    } catch (error) {}
  }

  if (variable.value_type === VariableValueType.STRING && typeof variable.value !== 'string') {
    variable.value = String(variable.value);
  }
  if (variable.value_type === VariableValueType.NUMBER && typeof variable.value !== 'number') {
    variable.value = variable.value ? Number(variable.value) : undefined;
  }
  if (variable.value_type === VariableValueType.BOOLEAN && typeof variable.value !== 'boolean') {
    variable.value = Boolean(variable.value);
  }
}

export function processVariableTypedValue(variable: Variable) {
  if (variable.value_type) {
    variable.typed_value = parseValueFromString(variable.value, variable.value_type as any);
  } else {
    variable.typed_value = variable.value;
  }
}

/**
 * Stringify each variable's widget schema & codes value
 */
export function stringifyComplexDictField<
  T extends
    | WorkflowInitiatePayload
    | WorkflowInitiatePayload<Job>
    | WorkflowTemplatePayload
    | WorkflowTemplatePayload<JobDefinitionForm, VariableDefinitionForm>
    | WorkflowAcceptPayload
    | WorkflowForkPayload
>(input: T): T {
  let ret = cloneDeep(input);
  ret.config?.job_definitions.forEach((job: any) => {
    job.variables.forEach(_stringify);
  });

  ret.config.variables?.forEach(_stringify);

  const ifIsForking = (ret as WorkflowForkPayload).fork_proposal_config;

  /* istanbul ignore if */
  if (ifIsForking) {
    ifIsForking.job_definitions.forEach((job: any) => {
      job.variables.forEach(_stringify);
    });

    ifIsForking.variables?.forEach(_stringify);
  }

  // process typed_value
  ret = processTypedValue(ret);

  return ret;

  function _stringify(variable: any) {
    /* istanbul ignore if: needless to test */
    if (typeof variable.widget_schema === 'object') {
      variable.widget_schema = JSON.stringify(variable.widget_schema);
    }

    stringifyVariableValue(variable);
  }
}

/**
 * Parse each variable's widget schema & codes value
 */
export function parseComplexDictField<
  T extends WorkflowExecutionDetails | WorkflowTemplate | WorkflowForkPayload | RevisionDetail
>(input: T): T {
  const ret = cloneDeep(input);

  ret.config?.job_definitions.forEach((job: any) => {
    job.variables.forEach(_parse);
  });

  ret.config?.variables?.forEach(_parse);

  const ifIsForking = (ret as WorkflowForkPayload).fork_proposal_config;

  /* istanbul ignore if: logic is same as above */
  if (ifIsForking) {
    ifIsForking.job_definitions.forEach((job: any) => {
      job.variables.forEach(_parse);
    });

    ifIsForking.variables?.forEach(_parse);
  }
  return ret;

  function _parse(variable: Variable): any {
    /* istanbul ignore next: needless to test */
    if (typeof variable.widget_schema === 'string') {
      try {
        variable.widget_schema = variable.widget_schema
          ? JSON.parse(variable.widget_schema)
          : /* istanbul ignore next */ {};
      } catch (error) {
        variable.widget_schema = {};
      }
    }

    parseVariableValue(variable);
  }
}

export function processTypedValue<
  T extends
    | WorkflowInitiatePayload
    | WorkflowInitiatePayload<Job>
    | WorkflowTemplatePayload
    | WorkflowTemplatePayload<JobDefinitionForm, VariableDefinitionForm>
    | WorkflowAcceptPayload
    | WorkflowForkPayload
>(input: T): T {
  const ret = cloneDeep(input);
  ret.config?.job_definitions.forEach((job: any) => {
    job.variables.forEach(processVariableTypedValue);
  });

  ret.config.variables?.forEach(processVariableTypedValue);

  const ifIsForking = (ret as WorkflowForkPayload).fork_proposal_config;

  /* istanbul ignore if */
  if (ifIsForking) {
    ifIsForking.job_definitions.forEach((job: any) => {
      job.variables.forEach(processVariableTypedValue);
    });

    ifIsForking.variables?.forEach(processVariableTypedValue);
  }

  return ret;
}

export function parseVariableToFormValue<T extends Workflow>(
  input: T,
): {
  [key: string]: any;
} {
  const formValue: any = {};
  const config = input.config;

  let variablesList: Variable[] = [];

  // global
  if (config && config.variables && config.variables.length > 0) {
    variablesList = variablesList.concat(config.variables);
  }

  // job
  if (config && config.job_definitions && config.job_definitions.length > 0) {
    config.job_definitions.forEach((item) => {
      variablesList = variablesList.concat(item.variables || []);
    });
  }

  if (variablesList.length > 0) {
    variablesList.forEach((item) => {
      formValue[item.name] = item.value;
    });
  }

  return formValue;
}

// -------------- Private helpers ---------------

/**
 * Merge server side variable.widget_schema with client side's preset
 * NOTE: server side's config should always priority to client side!
 */
function _mergeVariableSchemaWithPresets(variable: Variable, presets: VariablePresets) {
  return Object.assign(presets[variable.name] || {}, variable.widget_schema);
}
