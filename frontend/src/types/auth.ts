export type UserRole = "admin" | "operator"

export interface User {
  id: number
  username: string
  display_name: string
  role: UserRole
  is_active: boolean
  must_change_password: boolean
  created_at: string
  updated_at: string
  last_login_at: string | null
}

export interface LoginResponse {
  access_token: string
  token_type: "bearer"
  expires_in: number
  user: User
}

export interface UserListResponse {
  items: User[]
  total: number
  page: number
  page_size: number
}
