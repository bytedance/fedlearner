import { client } from '../libs/http';

export async function deleteJob(name) {
  return client.delete(`job/${name}`).json();
}
