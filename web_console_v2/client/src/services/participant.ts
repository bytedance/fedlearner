import request from 'libs/request';
import {
  CreateParticipantPayload,
  Participant,
  UpdateParticipantPayload,
  Version,
  DomainName,
} from 'typings/participant';
import { APIResponse } from 'typings/app';

export function fetchParticipants(): Promise<{ data: Participant[] }> {
  return request.get('/v2/participants');
}

export function createParticipant(payload: CreateParticipantPayload): Promise<Participant> {
  return request.post('/v2/participants', payload);
}

export function updateParticipant(
  id: ID,
  payload: UpdateParticipantPayload,
): Promise<{ data: Participant }> {
  return request.patch(`/v2/participants/${id}`, payload);
}

export function getParticipantDetailById(id: ID): Promise<{ data: Participant }> {
  return request.get(`/v2/participants/${id}`);
}

export function checkParticipantConnection(
  id: ID,
): Promise<{ data: { success: boolean; message: string; application_version: Version } }> {
  return request.get(`/v2/participants/${id}/connection_checks`);
}

export function getParticipantByProjectId(id: ID): Promise<{ data: Participant[] }> {
  return request.get(`/v2/projects/${id}/participants`);
}

export function deleteParticipant(id: ID): Promise<{ id: ID }> {
  return request.delete(`/v2/participants/${id}`);
}

export function fetchDomainNameList(): APIResponse<DomainName[]> {
  return request.get('/v2/participant_candidates');
}
