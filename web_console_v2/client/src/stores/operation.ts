import { atom, selector } from 'recoil';
import { fetchDashboardList } from '../services/operation';
import { Message } from '@arco-design/web-react';

export const forceReloadDashboard = atom({
  key: 'ForceReloadDashboard',
  default: 0,
});

export const DashboardListQuery = selector({
  key: 'fetchDashboardList',

  get: async ({ get }) => {
    get(forceReloadDashboard);
    try {
      const res = await fetchDashboardList();
      return res?.data ?? [];
    } catch (error) {
      Message.error(error.message);
    }
  },
});
