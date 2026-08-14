<script setup lang="ts">
import { onMounted, reactive, ref } from "vue"
import { Check, Upload } from "@element-plus/icons-vue"
import { ElMessage } from "element-plus"

import {
  listKnowledgeEntries,
  syncKnowledgeEntry,
  updateKnowledgeEntry,
} from "../../api/knowledgeEntries"
import { getApiErrorMessage } from "../../api/http"
import type {
  KnowledgeEntry,
  KnowledgeEntryPage,
  KnowledgeEntryStatus,
} from "../../types/knowledgeEntry"
import {
  mergeReconciledDrafts,
  runKnowledgeSyncAction,
} from "../../utils/knowledgeSyncRecovery"

interface Draft {
  title: string
  content: string
}

const items = ref<KnowledgeEntry[]>([])
const drafts = reactive<Record<number, Draft>>({})
const submitting = reactive(new Set<number>())
const loading = ref(false)
const page = ref(1)
const total = ref(0)
const errorMessage = ref("")

const statusLabels: Record<KnowledgeEntryStatus, string> = {
  pending: "待审核",
  sync_failed: "同步失败",
  synced: "已同步",
}

function statusType(status: KnowledgeEntryStatus) {
  if (status === "synced") return "success"
  if (status === "sync_failed") return "danger"
  return "warning"
}

function formatTime(value: string | null) {
  if (!value) return "-"
  return new Intl.DateTimeFormat("zh-CN", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value))
}

function applyPage(result: KnowledgeEntryPage, reconciledEntryId?: number) {
  items.value = result.items
  total.value = result.total
  if (reconciledEntryId !== undefined) {
    Object.assign(
      drafts,
      mergeReconciledDrafts(drafts, result.items, reconciledEntryId),
    )
    return
  }
  for (const entry of result.items) {
    drafts[entry.id] = { title: entry.title, content: entry.content }
  }
}

async function loadEntries() {
  loading.value = true
  errorMessage.value = ""
  try {
    applyPage(await listKnowledgeEntries(page.value))
  } catch (error) {
    errorMessage.value = getApiErrorMessage(error, "候选知识加载失败")
  } finally {
    loading.value = false
  }
}

async function reconcileEntry(entryId: number): Promise<KnowledgeEntry | null> {
  const result = await listKnowledgeEntries(page.value)
  applyPage(result, entryId)
  return result.items.find((entry) => entry.id === entryId) ?? null
}

function replaceEntry(result: KnowledgeEntry) {
  const index = items.value.findIndex((entry) => entry.id === result.id)
  if (index >= 0) items.value[index] = result
  drafts[result.id] = { title: result.title, content: result.content }
}

async function save(entry: KnowledgeEntry) {
  if (submitting.has(entry.id)) return
  const draft = drafts[entry.id]
  if (!draft?.title.trim() || !draft.content.trim()) {
    errorMessage.value = "标题和正文不能为空"
    return
  }
  submitting.add(entry.id)
  errorMessage.value = ""
  try {
    replaceEntry(await updateKnowledgeEntry(entry.id, draft.title, draft.content))
    ElMessage.success("候选知识已保存")
  } catch (error) {
    errorMessage.value = getApiErrorMessage(error, "候选知识保存失败")
  } finally {
    submitting.delete(entry.id)
  }
}

async function sync(entry: KnowledgeEntry) {
  if (submitting.has(entry.id)) return
  submitting.add(entry.id)
  errorMessage.value = ""
  try {
    const outcome = await runKnowledgeSyncAction(
      () => syncKnowledgeEntry(entry.id),
      () => reconcileEntry(entry.id),
    )
    if (outcome.result) replaceEntry(outcome.result)
    if (outcome.error) {
      errorMessage.value = getApiErrorMessage(outcome.error, "知识同步失败")
    } else {
      ElMessage.success("候选知识已同步至 Dify")
    }
  } finally {
    submitting.delete(entry.id)
  }
}

onMounted(loadEntries)
</script>

<template>
  <div class="page-view knowledge-view">
    <header class="page-titlebar">
      <div>
        <h1>候选知识</h1>
        <p>共 {{ total }} 条</p>
      </div>
    </header>

    <el-alert
      v-if="errorMessage"
      :title="errorMessage"
      type="error"
      :closable="false"
      show-icon
      class="knowledge-alert"
    />

    <section v-loading="loading" class="knowledge-list">
      <article v-for="entry in items" :key="entry.id" class="knowledge-entry">
        <header class="knowledge-entry-header">
          <div>
            <h2>KE-{{ entry.id }}</h2>
            <span>来源 WO-{{ entry.work_order_id.toString().padStart(6, "0") }}</span>
          </div>
          <el-tag :type="statusType(entry.status)" effect="plain">
            {{ statusLabels[entry.status] }}
          </el-tag>
        </header>

        <el-form
          v-if="entry.status !== 'synced'"
          label-position="top"
          class="knowledge-form"
        >
          <el-form-item label="标题">
            <el-input v-model="drafts[entry.id].title" maxlength="1000" show-word-limit />
          </el-form-item>
          <el-form-item label="Markdown 正文">
            <el-input
              v-model="drafts[entry.id].content"
              type="textarea"
              :rows="12"
            />
          </el-form-item>
        </el-form>

        <div v-else class="knowledge-readonly">
          <h3>{{ entry.title }}</h3>
          <pre>{{ entry.content }}</pre>
        </div>

        <el-alert
          v-if="entry.sync_error"
          :title="entry.sync_error"
          type="error"
          :closable="false"
          show-icon
        />

        <dl class="knowledge-meta">
          <div><dt>Dify 文档 ID</dt><dd>{{ entry.dify_document_id || "-" }}</dd></div>
          <div><dt>创建时间</dt><dd>{{ formatTime(entry.created_at) }}</dd></div>
          <div><dt>更新时间</dt><dd>{{ formatTime(entry.updated_at) }}</dd></div>
          <div><dt>同步时间</dt><dd>{{ formatTime(entry.synced_at) }}</dd></div>
        </dl>

        <div v-if="entry.status !== 'synced'" class="action-row">
          <el-button
            :icon="Check"
            :loading="submitting.has(entry.id)"
            :disabled="submitting.has(entry.id)"
            @click="save(entry)"
          >保存修改</el-button>
          <el-button
            type="primary"
            :icon="Upload"
            :loading="submitting.has(entry.id)"
            :disabled="submitting.has(entry.id)"
            @click="sync(entry)"
          >审核并同步</el-button>
        </div>
        <el-alert
          v-else
          title="已同步至 Dify；如需修改，请前往 Dify 控制台。"
          type="success"
          :closable="false"
          show-icon
          class="synced-note"
        />
      </article>

      <el-empty v-if="!loading && items.length === 0" description="暂无候选知识" />
      <el-pagination
        v-if="total > 20"
        v-model:current-page="page"
        :page-size="20"
        :total="total"
        layout="prev, pager, next"
        @current-change="loadEntries"
      />
    </section>
  </div>
</template>
