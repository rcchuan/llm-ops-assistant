import { http } from "./http"

export interface HealthResponse {
  status: "ok" | "degraded"
  service: string
  version: string
  database: {
    status: "up" | "down"
  }
}

export async function getHealth(): Promise<HealthResponse> {
  const response = await http.get<HealthResponse>("/health", {
    validateStatus: (status) => status === 200 || status === 503,
  })
  return response.data
}
