export interface FedUserInfo {
  id: string;
  username: string;
  name?: string;
  email?: string;
  role: FedRoles;
}

export interface FedLoginFormData {
  username: string;
  passowrd: string;
}

export enum FedRoles {
  Admin = 'ADMIN',
  User = 'USER',
}
