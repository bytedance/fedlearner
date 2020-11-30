import { AxiosResponse } from 'axios'
import { Optional } from 'utility-types'

const fakeUserInfo: Optional<AxiosResponse> = {
  data: {
    id: '121',
    username: 'bytedance',
    name: 'Bytedance',
    email: 'fl@bytedance.com',
    tel: '+8613322221111',
    avatar: '',
    role: 'admin',
  },
  // to mock server error, just tweak the status code below
  status: 200,
}

export default fakeUserInfo
