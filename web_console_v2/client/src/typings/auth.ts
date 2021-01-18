export interface FedUserInfo {
  id: string;
  username?: string;
  name: string;
  email?: string;
  role?: string;
}

export interface FedLoginFormData {
  username: string;
  passowrd: string;
}

export enum FedRoles {
  Admin,
  Operator,
}
