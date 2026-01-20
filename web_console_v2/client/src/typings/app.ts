/** Federation Learner global types */
import { FedRoles } from 'typings/auth';
import { ProjectTaskType } from './project';
export interface FedRouteConfig {
  path: string;
  component: React.FunctionComponent;
  exact?: boolean;
  /** Whether require logged in */
  auth?: boolean;
  roles?: FedRoles[];
  async?: boolean;
  /**
   * Whether can show route, must all flagKey in array be true
   * 1. If flagKey no existed in appFlag/localstorage, will be treated as true value
   * 2. If flagKey existed in appFlag/localstorage, Every flagKey must be true in appFlag/localstorage
   */
  flagKeys?: string[];
  abilitiesSupport?: ProjectTaskType[];
}

export enum FedLanguages {
  Chinese = 'zh',
  English = 'en',
}

export enum ErrorCodes {
  TokenExpired = 422,
  Unauthorized = 401,
}

export type Side = 'self' | 'peer';

export interface PageMeta {
  /** Current page number */
  current_page: number;
  /** Each page count */
  page_size: number;
  /** Total page count */
  total_pages: number;
  /** Total item count */
  total_items: number;
}

export type ResponseInfo<T = any> = {
  /** Response data */
  data: T;
  /** Page meta info */
  page_meta?: PageMeta;
  /** Error Code */
  code?: number;
  /** Error message */
  message?: string;
};

export type APIResponse<T = any> = Promise<ResponseInfo<T>>;

export interface PageQueryParams {
  /** current page, default: 1 */
  page?: number;
  /** each page count, default: 10 */
  page_size?: number;
}

export interface DateTimeInfo {
  /** Unix timestamps in seconds */
  created_at: DateTime;
  /** Unix timestamps in seconds */
  updated_at: DateTime;
  /** Unix timestamps in seconds */
  deleted_at: DateTime | null;
}
