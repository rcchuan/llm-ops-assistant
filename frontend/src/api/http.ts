import axios, { isAxiosError } from "axios"

const baseURL = import.meta.env.VITE_API_BASE_URL

if (!baseURL) {
  throw new Error("缺少 VITE_API_BASE_URL 配置")
}

export const http = axios.create({
  baseURL,
  timeout: 5000,
})

const TOKEN_KEY = "llm_ops_access_token"

export function getAccessToken(): string | null {
  return localStorage.getItem(TOKEN_KEY)
}

export function setAccessToken(token: string): void {
  localStorage.setItem(TOKEN_KEY, token)
}

export function clearAccessToken(): void {
  localStorage.removeItem(TOKEN_KEY)
}

export function getApiErrorMessage(error: unknown, fallback = "操作失败，请稍后重试"): string {
  if (!isAxiosError(error)) return fallback
  const detail = error.response?.data?.detail
  if (typeof detail === "string") return detail
  if (detail && typeof detail.message === "string") return detail.message
  return fallback
}

http.interceptors.request.use((config) => {
  const token = getAccessToken()
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

http.interceptors.response.use(
  (response) => response,
  (error) => {
    const status = error.response?.status
    const code = error.response?.data?.detail?.code
    if (status === 401 && !String(error.config?.url).endsWith("/auth/login")) {
      clearAccessToken()
      if (window.location.pathname !== "/login") window.location.assign("/login")
    }
    if (status === 403 && code === "PASSWORD_CHANGE_REQUIRED") {
      if (window.location.pathname !== "/change-password") window.location.assign("/change-password")
    }
    return Promise.reject(error)
  },
)
