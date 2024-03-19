import { clone, isEmpty, isNil, cloneDeep } from 'lodash-es';
import { giveWeakRandomKey } from 'shared/helpers';
import { JobType, Job, JobDependency } from 'typings/job';
import {
  Variable,
  VariableAccessMode,
  VariableComponent,
  VariableValueType,
} from 'typings/variable';
import { JobSlot } from 'typings/workflow';
import { Overwrite } from 'utility-types';
import jobTypeToMetaDatasMap from 'jobMetaDatas';

export type SlotName = string;
export type SlotEntry = [SlotName, JobSlot];
export type SlotEntries = [SlotName, JobSlot][];
export type VariableDefinitionForm = Variable & { _uuid: string };
export type JobDefinitionForm = Overwrite<
  Omit<Job, 'dependencies'>,
  { variables: VariableDefinitionForm[] }
> & { _slotEntries: SlotEntries };
export type JobDefinitionFormWithoutSlots = Omit<JobDefinitionForm, '_slotEntries'>;

export const TPL_GLOBAL_NODE_SYMBOL = Symbol('Template-global-node');
export const TPL_GLOBAL_NODE_UUID = giveWeakRandomKey(TPL_GLOBAL_NODE_SYMBOL);

export const IS_DEFAULT_EASY_MODE = true;

// You can note that we don't have `dependencies` field here
// since the job form doesn't decide the value, but the TemplateCanvas do
export const DEFAULT_JOB: JobDefinitionForm = {
  name: '',
  job_type: JobType.RAW_DATA,
  is_federated: false,
  easy_mode: IS_DEFAULT_EASY_MODE,
  yaml_template: '{}',
  variables: [],
  _slotEntries: [],
};

export const DEFAULT_GLOBAL_VARS: { variables: VariableDefinitionForm[] } = { variables: [] };

export const DEFAULT_VARIABLE: VariableDefinitionForm = {
  _uuid: '',
  name: '',
  value: '',
  tag: '',
  access_mode: VariableAccessMode.PEER_WRITABLE,
  value_type: VariableValueType.STRING,
  widget_schema: {
    component: VariableComponent.Input,
    required: true,
  },
};

export function giveDefaultVariable() {
  const newVar = cloneDeep(DEFAULT_VARIABLE);
  newVar._uuid = giveWeakRandomKey();
  return newVar;
}

/**
 * Create a stoire that contains a map with a <tpl-canvas-node-uuid, any values> struct,
 * plus some helpers to control the map
 */
class TplNodeToAnyResourceStore<ResourceT> {
  map = new Map<string, ResourceT>();

  defaultResource: (id: string) => ResourceT;

  constructor(options: { defaultResource: (id: string) => ResourceT }) {
    this.defaultResource = options.defaultResource;
  }

  get entries() {
    return Array.from(this.map.entries());
  }

  get size() {
    return this.map.size;
  }

  getValueById(id: string) {
    if (isNil(id)) return undefined;

    return this.map.get(id)!;
  }

  insertNewResource(id: string) {
    const newResrc = this.defaultResource(id);
    this.upsertValue(id, newResrc);

    return newResrc;
  }

  removeValueById(id: string) {
    return this.map.delete(id);
  }

  upsertValue(id: string, val: ResourceT) {
    return this.map.set(id, val);
  }

  clearMap() {
    return this.map.clear();
  }
}

/** Store of job defintiions & variables */
export const definitionsStore = new TplNodeToAnyResourceStore<JobDefinitionFormWithoutSlots>({
  defaultResource(id: string) {
    return id === TPL_GLOBAL_NODE_UUID
      ? (clone(DEFAULT_GLOBAL_VARS) as JobDefinitionForm)
      : clone(DEFAULT_JOB);
  },
});

(window as any).definitionsStore = definitionsStore;

export function mapUuidDepToJobName(dep: JobDependency): JobDependency {
  return {
    source: definitionsStore.getValueById(dep.source)?.name!,
  };
}

/**
 * 1. Fill empty widget_schema
 * 2. Add _uuid to each varriable
 */
export function preprocessVariables(variable: Variable): VariableDefinitionForm {
  const copy = clone(variable) as VariableDefinitionForm;

  if (!variable.widget_schema || isEmpty(variable.widget_schema)) {
    copy.widget_schema = clone(DEFAULT_VARIABLE.widget_schema);
  }

  copy._uuid = giveWeakRandomKey();

  return copy;
}

/** Store of job editor infos */
export const editorInfosStore = new TplNodeToAnyResourceStore<{
  slotEntries: SlotEntries;
  meta_yaml: string;
}>({
  defaultResource(id: string) {
    if (id === TPL_GLOBAL_NODE_UUID) {
      return null as never;
    }

    const jobType = definitionsStore.getValueById(id)?.job_type;

    if (!jobType) return null as never;

    const jobMetaData = jobTypeToMetaDatasMap.get(jobType);

    if (!jobMetaData) return null as never;

    return {
      slotEntries: Object.entries(jobMetaData.slots),
      meta_yaml: jobMetaData.metaYamlString,
    };
  },
});
