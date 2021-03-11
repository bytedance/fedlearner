import { clone, isNil } from 'lodash';
import { giveWeakRandomKey } from 'shared/helpers';
import { JobType, JobDefinitionForm } from 'typings/job';
import { Variable, VariableAccessMode, VariableComponent } from 'typings/variable';

export const TPL_GLOBAL_NODE_UUID = giveWeakRandomKey();

export const DEFAULT_JOB: JobDefinitionForm = {
  name: '',
  job_type: JobType.DATA_JOIN,
  is_manual: false,
  is_federated: false,
  variables: [],
  yaml_template: '{}',
};

export const DEFAULT_GLOBAL_VARS: { variables: Variable[] } = { variables: [] };

export const DEFAULT_VARIABLE: Variable = {
  name: '',
  value: '',
  access_mode: VariableAccessMode.PEER_WRITABLE,
  widget_schema: {
    component: VariableComponent.Input,
    type: 'string',
    required: true,
  },
};

const storedJobNGlbalForms: Map<string, JobDefinitionForm> = new Map();

/**
 * NOTE: will create a default job def or global vars if not exist
 */
export function getOrInsertValueByid(id?: string) {
  if (isNil(id)) return null;

  if (!storedJobNGlbalForms.has(id)) {
    upsertValue(id, id === TPL_GLOBAL_NODE_UUID ? clone(DEFAULT_GLOBAL_VARS) : clone(DEFAULT_JOB));
  }

  return storedJobNGlbalForms.get(id)!;
}

export function removeValueId(id: string) {
  return storedJobNGlbalForms.delete(id);
}

export function upsertValue(id: string, val: any) {
  return storedJobNGlbalForms.set(id, val);
}

export function clearMap() {
  return storedJobNGlbalForms.clear();
}

export default storedJobNGlbalForms;
