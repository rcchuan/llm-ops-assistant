<script setup lang="ts">
import { onMounted, ref } from "vue"

import { getChatHistory } from "../api/chat"
import { getApiErrorMessage } from "../api/http"
import SourceList from "../components/chat/SourceList.vue"
import type { ChatMessage } from "../types/chat"

const messages = ref<ChatMessage[]>([])
const loading = ref(true)
const errorMessage = ref("")

function formatTime(value: string) {
  return new Intl.DateTimeFormat("zh-CN", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(value))
}

async function loadHistory() {
  try {
    messages.value = await getChatHistory()
  } catch (error) {
    errorMessage.value = getApiErrorMessage(error, "问答历史加载失败")
  } finally {
    loading.value = false
  }
}

onMounted(loadHistory)
</script>

<template>
  <div class="page-view history-view">
    <header class="page-titlebar">
      <div>
        <h1>问答历史</h1>
        <p>最近 50 条个人问答记录</p>
      </div>
    </header>

    <section v-loading="loading" class="history-list">
      <el-alert v-if="errorMessage" :title="errorMessage" type="error" :closable="false" show-icon />
      <el-empty v-else-if="!loading && messages.length === 0" description="暂无问答历史" />
      <article v-for="message in messages" :key="message.id ?? message.created_at" class="history-item">
        <header>
          <time>{{ formatTime(message.created_at) }}</time>
          <el-tag v-if="message.feedback === 'helpful'" type="success" effect="plain">有帮助</el-tag>
          <el-tag v-else-if="message.feedback === 'unhelpful'" type="danger" effect="plain">无帮助</el-tag>
          <el-tag v-else type="info" effect="plain">未反馈</el-tag>
        </header>
        <div class="history-question"><strong>问题</strong><p>{{ message.question }}</p></div>
        <div class="history-answer"><strong>回答</strong><p>{{ message.answer }}</p></div>
        <SourceList :sources="message.resources" />
      </article>
    </section>
  </div>
</template>
