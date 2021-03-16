import React from 'react';
import {
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
import { cloneDeep, merge } from 'lodash';
import variablePresets, { VariablePresets } from './variablePresets';
import { FC } from 'react';

const __IS_JEST__ = typeof jest !== 'undefined';

const FakeVariableLabel: FC<any> = ({ label, tooltip }: any) => {
  return (
    <label role="label">
      {label}
      {tooltip && <small>{tooltip}</small>}
    </label>
  );
};

const VariableLabel = __IS_JEST__ ? FakeVariableLabel : require('components/VariableLabel').default;

// ------- Build form Formily schema --------
type BuildOptions = {
  withPermissions?: boolean;
};

// Make option variables name end with __OPTION
// for better recognition
let withPermissions__OPTION = false;

function _enableOptions(options?: BuildOptions) {
  if (!options) return;

  withPermissions__OPTION = !!options.withPermissions;
}
function _resetOptions() {
  withPermissions__OPTION = false;
}

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
  const schema: FormilySchema = {
    type: 'object',
    title: name,
    properties: {},
  };

  return variables.reduce((schema, current, index) => {
    const worker =
      componentToWorkersMap[current.widget_schema?.component || VariableComponent.Input];

    current.widget_schema = _mergeVariableSchemaWithPresets(current, variablePresets);
    current.widget_schema.index = index;

    _enableOptions(options);

    Object.assign(schema.properties, worker(current));

    _resetOptions();

    return schema;
  }, schema);
}

//---- Variable to Schema private helpers --------

function _getPermissions({ access_mode }: Variable) {
  return {
    readOnly: withPermissions__OPTION && access_mode === VariableAccessMode.PEER_READABLE,
    display: withPermissions__OPTION === false ? true : access_mode !== VariableAccessMode.PRIVATE,
  };
}

function _getDatas({ value, widget_schema: { type, enum: enums } }: Variable) {
  return {
    type,
    default: value,
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
    'x-rules': rules,
  };
}

//---- Form Schema Workers --------
export function createInput(variable: Variable): FormilySchema {
  const {
    name,
    widget_schema: { prefix, suffix, maxLength },
  } = variable;

  return {
    [name]: merge(
      _getUIs(variable),
      _getDatas(variable),
      _getPermissions(variable),
      _getValidations(variable),
      {
        'x-component': 'Input',
        'x-component-props': {
          // check here for more Input props:
          // https://ant.design/components/input/#Input
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
    [name]: merge(
      _getUIs(variable),
      _getDatas(variable),
      _getPermissions(variable),
      _getValidations(variable),
      {
        'x-component': 'TextArea',
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
    [name]: merge(
      _getUIs(variable),
      _getDatas(variable),
      _getPermissions(variable),
      _getValidations(variable),
      {
        enum: options?.source || /* istanbul ignore next: no need to test empty array */ [],
        'x-component': 'Select',
        'x-component-props': {
          // check here for more Select props:
          // https://ant.design/components/select
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
    [name]: merge(
      _getUIs(variable),
      _getDatas(variable),
      _getPermissions(variable),
      _getValidations(variable),
      {
        'x-component': 'Switch',
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
    [name]: merge(
      _getUIs(variable),
      _getDatas(variable),
      _getPermissions(variable),
      _getValidations(variable),
      {
        enum: options?.source || [],
        'x-component': 'Checkbox',
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
    [name]: merge(
      _getUIs(variable),
      _getDatas(variable),
      _getPermissions(variable),
      _getValidations(variable),
      {
        enum: options?.source || [],
        'x-component': 'Radio',
      },
    ),
  };
}

export function createNumberPicker(variable: Variable): FormilySchema {
  const {
    name,
    widget_schema: { min, max, formatter, parser },
  } = variable;

  return {
    [name]: merge(
      _getUIs(variable),
      _getDatas(variable),
      _getPermissions(variable),
      _getValidations(variable),
      {
        minimum: min,
        maximum: max,
        'x-component': 'NumberPicker',
        'x-component-props': {
          min,
          max,
          formatter,
          parser,
        },
      },
    ),
  };
}

export function createModelCodesEditor(variable: Variable): FormilySchema {
  const { name } = variable;

  return {
    [name]: merge(
      _getUIs(variable),
      _getDatas(variable),
      _getPermissions(variable),
      _getValidations(variable),
      {
        'x-component': 'Code',
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
  [VariableComponent.Code]: createModelCodesEditor,
};

// ---------- Widget schemas stringify, parse -----------

export function stringifyVariableCodes(variable: Variable) {
  if (variable.variable_type === VariableValueType.CODE) {
    variable.value = JSON.stringify(variable.value);
  }
}

export function parseVariableCodes(variable: Variable) {
  if (variable.variable_type === VariableValueType.CODE) {
    variable.value = JSON.parse(variable.value);
  }
}

/**
 * Stringify each variable's widget schema & codes value
 */
export function stringifyComplexDictField<
  T extends
    | WorkflowInitiatePayload
    | WorkflowTemplatePayload
    | WorkflowAcceptPayload
    | WorkflowForkPayload
>(input: T): T {
  const ret = cloneDeep(input);

  ret.config?.job_definitions.forEach((job: any) => {
    job.variables.forEach(_stringify);
  });

  ret.config.variables?.forEach(_stringify);

  let ifIsForking = (ret as WorkflowForkPayload).fork_proposal_config;

  /* istanbul ignore if */
  if (ifIsForking) {
    ifIsForking.job_definitions.forEach((job: any) => {
      job.variables.forEach(_stringify);
    });

    ifIsForking.variables?.forEach(_stringify);
  }

  return ret;

  function _stringify(variable: any) {
    /* istanbul ignore if: needless to test */
    if (typeof variable.widget_schema === 'object') {
      variable.widget_schema = JSON.stringify(variable.widget_schema);
    }

    stringifyVariableCodes(variable);
  }
}

/**
 * Parse each variable's widget schema & codes value
 */
export function parseComplexDictField<
  T extends WorkflowExecutionDetails | WorkflowTemplate | WorkflowForkPayload
>(input: T): T {
  const ret = cloneDeep(input);

  ret.config?.job_definitions.forEach((job: any) => {
    job.variables.forEach(_parse);
  });

  ret.config?.variables?.forEach(_parse);

  let ifIsForking = (ret as WorkflowForkPayload).fork_proposal_config;

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
      variable.widget_schema = variable.widget_schema
        ? JSON.parse(variable.widget_schema)
        : /* istanbul ignore next */ {};
    }

    parseVariableCodes(variable);
  }
}

// -------------- Private helpers ---------------

/**
 * Merge server side variable.widget_schema with client side's preset
 * NOTE: server side's config should always priority to client side!
 */
function _mergeVariableSchemaWithPresets(variable: Variable, presets: VariablePresets) {
  return Object.assign(presets[variable.name] || {}, variable.widget_schema);
}
