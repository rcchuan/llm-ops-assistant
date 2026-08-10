import { http } from "./http"
import { acceptsHealthStatus, type HealthResponse } from "../types/health"

export type { HealthResponse } from "../types/health"

export async function getHealth(): Promise<HealthResponse> {
  const response = await http.get<HealthResponse>("/health", {
    validateStatus: acceptsHealthStatus,
  })
  return response.data
}
