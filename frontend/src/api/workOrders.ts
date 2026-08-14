import { http } from "./http"
import type { WorkOrder, WorkOrderLink, WorkOrderPage } from "../types/workOrder"

export interface WorkOrderCreatePayload {
  qa_record_id: number
  symptom: string
  attempted_steps?: string
  additional_notes?: string
}

export async function createWorkOrder(payload: WorkOrderCreatePayload): Promise<WorkOrder> {
  return (await http.post<WorkOrder>("/work-orders", payload)).data
}

export async function listWorkOrders(page = 1): Promise<WorkOrderPage> {
  return (await http.get<WorkOrderPage>("/work-orders", { params: { page, page_size: 20 } })).data
}

export async function getWorkOrder(id: number): Promise<WorkOrder> {
  return (await http.get<WorkOrder>(`/work-orders/${id}`)).data
}

export async function getWorkOrderLinks(ids: number[]): Promise<WorkOrderLink[]> {
  if (ids.length === 0) return []
  return (await http.post<{ items: WorkOrderLink[] }>("/work-orders/links", { qa_record_ids: ids })).data.items
}

export async function startWorkOrder(id: number): Promise<WorkOrder> {
  return (await http.post<WorkOrder>(`/work-orders/${id}/start`)).data
}

export async function saveProcessingContent(
  id: number,
  solution: string,
): Promise<WorkOrder> {
  return (await http.put<WorkOrder>(`/work-orders/${id}/processing-content`, { solution })).data
}

export async function resolveWorkOrder(
  id: number,
  solution: string,
): Promise<WorkOrder> {
  return (await http.post<WorkOrder>(`/work-orders/${id}/resolve`, { solution })).data
}

export async function confirmWorkOrder(id: number): Promise<WorkOrder> {
  return (await http.post<WorkOrder>(`/work-orders/${id}/confirm`)).data
}

export async function reopenWorkOrder(id: number, unresolved_note: string): Promise<WorkOrder> {
  return (await http.post<WorkOrder>(`/work-orders/${id}/reopen`, { unresolved_note })).data
}
