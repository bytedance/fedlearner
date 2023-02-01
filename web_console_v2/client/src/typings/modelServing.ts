import { PageQueryParams, DateTimeInfo } from 'typings/app';
import { ModelType } from 'typings/modelCenter';

export enum ModelDirectionType {
  VERTICAL = 'vertical',
  HORIZONTAL = 'horizontal',
}
export enum ModelServingState {
  UNKNOWN = 'UNKNOWN',
  LOADING = 'LOADING',
  AVAILABLE = 'AVAILABLE',
  UNLOADING = 'UNLOADING',
  DELETED = 'DELETED',
  PENDING_ACCEPT = 'PENDING_ACCEPT',
  WAITING_CONFIG = 'WAITING_CONFIG',
}
export enum ModelServingInstanceState {
  AVAILABLE = 'AVAILABLE',
  UNAVAILABLE = 'UNAVAILABLE',
}

export enum ModelServingDetailTabType {
  USER_GUIDE = 'user-guide',
  INSTANCE_LIST = 'instance-list',
}

export interface ModelServingQueryParams extends PageQueryParams {
  name?: string;
  project_id?: ID;
  keyword?: string;
  filter?: string;
  order_by?: string;
}

export interface ModelServingInstance extends DateTimeInfo {
  name: string;
  status: ModelServingInstanceState;
  cpu: string;
  memory: string;
}

export interface ModelServingResource {
  cpu: string;
  memory: string;
  replicas: number;
}

export interface ModelServing extends DateTimeInfo {
  id: number;
  project_id: number;
  name: string;
  comment: string;
  instances: ModelServingInstance[];
  deployment_id: number;
  resource: ModelServingResource;
  model_id: number;
  is_local: boolean; // 横向：true，纵向：false
  support_inference: boolean;
  model_type: ModelType;

  status: ModelServingState;
  /** URL */
  endpoint: string;
  /** API Input and Output */
  signature: string;
  extra: any;
  instance_num_status: string;
  model_group_id?: number;
  psm?: string;
  remote_platform?: RemotePlatform;
}

export interface UserTypeInfo {
  type: string;
}

export interface RemotePlatform {
  payload: string;
  platform: string;
}
