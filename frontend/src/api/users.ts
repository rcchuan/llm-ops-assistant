import type { User, UserListResponse } from "../types/auth"
import { http } from "./http"

export async function getUsers(page: number, pageSize: number): Promise<UserListResponse> {
  const response = await http.get<UserListResponse>("/users", {
    params: { page, page_size: pageSize },
  })
  return response.data
}

export async function createUser(payload: {
  username: string
  display_name: string
  initial_password: string
}): Promise<User> {
  const response = await http.post<User>("/users", payload)
  return response.data
}

export async function updateUserStatus(userId: number, isActive: boolean): Promise<User> {
  const response = await http.patch<User>(`/users/${userId}/status`, { is_active: isActive })
  return response.data
}

export async function resetUserPassword(userId: number, newPassword: string): Promise<void> {
  await http.post(`/users/${userId}/reset-password`, { new_password: newPassword })
}
