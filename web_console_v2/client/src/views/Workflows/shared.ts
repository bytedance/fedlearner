import { StateTypes } from 'components/StateIndicator';
import i18n from 'i18n';
import { Pod, PodState } from 'typings/job';
import { cloneDeep } from 'lodash-es';
import { processVariableTypedValue, stringifyVariableValue } from 'shared/formSchema';
import { DataJobVariable } from 'typings/dataset';
import { Variable } from 'typings/variable';
import { TableColumnProps } from '@arco-design/web-react';

type TableFilterConfig = Pick<TableColumnProps, 'filters' | 'onFilter'>;

/**
 * @param variableShells Variable defintions without any user input value
 * @param formValues User inputs
 */
export function hydrate(
  variableShells: Array<Variable | DataJobVariable>,
  formValues?: Record<string, any>,
  options: {
    isStringifyVariableValue?: boolean;
    isProcessVariableTypedValue?: boolean;
    isStringifyVariableWidgetSchema?: boolean;
  } = {
    isStringifyVariableValue: false,
    isProcessVariableTypedValue: false,
    isStringifyVariableWidgetSchema: false,
  },
): Array<Variable | DataJobVariable> {
  if (!formValues) return [];
  return variableShells.map((item) => {
    const newVariable = cloneDeep({ ...item, value: formValues[item.name] ?? item.value });

    if (options?.isStringifyVariableValue) {
      stringifyVariableValue(newVariable as Variable);
    }
    if (options?.isProcessVariableTypedValue) {
      processVariableTypedValue(newVariable as Variable);
    }
    if (options?.isStringifyVariableWidgetSchema) {
      if (typeof newVariable.widget_schema === 'object') {
        newVariable.widget_schema = JSON.stringify(newVariable.widget_schema);
      }
    }

    return newVariable;
  });
}

export const podStateType: { [key: string]: StateTypes } = {
  [PodState.SUCCEEDED]: 'success',
  [PodState.RUNNING]: 'processing',
  [PodState.FAILED]: 'error',
  [PodState.PENDING]: 'warning',
  [PodState.UNKNOWN]: 'default',
  [PodState.FAILED_AND_FREED]: 'warning',
  [PodState.SUCCEEDED_AND_FREED]: 'success',
  // Deprecated state values
  [PodState.SUCCEEDED__deprecated]: 'success',
  [PodState.RUNNING__deprecated]: 'processing',
  [PodState.FAILED__deprecated]: 'error',
  [PodState.PENDING__deprecated]: 'warning',
  [PodState.UNKNOWN__deprecated]: 'default',
  [PodState.SUCCEEDED_AND_FREED__deprecated]: 'warning',
  [PodState.FAILED_AND_FREED__deprecated]: 'success',
};
export const podStateText: { [key: string]: string } = {
  [PodState.SUCCEEDED]: i18n.t('workflow.job_node_success'),
  [PodState.RUNNING]: i18n.t('workflow.job_node_running'),
  [PodState.FAILED]: i18n.t('workflow.job_node_failed'),
  [PodState.PENDING]: i18n.t('workflow.job_node_waiting'),
  [PodState.UNKNOWN]: i18n.t('workflow.pod_unknown'),
  [PodState.FAILED_AND_FREED]: i18n.t('workflow.pod_failed_cleared'),
  [PodState.SUCCEEDED_AND_FREED]: i18n.t('workflow.pod_success_cleared'),
  // Deprecated state values
  [PodState.SUCCEEDED__deprecated]: i18n.t('workflow.job_node_success'),
  [PodState.RUNNING__deprecated]: i18n.t('workflow.job_node_running'),
  [PodState.FAILED__deprecated]: i18n.t('workflow.job_node_failed'),
  [PodState.PENDING__deprecated]: i18n.t('workflow.job_node_waiting'),
  [PodState.UNKNOWN__deprecated]: i18n.t('workflow.pod_unknown'),
  [PodState.SUCCEEDED_AND_FREED__deprecated]: i18n.t('workflow.pod_failed_cleared'),
  [PodState.FAILED_AND_FREED__deprecated]: i18n.t('workflow.pod_success_cleared'),
};

/* istanbul ignore next */
export function getPodState(pod: Pod): { type: StateTypes; text: string; tip: string } {
  let tip: string = '';
  if ([PodState.FAILED, PodState.PENDING].includes(pod.state)) {
    tip = pod.message || '';
  }
  return {
    text: podStateText[pod.state],
    type: podStateType[pod.state],
    tip,
  };
}

export const podStateOptions = [
  {
    label: podStateText[PodState.SUCCEEDED],
    value: PodState.SUCCEEDED,
  },
  {
    label: podStateText[PodState.RUNNING],
    value: PodState.RUNNING,
  },
  {
    label: podStateText[PodState.FAILED],
    value: PodState.FAILED,
  },
  {
    label: podStateText[PodState.PENDING],
    value: PodState.PENDING,
  },
  {
    label: podStateText[PodState.UNKNOWN],
    value: PodState.UNKNOWN,
  },
  {
    label: podStateText[PodState.FAILED_AND_FREED],
    value: PodState.FAILED_AND_FREED,
  },
  {
    label: podStateText[PodState.SUCCEEDED_AND_FREED],
    value: PodState.SUCCEEDED_AND_FREED,
  },
];

export const podStateFilters: TableFilterConfig = {
  filters: podStateOptions.map((item) => ({
    text: item.label,
    value: item.value,
  })),
  onFilter: (value: string, record: Pod) => {
    return value === record.state;
  },
};
