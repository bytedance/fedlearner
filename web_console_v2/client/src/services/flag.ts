import request from 'libs/request';
import { Flag } from 'typings/flag';

export function fetchFlagList(): Promise<{ data: Flag }> {
  return request('/v2/flags');
}

export function fetchParticipantFlagById(participantId: ID): Promise<{ data: Flag }> {
  return request(`/v2/participants/${participantId}/flags`);
}
