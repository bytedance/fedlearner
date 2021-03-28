import { AxiosPromise } from 'axios';
import request from 'libs/request';
import { FedLoginFormData, FedUserInfo } from 'typings/auth';

export function fetchUserInfo(id: string): AxiosPromise<{ data: FedUserInfo }> {
  return request(`/v2/auth/users/${id}`);
}

export function login(
  payload: FedLoginFormData,
): AxiosPromise<{ data: { user: FedUserInfo; access_token: string } }> {
  return request.post('/v2/auth/signin', payload);
}

export function addNewUser(payload: FedUserInfo): AxiosPromise<{ data: { user: FedUserInfo } }> {
  return request.post('/v2/auth/users/', payload);
}

export function logout() {
  return request.post('/v2/auth/signout');
}
