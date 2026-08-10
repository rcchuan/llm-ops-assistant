export interface StatisticsOverview {
  qa: { total_count: number; operator_count: number; converted_count: number; conversion_rate: number | null }
  feedback: { helpful_count: number; unhelpful_count: number; unrated_count: number; satisfaction_rate: number | null }
  work_orders: Record<"pending" | "processing" | "resolved" | "closed", number>
  knowledge_entries: Record<"pending" | "sync_failed" | "synced", number>
}

export function formatRate(rate: number | null): string {
  return rate === null ? "暂无数据" : `${rate.toFixed(2)}%`
}

export const workOrderLabels = { pending: "待处理", processing: "处理中", resolved: "已解决", closed: "已关闭" } as const
export const knowledgeLabels = { pending: "待处理", sync_failed: "同步失败", synced: "已同步" } as const

export function configurationLabel(status: "configured" | "not_configured"): string {
  return status === "configured" ? "配置完整" : "未配置"
}
