import { AxiosPromise } from 'axios'
import request from 'libs/request'

export function fetchUserInfo(): AxiosPromise<FedUserInfo> {
  return request('/v1/userinfo')
}

export function login() {
  return request('/v1/login')
}

export function logout() {
  return request('/v1/logout')
}
