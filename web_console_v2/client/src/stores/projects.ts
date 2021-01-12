import { atom, selector } from 'recoil';
import { fetchProjects } from 'services/project';
import { Project } from 'typings/project';

export const projectListState = atom<Project[]>({
  key: 'ProejctList',
  default: [],
});

export const projectListQuery = selector({
  key: 'FetchProjectList',
  get: async () => {
    try {
      const { data } = await fetchProjects();

      return data.data;
    } catch (error) {
      throw error;
    }
  },
  set: ({ set }, newValue) => {
    set(projectListState, newValue);
  },
});

export const projectListGetters = selector({
  key: 'ProjectListComputed',
  get({ get }) {
    return get(projectListState);
  },
});
