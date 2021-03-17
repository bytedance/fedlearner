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

// TODO: implement user role module
export enum FedRoles {
  Admin,
  Operator,
}
