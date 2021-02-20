import { atom, selector } from 'recoil';
import { fetchProjectList } from 'services/project';

export const forceReloadProjectList = atom({
  key: 'ForceReloadProjectList',
  default: 0,
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
