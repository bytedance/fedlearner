/** Federation Learner global types */
export interface FedRouteConfig {
  path: string
  component: React.FunctionComponent
  exact?: boolean
  auth?: boolean // whether require logged in
  roles?: string[]
  children?: FedRouteConfig[]
}

export enum FedLanguages {
  Chinese = 'cn',
  English = 'en',
}
