import { AxiosPromise, AxiosResponse } from 'axios';
import request from 'libs/request';
import { FedLoginFormData, FedUserInfo } from 'typings/auth';

export function fetchUserInfo(id: string): AxiosPromise<FedUserInfo> {
  return request(`/v2/auth/users/${id}`);
}

export function login(payload: FedLoginFormData) {
  return request.post('/v2/auth/signin', payload);
}

export function logout() {
  return request.post('/v2/auth/signout');
}
