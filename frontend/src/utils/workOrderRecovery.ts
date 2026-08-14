import { isAxiosError } from "axios"

import type { WorkOrderLink } from "../types/workOrder"

export interface WorkOrderActionOutcome<T> {
  result: T | null
  error: unknown | null
}

export async function runWorkOrderAction<T>(
  action: () => Promise<T>,
  reconcile: () => Promise<T>,
): Promise<WorkOrderActionOutcome<T>> {
  try {
    return { result: await action(), error: null }
  } catch (error) {
    try {
      return { result: await reconcile(), error }
    } catch {
      return { result: null, error }
    }
  }
}

export async function findExistingWorkOrderAfterConflict(
  error: unknown,
  qaRecordId: number,
  loadLinks: (ids: number[]) => Promise<WorkOrderLink[]>,
): Promise<number | null> {
  if (!isAxiosError(error) || error.response?.status !== 409) return null
  try {
    const link = (await loadLinks([qaRecordId])).find(
      (item) => item.qa_record_id === qaRecordId,
    )
    return link?.work_order_id ?? null
  } catch {
    return null
  }
}
