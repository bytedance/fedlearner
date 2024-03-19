/* istanbul ignore file */

/**
 * Variable additional schema dictionary for Workflow
 * NOTE: each variable schema here should only maintain UI related stuffs
 * all the data model things should be described by server-side, e.g. type, name, pattern...
 */

import { VariableWidgetSchema } from 'typings/variable';
import { Optional } from 'utility-types';

export type VariablePresets = { [key: string]: Optional<VariableWidgetSchema> };

// FXIME: demo codes belows
/* istanbul ignore next */
const variablePresets: VariablePresets = {
  cpu_limit: {
    placeholder: '请输入CPU最大使用率',
    formatter: (value: number) => `${value}%`,
    parser: (value: string) => value.replace('%', ''),
  },
  worker_mem: {
    placeholder: "It's an invalid placeholder due to server-side already provide one",
  },
} as const;

export default variablePresets;
