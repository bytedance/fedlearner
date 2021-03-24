import { clone, isEmpty, isNil } from 'lodash';
import { giveWeakRandomKey } from 'shared/helpers';
import { JobType, JobDefinitionForm, JobDependency } from 'typings/job';
import {
  Variable,
  VariableAccessMode,
  VariableComponent,
  VariableValueType,
} from 'typings/variable';

export const TPL_GLOBAL_NODE_UUID = giveWeakRandomKey();

// You can note that we don't have `dependencies` field here
// since the job form doesn't decide the value, but the TemplateCanvas do
export const DEFAULT_JOB: JobDefinitionForm = {
  name: '',
  job_type: JobType.DATA_JOIN,
  is_federated: false,
  variables: [],
  yaml_template: '{}',
};

export const DEFAULT_GLOBAL_VARS: { variables: Variable[] } = { variables: [] };

export const DEFAULT_VARIABLE: Variable = {
  name: '',
  value: '',
  access_mode: VariableAccessMode.PEER_WRITABLE,
  value_type: VariableValueType.STRING,
  widget_schema: {
    component: VariableComponent.Input,
    required: true,
  },
};

export function turnUuidDepToJobName(dep: JobDependency): JobDependency {
  return {
    source: getOrInsertValueById(dep.source)?.name!,
  };
}

export function fillEmptyWidgetSchema(variable: Variable) {
  if (!variable.widget_schema || isEmpty(variable.widget_schema)) {
    const copy = clone(variable);
    copy.widget_schema = clone(DEFAULT_VARIABLE.widget_schema);

    return copy;
  }

  return variable;
}

// ------------------------------------- Store of job defintiions & variables ---------------------------------------------

const storedJobNGlbalValues: Map<string, JobDefinitionForm> = new Map();

/**
 * NOTE: will create a default job def or global vars if not exist
 */
export function getOrInsertValueById(id?: string) {
  if (isNil(id)) return null;

  if (!storedJobNGlbalValues.has(id)) {
    upsertValue(id, id === TPL_GLOBAL_NODE_UUID ? clone(DEFAULT_GLOBAL_VARS) : clone(DEFAULT_JOB));
  }

  return storedJobNGlbalValues.get(id)!;
}

export function removeValueById(id: string) {
  return storedJobNGlbalValues.delete(id);
}

export function upsertValue(id: string, val: any) {
  return storedJobNGlbalValues.set(id, val);
}

export function clearMap() {
  return storedJobNGlbalValues.clear();
}

export default storedJobNGlbalValues;
