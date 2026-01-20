import request from 'libs/request';
import { APIResponse } from 'typings/app';
import { ItemStatus, SchedulerItem, SchedulerRunner, SchedulerQueryParams } from 'typings/composer';

export function fetchSchedulerItemList(
  params?: SchedulerQueryParams,
): APIResponse<SchedulerItem[]> {
  return request(`/v2/scheduler_items`, { params, snake_case: true });
}

export function fetchSchedulerRunnerList(
  params?: SchedulerQueryParams,
): APIResponse<SchedulerRunner[]> {
  return request(`/v2/scheduler_runners`, { params, snake_case: true });
}

export function fetchRunnersByItemId(
  item_id: ID,
  params?: SchedulerQueryParams,
): APIResponse<SchedulerRunner[]> {
  return request(`/v2/scheduler_items/${item_id}`, { params, snake_case: true });
}

export function patchEditItemState(
  item_id: ID,
  status: ItemStatus,
): APIResponse<SchedulerRunner[]> {
  return request.patch(`/v2/scheduler_items/${item_id}`, { status });
}
