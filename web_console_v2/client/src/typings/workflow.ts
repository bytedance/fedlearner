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
  UNSPECIFIED = 'UNSPECIFIED',
  PRIVATE = 'PRIVATE',
  PEER_READABLE = 'PEER_READABLE',
  PEER_WRITABLE = 'PEER_WRITABLE',
}

export interface Variable {
  name: string
  value: any
  access_mode: VariableAccessMode
  widget_schema: VariableWidgetSchema
}

export enum JobType {
  UNSPECIFIED = 'UNSPECIFIED',
  RAW_DATA = 'RAW_DATA',
  DATA_JOIN = 'DATA_JOIN',
  PSI_DATA_JOIN = 'PSI_DATA_JOIN',
  NN_MODEL_TRANINING = 'NN_MODEL_TRANINING',
  TREE_MODEL_TRAINING = 'TREE_MODEL_TRAINING',
  NN_MODEL_EVALUATION = 'NN_MODEL_EVALUATION',
  TREE_MODEL_EVALUATION = 'TREE_MODEL_EVALUATION',
}

export enum JobState {
  READY = 'READY',
}

export enum JobDependencyType {
  UNSPECIFIED = 'UNSPECIFIED',
  ON_COMPLETE = 'ON_COMPLETE',
  ON_START = 'ON_START',
  MANUAL = 'MANUAL',
}

export interface JobDependency {
  source: string
  type: JobDependencyType
}

export interface Job {
  name: string
  type: JobType
  template?: string
  is_federated: boolean
  is_left?: boolean
  is_manual?: boolean
  variables: Variable[]
  dependencies: JobDependency[]
  yaml_template?: string
}

export type WorkflowConfig = {
  group_alias: string
  is_left: boolean
  variables?: Variable[]
  job_definitions: Job[]
}

export interface WorkflowTemplate {
  id: number
  name: string
  comment: string
  is_left: boolean
  group_alias: string
  config: WorkflowConfig
}

export type WorkflowTemplatePayload = {
  name: string
  comment?: string
  config: any
}

export type WorkflowInitiatePayload = {
  name: string
  project_id: string
  forkable: boolean
  forked_from?: boolean
  config: WorkflowConfig
  comment?: string
}

export enum WorkflowState {
  INVALID = 'INVALID',
  NEW = 'NEW',
  READY = 'READY',
  RUNNING = 'RUNNING',
  STOPPED = 'STOPPED',
  COMPLETED = 'COMPLETED',
}

export enum TransactionState {
  READY = 'READY',
  ABORTED = 'ABORTED',

  COORDINATOR_PREPARE = 'COORDINATOR_PREPARE',
  COORDINATOR_COMMITTABLE = 'COORDINATOR_COMMITTABLE',
  COORDINATOR_COMMITTING = 'COORDINATOR_COMMITTING',
  COORDINATOR_ABORTING = 'COORDINATOR_ABORTING',

  PARTICIPANT_PREPARE = 'PARTICIPANT_PREPARE',
  PARTICIPANT_COMMITTABLE = 'PARTICIPANT_COMMITTABLE',
  PARTICIPANT_COMMITTING = 'PARTICIPANT_COMMITTING',
  PARTICIPANT_ABORTING = 'PARTICIPANT_ABORTING',
}

export type Workflow = {
  id: number
  name: string
  project_id: number
  config: WorkflowConfig | null
  forkable: boolean
  forked_from?: boolean | null
  comment: string | null
  state: WorkflowState
  target_state: WorkflowState
  transaction_state: TransactionState
  transaction_err: string | null
  created_at: DateTime
  updated_at: DateTime
}
