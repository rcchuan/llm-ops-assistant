<script setup lang="ts">
import { computed, onMounted, ref } from "vue"
import { Coin, Connection, Monitor, RefreshRight } from "@element-plus/icons-vue"

import { getHealth } from "../api/health"

type ConnectionState = "loading" | "healthy" | "degraded" | "offline"

const state = ref<ConnectionState>("loading")
const serviceVersion = ref("-")
const checkedAt = ref("-")

const stateCopy = computed(() => {
  const labels = {
    loading: { title: "正在检查", detail: "等待后端返回联通状态" },
    healthy: { title: "链路正常", detail: "前端、后端与 MySQL 均可访问" },
    degraded: { title: "数据库不可用", detail: "后端在线，但无法连接 MySQL" },
    offline: { title: "后端不可达", detail: "请确认 FastAPI 已在 127.0.0.1:8000 启动" },
  }
  return labels[state.value]
})

const backendState = computed(() => (state.value === "offline" ? "down" : state.value === "loading" ? "checking" : "up"))
const databaseState = computed(() => {
  if (state.value === "loading") return "checking"
  return state.value === "healthy" ? "up" : "down"
})

async function checkHealth() {
  state.value = "loading"
  try {
    const health = await getHealth()
    serviceVersion.value = health.version
    state.value = health.database.status === "up" ? "healthy" : "degraded"
  } catch {
    serviceVersion.value = "-"
    state.value = "offline"
  } finally {
    checkedAt.value = new Intl.DateTimeFormat("zh-CN", {
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
    }).format(new Date())
  }
}

onMounted(checkHealth)
</script>

<template>
  <main class="page-shell">
    <header class="masthead">
      <div>
        <p class="stage-label">阶段 1 · 工程骨架</p>
        <h1>智能运维助手</h1>
      </div>
      <span class="build-label">BUILD 0.2.0</span>
    </header>

    <section class="status-summary" :data-state="state" aria-live="polite">
      <div class="summary-mark" aria-hidden="true"></div>
      <div>
        <p class="summary-label">系统联通状态</p>
        <h2>{{ stateCopy.title }}</h2>
        <p>{{ stateCopy.detail }}</p>
      </div>
      <el-button :loading="state === 'loading'" @click="checkHealth">
        <el-icon><RefreshRight /></el-icon>
        重新检查
      </el-button>
    </section>

    <section class="connection-panel" aria-label="服务连接链路">
      <div class="connection-heading">
        <h2>连接链路</h2>
        <span>实时健康检查</span>
      </div>

      <div class="service-chain">
        <article class="service-node" data-status="up">
          <el-icon><Monitor /></el-icon>
          <div>
            <span>Vue 前端</span>
            <strong>页面已加载</strong>
          </div>
          <i class="status-dot" aria-label="正常"></i>
        </article>

        <span class="chain-link" aria-hidden="true"></span>

        <article class="service-node" :data-status="backendState">
          <el-icon><Connection /></el-icon>
          <div>
            <span>FastAPI 后端</span>
            <strong>{{ backendState === "up" ? `在线 · ${serviceVersion}` : backendState === "checking" ? "检查中" : "不可达" }}</strong>
          </div>
          <i class="status-dot" :aria-label="backendState"></i>
        </article>

        <span class="chain-link" aria-hidden="true"></span>

        <article class="service-node" :data-status="databaseState">
          <el-icon><Coin /></el-icon>
          <div>
            <span>MySQL 数据库</span>
            <strong>{{ databaseState === "up" ? "连接正常" : databaseState === "checking" ? "检查中" : "连接失败" }}</strong>
          </div>
          <i class="status-dot" :aria-label="databaseState"></i>
        </article>
      </div>

      <footer class="check-meta">
        <span>GET /api/v1/health</span>
        <span>最近检查 {{ checkedAt }}</span>
      </footer>
    </section>
  </main>
</template>
