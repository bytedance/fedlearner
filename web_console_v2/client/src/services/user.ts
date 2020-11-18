import { AxiosPromise } from 'axios'
import request from 'libs/request'
import { sleep } from 'shared/helpers'

export function fetchUserInfo(): AxiosPromise<FedUserInfo> {
  // TEMPORARY MOCK
  // return sleep(2000).then(() => {
  //   return {
  //     data: {
  //       id: 'dasdasdasd',
  //       username: 'Bytedance',
  //       name: 'Bytedance',
  //       email: 'Bytedance@bytedance.com',
  //       tel: '+8613100000000',
  //       avatar: 'avatar',
  //     },
  //   }
  // }) as AxiosPromise<FedUserInfo>
  return request('/v1/userinfo')
}
