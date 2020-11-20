import { atom, selector } from 'recoil'
import { fetchUserInfo } from 'services/user'

export const userInfoStates = atom<FedUserInfo>({
  key: 'UserInfo',
  default: {
    id: '',
    username: '',
    name: '',
    email: '',
    tel: '',
    avatar: '',
  },
})

export const userInfoGetters = selector({
  key: 'UserInfoComputed',
  get({ get }) {
    return {
      isLoggedIn: Boolean(get(userInfoQuery).id),
    }
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
})
