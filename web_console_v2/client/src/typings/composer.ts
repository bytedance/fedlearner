export enum ItemStatus {
  ON = 'ON',
  OFF = 'OFF',
}

export enum RunnerStatus {
  INIT = 'INIT',
  RUNNING = 'RUNNING',
  DONE = 'DONE',
  FAILED = 'FAILED',
}

export interface SchedulerItem {
  id: ID;
  name: string;
  status: ItemStatus;
  cron_config?: string;
  last_run_at: DateTime;
  retry_cnt: number;
  created_at: DateTime;
  updated_at: DateTime;
  deleted_at?: DateTime;
  pipeline: Object;
}

export interface SchedulerRunner {
  id: ID;
  item_id: ID;
  status: RunnerStatus;
  start_at: DateTime;
  end_at: DateTime;
  created_at: DateTime;
  updated_at: DateTime;
  deleted_at?: DateTime;
  pipeline: Object;
  context: Object;
  output: Object;
}

export interface SchedulerQueryParams {
  filter?: string;
  page?: number;
  pageSize?: number;
}
