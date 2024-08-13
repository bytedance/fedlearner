export type Overwrite<T, U> = Pick<T, Exclude<keyof T, keyof U>> & U;

export type Notification = {
  /** workflow id */
  id?: number | null;
  kind: string;
  workflow_name: string;
  peer_name: string;
  project_name: string;
  created_at: DateTime;
  project_id: ID;
};
