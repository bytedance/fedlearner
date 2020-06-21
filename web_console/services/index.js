import { client } from '../libs/http';

export async function login(json) {
  return client.post('login', { json }).json();
}

export async function logout() {
  return client.post('logout').json();
}

export async function createUser(json) {
  return client.post('users', { json }).json();
}

export async function deleteUser(id) {
  return client.delete(`users/${id}`).json();
}
