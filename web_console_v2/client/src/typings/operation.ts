export enum Role {
  COORDINATOR = 'coordinator',
  PARTICIPANT = 'participant',
}

export type JobGroupFetchPayload = {
  role: string;
  name_prefix: string;
  project_name: string;
  e2e_image_url: string;
  fedlearner_image_uri: string;
  platform_endpoint?: string;
};

export type JobItem = {
  job_name: string;
  job_type: string;
};

export type JobInfo = {
  job_name: string;
  log: Array<string>;
  status: object;
};

export type Dashboard = {
  name: string;
  url: string;
  uuid: string;
};
