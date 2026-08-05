<script setup lang="ts">
import { computed, nextTick, onMounted, ref } from "vue"
import { ChatDotRound, Delete, Promotion } from "@element-plus/icons-vue"

import { getCurrentChat, sendChatMessage, startNewChat, updateChatFeedback } from "../api/chat"
import { getApiErrorMessage } from "../api/http"
import SourceList from "../components/chat/SourceList.vue"
import type { ChatMessage, Feedback } from "../types/chat"

const quickQuestions = [
  "MySQL 主从延迟怎么排查？",
  "Linux 磁盘空间不足怎么处理？",
  "Prometheus CPU 使用率告警怎么排查？",
  "网络访问超时应该如何定位？",
]

const messages = ref<ChatMessage[]>([])
const question = ref("")
const loading = ref(false)
const restoring = ref(true)
const errorMessage = ref("")
const startNew = ref(false)
const locked = ref(false)
const messageList = ref<HTMLElement | null>(null)
let stateVersion = 0

const lockedMessage = computed(() =>
  messages.value[messages.value.length - 1]?.persisted === null
    ? "保存状态无法确认，请勿重复提交，当前对话无法继续，请点击‘新对话’后继续"
    : "本次回答未保存，当前对话无法继续，请点击‘新对话’重新开始",
)

async function restoreChat() {
  const version = ++stateVersion
  restoring.value = true
  try {
    const current = await getCurrentChat()
    if (version !== stateVersion) return
    messages.value = current.messages
  } catch (error) {
    if (version !== stateVersion) return
    errorMessage.value = getApiErrorMessage(error, "当前会话加载失败")
  } finally {
    if (version === stateVersion) restoring.value = false
  }
}

async function scrollToBottom() {
  await nextTick()
  messageList.value?.scrollTo({ top: messageList.value.scrollHeight, behavior: "smooth" })
}

async function submitQuestion() {
  const normalized = question.value.trim()
  if (!normalized || loading.value || locked.value || restoring.value) return
  const version = ++stateVersion
  loading.value = true
  errorMessage.value = ""
  try {
    const message = await sendChatMessage(normalized, startNew.value)
    if (version !== stateVersion) return
    messages.value.push(message)
    question.value = ""
    startNew.value = false
    locked.value = message.conversation_locked
    await scrollToBottom()
  } catch (error) {
    if (version !== stateVersion) return
    errorMessage.value = getApiErrorMessage(error, "回答生成失败，请稍后重试")
  } finally {
    if (version === stateVersion) loading.value = false
  }
}

async function newChat() {
  if (restoring.value || loading.value) return
  const version = ++stateVersion
  try {
    await startNewChat()
    if (version !== stateVersion) return
    messages.value = []
    question.value = ""
    errorMessage.value = ""
    startNew.value = true
    locked.value = false
  } catch (error) {
    if (version !== stateVersion) return
    errorMessage.value = getApiErrorMessage(error, "新对话创建失败")
  }
}

async function setFeedback(message: ChatMessage, feedback: Feedback) {
  if (message.id === null) return
  try {
    const updated = await updateChatFeedback(message.id, feedback)
    message.feedback = updated.feedback
  } catch (error) {
    errorMessage.value = getApiErrorMessage(error, "反馈保存失败")
  }
}

function fillQuestion(value: string) {
  question.value = value
}

onMounted(restoreChat)
</script>

<template>
  <div class="page-view chat-view">
    <header class="page-titlebar">
      <div>
        <h1>智能运维问答</h1>
        <p>基于现有运维知识库生成回答</p>
      </div>
      <el-button :icon="Delete" :disabled="loading || restoring" @click="newChat">新对话</el-button>
    </header>

    <section class="chat-panel">
      <div ref="messageList" v-loading="restoring" class="message-list">
        <div v-if="!restoring && messages.length === 0" class="chat-empty">
          <el-icon><ChatDotRound /></el-icon>
          <h2>从一个运维问题开始</h2>
          <div class="quick-questions">
            <button v-for="item in quickQuestions" :key="item" type="button" @click="fillQuestion(item)">
              {{ item }}
            </button>
          </div>
        </div>

        <article v-for="message in messages" :key="message.id ?? message.created_at" class="message-exchange">
          <div class="user-message">
            <span>你的问题</span>
            <p>{{ message.question }}</p>
          </div>
          <div class="assistant-message">
            <span>智能助手</span>
            <p class="answer-text">{{ message.answer }}</p>
            <SourceList :sources="message.resources" />
            <div v-if="message.persisted === true && message.id !== null" class="feedback-actions">
              <span>这条回答：</span>
              <el-button
                size="small"
                :type="message.feedback === 'helpful' ? 'primary' : 'default'"
                plain
                @click="setFeedback(message, 'helpful')"
              >有帮助</el-button>
              <el-button
                size="small"
                :type="message.feedback === 'unhelpful' ? 'danger' : 'default'"
                plain
                @click="setFeedback(message, 'unhelpful')"
              >无帮助</el-button>
            </div>
            <el-alert
              v-if="message.persisted === false"
              title="本次回答未保存到历史，刷新后将丢失"
              type="warning"
              :closable="false"
              show-icon
            />
            <el-alert
              v-else-if="message.persisted === null"
              title="保存状态无法确认，请勿重复提交"
              type="warning"
              :closable="false"
              show-icon
            />
          </div>
        </article>

        <div v-if="loading" class="answer-loading">正在查询运维知识库并生成回答……</div>
      </div>

      <div class="chat-composer">
        <el-alert
          v-if="locked"
          :title="lockedMessage"
          type="warning"
          :closable="false"
          show-icon
        />
        <el-alert v-else-if="errorMessage" :title="errorMessage" type="error" :closable="false" show-icon />
        <div class="composer-row">
          <el-input
            v-model="question"
            type="textarea"
            resize="none"
            :rows="3"
            maxlength="1000"
            show-word-limit
            :disabled="loading || locked || restoring"
            placeholder="请输入运维问题"
            @keydown.ctrl.enter.prevent="submitQuestion"
          />
          <el-button
            type="primary"
            :icon="Promotion"
            :loading="loading"
            :disabled="!question.trim() || locked || restoring"
            @click="submitQuestion"
          >发送</el-button>
        </div>
      </div>
    </section>
  </div>
</template>
