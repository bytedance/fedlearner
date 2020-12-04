/**
 * Variable Schema Dictionary of Workflow Template
 */

import { VariableSchema } from 'typings/variables'

//---- Start examples --------
// ---------------------------

const JOB_NAME_INPUT: VariableSchema = {
  key: 'job_name',
  title: 'label_job_name',
  type: 'string',
  component: 'Input',
  required: true,
  tooltip: 'tooltip_some_message',
  description: 'desc_some_desc',
  componentProps: {
    size: 'large',
    prefix: '',
    suffix: '',
    // check here for more Input props:
    // https://ant.design/components/input/#Input
    placeholder: 'please_enter_name', // i18n key for placeholder
    // ...other props denpend on which component in using
  },
}

const JOB_TYPE_SELECT: VariableSchema = {
  key: 'job_type',
  title: 'label_job_type',
  type: 'string',
  component: 'Select',
  required: true,
  options: [
    { label: 'label_data_join', value: 1 },
    { label: 'label_psi_data_join', value: 2 },
  ],
  componentProps: {
    placeholder: 'please_select_type',
    readonly: true, // it's equal to PEER_READABLE thus needless to define it explicitly
  },
}

const IS_PAIR_SWITCH: VariableSchema = {
  key: 'is_pair',
  initialValue: false,
  title: 'label_is_pair',
  type: 'boolean',
  component: 'Switch',
  componentProps: {
    checkedChildren: 'Yes', // Switch's prop to change true/false display
    unCheckedChildren: 'No',
  },
}

const FOLLOWER_SELECT: VariableSchema = {
  key: 'follower',
  title: 'label_follower',
  type: 'boolean',
  component: 'Select',
  required: false,
  dynamicOptions: '/api/v2/participants',
  componentProps: {
    placeholder: 'please_choose_follower',
    multiple: true,
  },
}

// TODO: Group form item example

export { JOB_NAME_INPUT, JOB_TYPE_SELECT, IS_PAIR_SWITCH, FOLLOWER_SELECT }

// ---------------------------
//---- End examples --------
