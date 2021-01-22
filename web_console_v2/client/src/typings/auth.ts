export interface FedUserInfo {
  id: string;
  username?: string;
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
