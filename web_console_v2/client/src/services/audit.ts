import request from 'libs/request';
import { APIResponse } from 'typings/app';
import { Audit, AuditQueryParams, AuditDeleteParams } from 'typings/audit';

export function fetchAuditList(params?: AuditQueryParams): APIResponse<Audit[]> {
  return request.get('/v2/events', {
    params,
    removeFalsy: true,
    snake_case: true,
  });
}

export function deleteAudit(params: AuditDeleteParams) {
  return request.delete('/v2/events', { params, removeFalsy: true, snake_case: true });
}
