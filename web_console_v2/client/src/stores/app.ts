import { atom, DefaultValue, selector } from 'recoil';
import LOCAL_STORAGE_KEYS from 'shared/localStorageKeys';
import store from 'store2';
import { DisplayType } from 'typings/component';
import { Flag } from 'typings/flag';
import { FedLoginWay } from 'typings/auth';
import { fetchSysInfo } from 'services/settings';
import { SystemInfo } from 'typings/settings';

export const appPreference = atom({
  key: 'AppPreference',
  default: {
    language: store.get(LOCAL_STORAGE_KEYS.language) as string,
    sidebarFolded: store.get(LOCAL_STORAGE_KEYS.sidebar_folded) as boolean,
    projectsDisplay:
      (store.get(LOCAL_STORAGE_KEYS.projects_display) as DisplayType) || DisplayType.Card,
    sysEmailGroup: store.get(LOCAL_STORAGE_KEYS.sys_email_group) as string,
  },
  effects_UNSTABLE: [
    // LocalStorage persistence
    ({ onSet }) => {
      onSet((newValue) => {
        if (newValue instanceof DefaultValue) {
          // Do nothing
        } else {
          store.set(LOCAL_STORAGE_KEYS.sidebar_folded, newValue.sidebarFolded);
          store.set(LOCAL_STORAGE_KEYS.language, newValue.language);
          store.set(LOCAL_STORAGE_KEYS.projects_display, newValue.projectsDisplay);
          store.set(LOCAL_STORAGE_KEYS.sys_email_group, newValue.sysEmailGroup);
        }
      });
    },
  ],
});

export const appState = atom({
  key: 'AppState',
  default: {
    hideSidebar: false,
  },
});

export const appGetters = selector({
  key: 'AppGetters',
  get({ get }) {
    const isSideBarHidden = get(appState).hideSidebar;

    return {
      sidebarWidth: isSideBarHidden ? 0 : get(appPreference).sidebarFolded ? 48 : 200,
    };
  },
});

export const appEmailGetters = selector({
  key: 'AppEmailGetters',
  get({ get }) {
    return get(appPreference).sysEmailGroup;
  },
});

export const appFlag = atom<Flag>({
  key: 'AppFlag',
  default: store.get(LOCAL_STORAGE_KEYS.app_flags) ?? {},
  effects_UNSTABLE: [
    // LocalStorage persistence
    ({ onSet }) => {
      onSet((newValue) => {
        if (newValue instanceof DefaultValue) {
          // Do nothing
        } else {
          store.set(LOCAL_STORAGE_KEYS.app_flags, newValue ?? {});
        }
      });
    },
  ],
});

export const appLoginWayList = atom<FedLoginWay[]>({
  key: 'AppLoginWayList',
  default: store.get(LOCAL_STORAGE_KEYS.app_login_way_list) ?? [],
  effects_UNSTABLE: [
    // LocalStorage persistence
    ({ onSet }) => {
      onSet((newValue) => {
        if (newValue instanceof DefaultValue) {
          // Do nothing
        } else {
          store.set(LOCAL_STORAGE_KEYS.app_login_way_list, newValue);
        }
      });
    },
  ],
});

export const systemInfoState = atom<{ current?: SystemInfo }>({
  key: 'SystemInfoState',
  default: {
    current: undefined,
  },
});

export const systemInfoQuery = selector({
  key: 'FetchSystemInfoState',
  get: async ({ get }) => {
    try {
      const res = await fetchSysInfo();

      return res.data;
    } catch (error) {
      throw error;
    }
  },
});
