import { atom, selector } from 'recoil';
import { fetchIntersectionDatasetList } from 'services/dataset';
import { Dataset, DatasetCreatePayload, DatasetType__archived } from 'typings/dataset';
import { WorkflowTemplate, WorkflowInitiatePayload, WorkflowConfig } from 'typings/workflow';
import { Job } from 'typings/job';
import { projectState } from 'stores/project';

export const datasetBasicForm = atom<DatasetCreatePayload>({
  key: 'DatasetBasicForm',
  default: {
    name: '',
    project_id: (undefined as unknown) as ID,
    dataset_type: DatasetType__archived.PSI,
    comment: '',
  },
});

export const forceReloadDatasetList = atom({
  key: 'ForceReloadDatasetList',
  default: 0,
});

export const intersectionDatasetListQuery = selector({
  key: 'FetchIntersectionDatasetList',

  get: async ({ get }) => {
    get(forceReloadDatasetList);
    const selectedProject = get(projectState);
    const projectId = selectedProject?.current?.id ?? 0;
    try {
      const res = await fetchIntersectionDatasetList({
        projectId,
      });

      return res?.data ?? [];
    } catch (error) {
      throw error;
    }
  },
});

export const datasetState = atom<{ current?: Dataset }>({
  key: 'DatasetState',
  default: {
    current: undefined,
  },
});

export const dataJoinTemplate = atom<WorkflowTemplate | undefined>({
  key: 'DataJoinTemplate',
  default: undefined,
});

export const dataJoinWorkflowForm = atom<WorkflowInitiatePayload<Job>>({
  key: 'DataJoinWorkflowForm',
  default: {
    project_id: '',
    template_id: undefined,
    name: '',
    forkable: false,
    config: {
      group_alias: '',
      variables: [],
      job_definitions: [],
    } as WorkflowConfig,
  },
});
