declare interface FedUserInfo {
  id: string
  username: string
  name: string
  email: string
  tel: string
  avatar: string
  role: string
}

declare interface FedLoginFormData {
  username: string
  passowrd: string
  remember: boolean
}
