export interface HealthResponse {
  status: "ok" | "degraded"
  service: string
  version: string
  database: { status: "up" | "down" }
  api: { status: "up" }
  dify_app: { status: "configured" | "not_configured" }
  dify_dataset: { status: "configured" | "not_configured" }
}

export function acceptsHealthStatus(status: number): boolean {
  return status === 200 || status === 503
}
