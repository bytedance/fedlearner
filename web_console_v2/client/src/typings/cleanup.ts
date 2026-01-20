export enum CleanupState {
  WAITING = 'WAITING',
  RUNNING = 'RUNNING',
  SUCCEEDED = 'SUCCEEDED',
  FAILED = 'FAILED',
  CANCELED = 'CANCELED',
}
export interface Cleanup {
  id: ID;
  payload: {
    paths: string[];
  };
  resource_id: ID;
  resource_type: string;
  state: CleanupState;
  target_start_at: DateTime;
  updated_at: DateTime;
  completed_at: DateTime;
  created_at: DateTime;
}

export interface CleanupQueryParams {
  filter?: string;
  page?: number;
  pageSize?: number;
}
