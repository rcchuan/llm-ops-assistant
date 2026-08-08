export type KnowledgeEntryStatus = "pending" | "sync_failed" | "synced"

export interface KnowledgeEntry {
  id: number
  work_order_id: number
  title: string
  content: string
  status: KnowledgeEntryStatus
  dify_document_id: string | null
  sync_error: string | null
  synced_at: string | null
  created_at: string
  updated_at: string
}

export interface KnowledgeEntryPage {
  items: KnowledgeEntry[]
  total: number
  page: number
  page_size: number
}
