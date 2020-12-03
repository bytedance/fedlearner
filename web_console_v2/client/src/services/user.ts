import { AxiosPromise } from 'axios'
import request from 'libs/request'

export function fetchUserInfo(): AxiosPromise<FedUserInfo> {
  return request('/v2/auth/user')
}

export function login(data: FedLoginFormData) {
  return request.post('/v2/auth/signin', data)
}

export function logout() {
  return request.post('/v2/auth/signout')
}
