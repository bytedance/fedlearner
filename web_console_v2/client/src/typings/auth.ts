export interface FedUserInfo {
  id: number;
  username: string;
  name?: string;
  email?: string;
  role: FedRoles;
  sso_name?: string;
}

export interface FedLoginFormData {
  username?: string;
  password?: string;
  /** SSO code */
  code?: string;
}
export interface FedLoginQueryParamsData {
  /** If sso_name is provided, Back-end will login with sso */
  sso_name?: string;
}

export enum FedRoles {
  Admin = 'ADMIN',
  User = 'USER',
}

export interface Cas {
  authorize_url: string;
  ticket_url: string;
  code_key: string;
}
export interface OAuth {
  client_id: string;
  authorize_url: string;
  access_token_url: string;
  user_info_url: string;
  logout_url: string;
  code_key: string;
}

export interface FedLoginWay {
  name: string;
  icon_url: string;
  protocol_type: string;
  display_name: string;
  cas?: Cas;
  oauth?: OAuth;
  [customProtocol: string]: any;
}
