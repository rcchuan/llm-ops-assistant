import { http } from "./http"
import type { KnowledgeEntry, KnowledgeEntryPage } from "../types/knowledgeEntry"


export async function listKnowledgeEntries(page = 1): Promise<KnowledgeEntryPage> {
  return (await http.get<KnowledgeEntryPage>("/knowledge-entries", { params: { page } })).data
}

export async function updateKnowledgeEntry(
  id: number,
  title: string,
  content: string,
): Promise<KnowledgeEntry> {
  return (await http.put<KnowledgeEntry>(`/knowledge-entries/${id}`, { title, content })).data
}

export async function syncKnowledgeEntry(id: number): Promise<KnowledgeEntry> {
  return (await http.post<KnowledgeEntry>(`/knowledge-entries/${id}/sync`)).data
}
