import { client } from '../libs/http';

export async function deleteJob(name) {
  return client.delete(`job/${name}`).json();
}

export async function createJob(json) {
  return client.post('job', { json }).json();
}
