/**
 * Variable Schema Dictionary of Workflow Template
 */
import { Variable, VariableAccessMode } from 'typings/variables'
import { ISchema } from '@formily/react-schema-renderer/src/types'
import VariableLabel from 'components/VariableLabel/index'
import { merge } from 'lodash'

//---- Start examples --------
// ---------------------------
const JobNameDefinitionBE = {
  name: 'job_name',
  value: '',
  access_mode: VariableAccessMode.PEER_WRITABLE,
  widget_schema: {
    index: 2,
    component: 'Input',
  },
}
const JobNameDefinitionFE = {
  widget_schema: {
    label: 'label_job_name',
    tooltip: 'tooltip_some_message',
    placeholder: 'please_enter_name',
    suffix: '.com',
  },
}
const JOB_NAME_INPUT = createInput(merge(JobNameDefinitionBE, JobNameDefinitionFE) as Variable)

const ParticipantDefinitionBE = {
  name: 'participant',
  value: 'foobar',
  access_mode: VariableAccessMode.PEER_READABLE,
  widget_schema: {
    index: 3,
    component: 'Input',
  },
}

const PARTICIPANT_INPUT = createInput(ParticipantDefinitionBE as Variable)

const JobTypeDefinitionBE = {
  name: 'job_type',
  value: 1,
  access_mode: VariableAccessMode.PEER_WRITABLE,
  widget_schema: {
    index: 2,
    options: {
      type: 'static',
      source: [
        { label: 'label_data_join', value: 1 },
        { label: 'label_psi_data_join', value: 2 },
      ],
    },
    multiple: true,
  },
}
const JobTypeDefinitionFE = {
  widget_schema: {
    label: 'label_job_type',
    placeholder: 'please_select_type',
    filterable: true,
  },
}
const JOB_TYPE_SELECT = createSelect(merge(JobTypeDefinitionBE, JobTypeDefinitionFE) as Variable)

//---- Variable to Form Schema private helpers --------

function _getPermissions({ access_mode }: Variable) {
  return {
    editable: access_mode === VariableAccessMode.PEER_READABLE,
    display: access_mode === VariableAccessMode.PRIVATE,
  }
}

function _getDatas({ value, widget_schema: { type, options } }: Variable) {
  if (options?.type === 'static') {
  }
  return {
    type,
    default: value,
    enum: options,
  }
}

function _getUIs({
  widget_schema: { size, placeholder, index, label, tooltip, description },
}: Variable) {
  return {
    title: VariableLabel({ label, tooltip }),
    description,
    'x-index': index,
    'x-component-props': {
      size,
      placeholder,
    },
  }
}

function _getValidations({ widget_schema: { pattern, rules } }: Variable) {
  return {
    pattern,
    rules,
  }
}

//---- Form Schema builders --------
export function createInput(variable: Variable): ISchema {
  const {
    name,
    widget_schema: { prefix, suffix, showCount, maxLength },
  } = variable

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
          showCount,
          maxLength,
          allowClear: true,
        },
      },
    ),
  }
}

export function createTextArea(variable: Variable): ISchema {
  const {
    name,
    widget_schema: { options, rows, showCount, maxLength },
  } = variable

  return {
    [name]: merge(
      _getUIs(variable),
      _getDatas(variable),
      _getPermissions(variable),
      _getValidations(variable),
      {
        enum: options?.source || [],
        'x-component': 'TextArea',
        'x-component-props': {
          rows,
          showCount,
          maxLength,
        },
      },
    ),
  }
}

export function createSelect(variable: Variable): ISchema {
  const {
    name,
    widget_schema: { options, filterOption, multiple },
  } = variable

  return {
    [name]: merge(
      _getUIs(variable),
      _getDatas(variable),
      _getPermissions(variable),
      _getValidations(variable),
      {
        enum: options?.source || [],
        'x-component': 'Select',
        'x-component-props': {
          // check here for more Select props:
          // https://ant.design/components/select
          allowClear: true,
          filterOption: filterOption,
          mode: multiple ? 'multiple' : null,
        },
      },
    ),
  }
}

export function createSwitch(variable: Variable): ISchema {
  const {
    name,
    widget_schema: { checkedChildren, unCheckedChildren },
  } = variable

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
  }
}

export function createCheckbox(variable: Variable): ISchema {
  const {
    name,
    widget_schema: { options },
  } = variable

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
  }
}

export function createRadio(variable: Variable): ISchema {
  const {
    name,
    widget_schema: { options },
  } = variable

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
  }
}

export function createNumberPicker(variable: Variable): ISchema {
  const {
    name,
    widget_schema: { min, max, formatter, parser },
  } = variable

  return {
    [name]: merge(
      _getUIs(variable),
      _getDatas(variable),
      _getPermissions(variable),
      _getValidations(variable),
      {
        'x-component': 'NumberPicker',
        'x-component-props': {
          min,
          max,
          formatter,
          parser,
        },
      },
    ),
  }
}

export function createUpload(variable: Variable): ISchema {
  const {
    name,
    widget_schema: { accept, action, multiple },
  } = variable

  return {
    [name]: merge(
      _getUIs(variable),
      _getDatas(variable),
      _getPermissions(variable),
      _getValidations(variable),
      {
        'x-component': 'Upload',
        'x-component-props': {
          // force to use dragger-upload
          listType: 'dragger',
          accept,
          action,
          multiple,
        },
      },
    ),
  }
}
