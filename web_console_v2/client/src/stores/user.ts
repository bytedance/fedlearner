import i18n from 'i18n'
import store from 'store2'
import { atom, selector } from 'recoil'
import { fetchUserInfo } from 'services/user'
import LOCAL_STORAGE_KEYS from 'shared/localStorageKeys'
import { isNil } from 'lodash'
import { FedUserInfo } from 'typings/auth'

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
  get: async ({ get }) => {
    if (process.env.REACT_APP_ENABLE_FULLY_MOCK) {
      return get(userInfoState)
    }

    try {
      const currentUserId = store.get(LOCAL_STORAGE_KEYS.current_user)?.id

      if (isNil(currentUserId)) {
        throw new Error(i18n.t('error.please_sign_in'))
      }
      const userinfo = await fetchUserInfo(currentUserId)

      return userinfo.data
    } catch (error) {
      throw error
    }
  },
})

export const userInfoGetters = selector({
  key: 'UserInfoComputed',
  get({ get }) {
    return {
      isAuthenticated: Boolean(get(userInfoQuery).id) || process.env.REACT_APP_ENABLE_FULLY_MOCK,
    }
  },
})
