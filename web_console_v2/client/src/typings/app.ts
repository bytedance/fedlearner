/** Federation Learner global types */
export interface FedRouteConfig {
  path: string;
  component: React.FunctionComponent;
  exact?: boolean;
  auth?: boolean; // whether require logged in
  roles?: string[];
}

export enum FedLanguages {
  Chinese = 'zh',
  English = 'en',
}

export enum ErrorCodes {
  TokenExpired = 422,
}
