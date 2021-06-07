/** Federation Learner global types */
import { FedRoles } from 'typings/auth';
export interface FedRouteConfig {
  path: string;
  component: React.FunctionComponent;
  exact?: boolean;
  auth?: boolean; // whether require logged in
  roles?: FedRoles[];
}

export enum FedLanguages {
  Chinese = 'zh',
  English = 'en',
}

export enum ErrorCodes {
  TokenExpired = 422,
}

export type Side = 'self' | 'peer';
