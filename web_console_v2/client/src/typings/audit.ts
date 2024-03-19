import { FedUserInfo } from './auth';

export interface Audit {
  id: number;
  uuid: string;
  name: string;
  user: FedUserInfo;
  user_id: number;
  resource_type: string;
  resource_name: string;
  /** operation type */
  op_type: string;
  /** event result */
  result: string;
  /** event source */
  source: string;
  extra: string | 'null' | null;
  request_id: string;
  access_key_id: string;
  error_code: string;
  source_ip: string;
  created_at: DateTime;
  updated_at: DateTime;
  deleted_at: DateTime;
  coordinator_pure_domain_name?: string;
  event_id?: number;
  project_id?: number;
  result_code?: string;
}

export interface AuditQueryParams {
  username?: string;
  /** event name */
  // name?: string;
  // resource_type?: string;
  // resource_name?: string;
  /** operation type */
  filter?: string;
  op_type?: string;
  // start_time: DateTime;
  // end_time: DateTime;
  /** current page, default: 1 */
  page?: number;
  /** each page count, default: 10 */
  page_size?: number;
}

export interface AuditDeleteParams {
  event_type?: string;
}

export enum EventType {
  INNER = 'inner',
  CROSS_DOMAIN = 'cross_domain',
}

export type QueryParams = {
  keyword?: string;
  selectType?: SelectType;
  startTime?: string;
  endTime?: string;
  radioType?: RadioType;
  crossDomainSelectType?: CrossDomainSelectType;
  eventType?: EventType;
};
export enum RadioType {
  ALL = 'all',
  WEEK = 'week',
  ONE_MONTH = 'one_month',
  THREE_MONTHS = 'three_month',
}

export enum SelectType {
  EVENT_NAME = 'name',
  RESOURCE_TYPE = 'resource_type',
  USER_NAME = 'username',
  RESOURCE_NAME = 'resource_name',
}
export enum CrossDomainSelectType {
  EVENT_NAME = 'name',
  RESOURCE_TYPE = 'resource_type',
  COORDINATOR_PURE_DOMAIN_NAME = 'coordinator_pure_domain_name',
  RESOURCE_NAME = 'resource_name',
  OP_TYPE = 'op_type',
}
