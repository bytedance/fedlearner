import { atom, selector } from 'recoil'
import { fetchUserInfo } from 'services/user'

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
      const userinfo = await fetchUserInfo()

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
