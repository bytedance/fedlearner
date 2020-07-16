import { client } from '../libs/http';

export async function getRawDatas() {
  return client.get('raw_datas').json();
}

export async function createRawData(json) {
  return client.post('raw_data', { json }).json();
}

export async function enableRawData(id) {
  return client.post(`raw_data/${id}/enable`).json();
}

export async function revokeRawData(id) {
  return client.post(`raw_data/${id}/revoke`).json();
}

export async function submitRawData(id) {
  return client.post(`raw_data/${id}/submit`).json();
}

export async function deleteRawDataJob(id) {
  return client.post(`raw_data/${id}/delete_job`).json();
}
