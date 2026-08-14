import { http } from "./http"
import type { StatisticsOverview } from "../types/statistics"

export async function getStatistics(): Promise<StatisticsOverview> {
  const response = await http.get<StatisticsOverview>("/admin/statistics/overview")
  return response.data
}
