import i18n from 'i18n';
import store from 'store2';
import { atom, selector } from 'recoil';
import { fetchUserInfo } from 'services/user';
import LOCAL_STORAGE_KEYS from 'shared/localStorageKeys';
import { isNil } from 'lodash-es';
import { FedRoles, FedUserInfo } from 'typings/auth';

export const userInfoState = atom<FedUserInfo>({
  key: 'UserInfo',
  default: {
    id: store.get(LOCAL_STORAGE_KEYS.current_user)?.id,
    username: '',
    name: '',
    email: '',
    role: FedRoles.User,
  },
});

export const userInfoQuery = selector<FedUserInfo>({
  key: 'UserInfoQuery',
  get: async ({ get }) => {
    try {
      const currentUserId = get(userInfoState).id;

      if (isNil(currentUserId)) {
        throw new Error(i18n.t('error.please_sign_in'));
      }
      const { data } = await fetchUserInfo(currentUserId);

      return data;
    } catch (error) {
      throw error;
    }
  },
  set: ({ set }, newValue: any) => {
    set(userInfoState, { ...newValue });
  },
});

export const userInfoGetters = selector({
  key: 'UserInfoComputed',
  get({ get }) {
    const userInfo = get(userInfoQuery);

    return {
      isAuthenticated: Boolean(userInfo.id) || process.env.REACT_APP_ENABLE_FULLY_MOCK,
      role: userInfo.role,
    };
  },
});
