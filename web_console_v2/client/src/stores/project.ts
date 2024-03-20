import { atom, selector } from 'recoil';
import { fetchProjectList } from 'services/project';
import { Project } from 'typings/project';
import LOCAL_STORAGE_KEYS from 'shared/localStorageKeys';
import store from 'store2';

export const forceReloadProjectList = atom({
  key: 'ForceReloadProjectList',
  default: 0,
});

export const projectState = atom<{ current?: Project }>({
  key: 'ProjectState',
  default: {
    current: store.get(LOCAL_STORAGE_KEYS.current_project),
  },
});

export const projectListQuery = selector({
  key: 'FetchProjectList',
  get: async ({ get }) => {
    get(forceReloadProjectList);
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
