/**
 * Variable additional schema dictionary for Workflow
 * NOTE: each variable schema here only maintain UI related stuffs
 * all the data model things should be described by server-side, e.g. type, name, pattern...
 */

import { VariableWidgetSchema } from 'typings/workflow';
import { Optional } from 'utility-types';

export type VariablePresets = { [key: string]: Optional<VariableWidgetSchema> };

// FXIME: demo codes belows
const variablePresets: VariablePresets = {
  job_name: {
    label: 'label_job_name',
    tooltip: 'tooltip_some_message',
    placeholder: 'please_enter_name',
    suffix: '.com',
  },
  participant: {},
  job_type: {
    label: 'label_job_type',
    placeholder: 'please_select_type',
    filterable: true,
  },
  is_pair: {
    checkedChildren: 'Paired!',
  },
  comment: {
    placeholder: 'please_enter_comment_here',
  },
  cpu_limit: {
    formatter: (value: number) => `${value}%`,
    parser: (value: string) => value.replace('%', ''),
  },
  certification: {},
} as const;

export default variablePresets;
