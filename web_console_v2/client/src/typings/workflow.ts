import {
  ComponentSize,
  InputWidgetSchema,
  SelectWidgetSchema,
  UploadWidgetSchema,
  NumberPickerWidgetSchema,
  SwitchWidgetSchema,
  TextAreaWidgetSchema,
  WidgetWithOptionsSchema,
} from './component'

export enum VariableComponent {
  Input = 'Input',
  Select = 'Select',
  Radio = 'Radio',
  Checkbox = 'Checkbox',
  TextArea = 'TextArea',
  NumberPicker = 'NumberPicker',
  Switch = 'Switch',
  TimePicker = 'TimePicker',
  Upload = 'Upload',
}

export type VariableRule = { validator: RegExp | string; message: string }

export interface VariableWidgetSchema
  extends UploadWidgetSchema,
    SelectWidgetSchema,
    NumberPickerWidgetSchema,
    TextAreaWidgetSchema,
    SwitchWidgetSchema,
    SelectWidgetSchema,
    InputWidgetSchema,
    WidgetWithOptionsSchema {
  /** ------ Metas ------ */
  // which component to use
  component: VariableComponent

  /** ------ Datas ------ */
  // NOTE: for array type value, it clould be either a Multiple-select/Checkbox
  // or a Group-items which allow user add | delete. eg. ENV field
  type: 'string' | 'number' | 'boolean' | 'array' | 'object'
  initialValue?: string | number | boolean | any[] | object

  /** ------ UIs ------ */
  // i18n key for job name form-item label
  label: string
  // display order
  index: number
  // will render a question icon beside the label, hover it to show the tooltip
  tooltip?: string
  // will render some text below the form item
  description?: string
  placeholder?: string
  size?: ComponentSize

  /** ------ Validations ------ */
  // RegExp string '\d'
  pattern?: string
  rules?: VariableRule[]
  required?: boolean

  /** ------ Miscs ------ */
  [key: string]: any
}

/** 🚧 NOTE: Types below are NOT the final verison at current stage */

export enum VariableAccessMode {
  UNSPECIFIED,
  PRIVATE,
  PEER_READABLE,
  PEER_WRITABLE,
}

export interface Variable {
  name: string
  value: any
  access_mode: VariableAccessMode
  widget_schema: VariableWidgetSchema
}

export enum JobType {
  UNSPECIFIED,
  RAW_DATA,
  DATA_JOIN,
  PSI_DATA_JOIN,
  NN_MODEL_TRANINING,
  TREE_MODEL_TRAINING,
  NN_MODEL_EVALUATION,
  TREE_MODEL_EVALUATION,
}

export enum JobDependencyType {
  UNSPECIFIED,
  ON_COMPLETE,
  ON_START,
  MANUAL,
}

export interface JobDependency {
  source: string
  type: JobDependencyType
}

export interface Job {
  name: string
  type: JobType
  template: string
  is_federated: boolean
  is_left: boolean
  variables: Variable[]
  dependencies: JobDependency[]
}

export type WorkflowConfig = {
  group_alias: string
  variables?: Variable[]
  jobs: Job[]
}

export interface WorkflowTemplate {
  id: number
  name: string
  comment: string
  group_alias: string
  config: WorkflowConfig
}

export type WorkflowTemplateForm = {
  name: string
  template: any
  comment?: string
}

export type WorkflowForm = {
  name: string
  project_token: string
  peer_forkable: boolean
  config: WorkflowConfig
  comment?: string
}
