import { AxiosResponse } from 'axios'
import { Optional } from 'utility-types'

const fakeUserInfo: Optional<AxiosResponse> = {
  data: {
    id: '1010100000100',
    username: 'mocked',
    name: 'Mocked',
    email: 'fl@mocked.com',
    tel: '',
    avatar: '',
    role: 'admin',
  },
  // to mock server error, just tweak the status code below
  status: 300,
}

export default fakeUserInfo
