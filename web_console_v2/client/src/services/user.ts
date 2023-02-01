import request from 'libs/request';
import { FedLoginFormData, FedUserInfo, FedLoginWay, FedLoginQueryParamsData } from 'typings/auth';

export function fetchUserInfo(id: ID): Promise<{ data: FedUserInfo }> {
  return request(`/v2/auth/users/${id}`);
}

export function login(
  payload: FedLoginFormData,
  queryParam: FedLoginQueryParamsData = {},
): Promise<{ data: { user: FedUserInfo; access_token: string } }> {
  return request.post('/v2/auth/signin', payload, {
    params: {
      ...queryParam,
    },
  });
}

export function getAllUsers(): Promise<{ data: FedUserInfo[] }> {
  return request.get('/v2/auth/users');
}

export function deleteUser(id: ID): Promise<{ data: FedUserInfo }> {
  return request.delete(`/v2/auth/users/${id}`);
}

export function updateUser(id: ID, payload: Partial<FedUserInfo>): Promise<{ data: FedUserInfo }> {
  return request.patch(`/v2/auth/users/${id}`, payload);
}

export function createNewUser(payload: FedUserInfo): Promise<{ data: FedUserInfo }> {
  return request.post('/v2/auth/users', payload);
}

export function logout() {
  return request.delete('/v2/auth/signin');
}

export function fetchLoginWayList(): Promise<{ data: FedLoginWay[] }> {
  return request(`/v2/auth/sso_infos`);
}

export function getMyUserInfo(): Promise<{ data: FedUserInfo }> {
  return request(`/v2/auth/self`);
}
