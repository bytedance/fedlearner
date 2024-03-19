import { atom, selector } from 'recoil';
import { fetchProjectList } from 'services/project';
import { Project, ProjectTaskType, ProjectAbilityType, ProjectActionType } from 'typings/project';
import LOCAL_STORAGE_KEYS from 'shared/localStorageKeys';
import store from 'store2';
import { userInfoState } from './user';

export const forceReloadProjectList = atom({
  key: 'ForceReloadProjectList',
  default: 0,
});

const mockProject: any = {
  id: 31,
  name: 'test',
  participant_type: 'PLATFORM',
  created_at: 1623319258,
  num_workflow: 8013,
  participants: [
    {
      id: 1,
      name: 'aliyun-test1',
      domain_name: 'fl-aliyun-test.com',
      host: '101.200.236.203',
      port: 32443,
      type: 'PLATFORM',
      comment: 'migrate from projectbytedance-test-hl',
      created_at: 1631007123,
      extra: { is_manual_configured: false, grpc_ssl_server_host: '' },
      updated_at: 1631007123,
      num_project: 0,
      last_connected_at: 0,
    },
  ],
  creator: '',
};
export const projectState = atom<{ current?: Project }>({
  key: 'ProjectState',
  default: {
    current: process.env.IS_DUMI_ENV ? mockProject : store.get(LOCAL_STORAGE_KEYS.current_project),
  },
});

export const projectListQuery = selector({
  key: 'FetchProjectList',
  get: async ({ get }) => {
    get(forceReloadProjectList);
    get(userInfoState);

    try {
      const res = await fetchProjectList();

      return res.data;
    } catch (error) {
      throw error;
    }
  },
});

export const projectListGetters = selector({
  key: 'ProjectListComputed',
  get({ get }) {
    return {
      projectCount: get(projectListQuery).length,
    };
  },
});

export type ProjectCreateForm = {
  name: string;
  comment: string;
  config: {
    variables: never[];
    abilities: ProjectTaskType[];
    action_rules: Record<ProjectActionType, ProjectAbilityType>;
    support_blockchain: boolean;
  };
};
export type ProjectJoinForm = {
  id: string;
  comment: string;
  config: {
    variables: never[];
  };
};

export const initialActionRules = {
  [ProjectActionType.ID_ALIGNMENT]: ProjectAbilityType.ALWAYS_ALLOW,
  [ProjectActionType.DATA_ALIGNMENT]: ProjectAbilityType.ALWAYS_ALLOW,
  [ProjectActionType.HORIZONTAL_TRAIN]: ProjectAbilityType.MANUAL,
  [ProjectActionType.WORKFLOW]: ProjectAbilityType.MANUAL,
  [ProjectActionType.VERTICAL_TRAIN]: ProjectAbilityType.MANUAL,
  [ProjectActionType.VERTICAL_EVAL]: ProjectAbilityType.MANUAL,
  [ProjectActionType.VERTICAL_PRED]: ProjectAbilityType.MANUAL,
  [ProjectActionType.VERTICAL_SERVING]: ProjectAbilityType.MANUAL,
  [ProjectActionType.TEE_SERVICE]: ProjectAbilityType.MANUAL,
  [ProjectActionType.TEE_RESULT_EXPORT]: ProjectAbilityType.MANUAL,
};
export const projectCreateForm = atom<ProjectCreateForm>({
  key: 'ProjectCreateForm',
  default: {
    name: '',
    comment: '',
    config: {
      variables: [],
      abilities: [ProjectTaskType.ALIGN],
      action_rules: initialActionRules,
      support_blockchain: true,
    },
  },
});
export const projectJoinForm = atom<ProjectJoinForm>({
  key: 'ProjectJoinForm',
  default: {
    id: '',
    comment: '',
    config: {
      variables: [],
    },
  },
});
