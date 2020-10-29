import { client } from '../libs/http';

export async function login(json) {
  return client.post('login', { json }).json();
}

export async function logout() {
  return client.post('logout').json();
}

export async function createFederation(json) {
  return client.post('federations', { json }).json();
}

export async function updateFederation(id, json) {
  return client.put(`federations/${id}`, { json }).json();
}

export async function federationHeartbeat(id) {
  return client.get(`federations/${id}/heartbeat`).json();
}

export async function createUser(json) {
  return client.post('users', { json }).json();
}

export async function updateUser(id, json) {
  return client.put(`users/${id}`, { json }).json();
}

export async function deleteUser(id) {
  return client.delete(`users/${id}`).json();
}

export async function updateMe(json) {
  return client.put('user', { json }).json();
}
