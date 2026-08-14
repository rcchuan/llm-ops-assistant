import type { LoginResponse, User } from "../types/auth"
import { http } from "./http"

export async function login(username: string, password: string): Promise<LoginResponse> {
  const response = await http.post<LoginResponse>("/auth/login", { username, password })
  return response.data
}

export async function getMe(): Promise<User> {
  const response = await http.get<User>("/auth/me")
  return response.data
}

export async function changePassword(currentPassword: string, newPassword: string): Promise<void> {
  await http.post("/auth/change-password", {
    current_password: currentPassword,
    new_password: newPassword,
  })
}
