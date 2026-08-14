export interface KnowledgeSyncOutcome<T> {
  result: T | null
  error: unknown | null
}

export interface KnowledgeDraft {
  title: string
  content: string
}

interface DraftSource extends KnowledgeDraft {
  id: number
}

export function mergeReconciledDrafts(
  current: Record<number, KnowledgeDraft>,
  entries: DraftSource[],
  reconciledEntryId: number,
): Record<number, KnowledgeDraft> {
  const merged = { ...current }
  for (const entry of entries) {
    if (entry.id === reconciledEntryId || !merged[entry.id]) {
      merged[entry.id] = { title: entry.title, content: entry.content }
    }
  }
  return merged
}

export async function runKnowledgeSyncAction<T>(
  action: () => Promise<T>,
  reconcile: () => Promise<T | null>,
): Promise<KnowledgeSyncOutcome<T>> {
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
