import request from 'libs/request';
import { FedLoginFormData, FedUserInfo } from 'typings/auth';

export function fetchUserInfo(id: string): Promise<{ data: FedUserInfo }> {
  return request(`/v2/auth/users/${id}`);
}

export function login(data: FedLoginFormData) {
  return request.post('/v2/auth/signin', data);
}

export function logout() {
  return request.post('/v2/auth/signout');
}
