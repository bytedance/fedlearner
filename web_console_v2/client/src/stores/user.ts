import i18n from 'i18n'
import store from 'store2'
import { atom, selector } from 'recoil'
import { fetchUserInfo } from 'services/user'
import LOCAL_STORAGE_KEYS from 'shared/localStorageKeys'
import { isNil } from 'lodash'

export const userInfoState = atom<FedUserInfo>({
  key: 'UserInfo',
  default: {
    id: '',
    username: '',
    name: '',
    email: '',
    tel: '',
    avatar: '',
    role: '',
  },
})

export const userInfoQuery = selector({
  key: 'UserInfoQuery',
  get: async () => {
    try {
      const currentUserId = store.get(LOCAL_STORAGE_KEYS.current_user)?.id

      if (isNil(currentUserId)) {
        throw new Error(i18n.t('errors.please_sign_in'))
      }
      const userinfo = await fetchUserInfo(currentUserId)

      return userinfo.data
    } catch (error) {
      throw error
    }
  },
  set: ({ set }, newValue) => {
    set(userInfoState, newValue)
  },
})

export const userInfoGetters = selector({
  key: 'UserInfoComputed',
  get({ get }) {
    return {
      isAuthenticated: Boolean(get(userInfoQuery).id),
    }
  },
})
