import type { ChatSource } from "./chat"

export type WorkOrderStatus = "pending" | "processing" | "resolved" | "closed"

export interface WorkOrderQA {
  id: number
  question: string
  answer: string
  resources: ChatSource[]
  created_at: string
}

export interface WorkOrderCreator {
  username: string
  display_name: string
}

export interface WorkOrder {
  id: number
  qa_record: WorkOrderQA
  creator: WorkOrderCreator | null
  symptom: string
  attempted_steps: string | null
  additional_notes: string | null
  solution: string | null
  unresolved_note: string | null
  status: WorkOrderStatus
  created_at: string
  updated_at: string
}

export interface WorkOrderPage {
  items: WorkOrder[]
  total: number
  page: number
  page_size: number
}

export interface WorkOrderLink {
  qa_record_id: number
  work_order_id: number | null
}
