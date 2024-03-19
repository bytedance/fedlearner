import { FilterOp } from 'typings/filter';

export const FILTER_EVENT_OPERATOR_MAPPER = {
  source: FilterOp.IN,
  start_time: FilterOp.GREATER_THAN,
  end_time: FilterOp.LESS_THAN,
  name: FilterOp.CONTAIN,
  resource_type: FilterOp.CONTAIN,
  username: FilterOp.EQUAL,
  resource_name: FilterOp.CONTAIN,
  coordinator_pure_domain_name: FilterOp.CONTAIN,
};

export const EVENT_SOURCE_TYPE_MAPPER = {
  inner: ['UI', 'API', 'UNKNOWN_SOURCE'],
  cross_domain: ['RPC'],
};

export const EVENT_TYPE_DELETE_MAPPER = {
  inner: 'USER_ENDPOINT',
  cross_domain: 'RPC',
};
