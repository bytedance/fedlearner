import { client } from '../libs/http';

export async function getTickets() {
  return client.get('tickets').json();
}

export async function createTicket(json) {
  return client.post('tickets', { json }).json();
}

export async function updateTicket(id, json) {
  return client.put(`tickets/${id}`, { json }).json();
}

export async function enableTicket(id) {
  return client.post(`tickets/${id}/enable`).json();
}

export async function revokeTicket(id) {
  return client.post(`tickets/${id}/revoke`).json();
}
