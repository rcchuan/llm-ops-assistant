export interface LoadResult<T> {
  data: T | null
  error: string | null
}

export interface DashboardLoadResult<S, H> {
  statistics: LoadResult<S>
  health: LoadResult<H>
}

export async function loadAdminDashboard<S, H>(
  loadStatistics: () => Promise<S>,
  loadHealth: () => Promise<H>,
): Promise<DashboardLoadResult<S, H>> {
  const [statistics, health] = await Promise.allSettled([loadStatistics(), loadHealth()])
  return {
    statistics: statistics.status === "fulfilled"
      ? { data: statistics.value, error: null }
      : { data: null, error: "统计数据加载失败" },
    health: health.status === "fulfilled"
      ? { data: health.value, error: null }
      : { data: null, error: "健康检查失败" },
  }
}
