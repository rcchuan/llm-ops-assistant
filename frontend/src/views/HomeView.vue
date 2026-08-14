<script setup lang="ts">
import { computed, onMounted, ref } from "vue"
import { Coin, Connection, Monitor, RefreshRight } from "@element-plus/icons-vue"

import { getHealth } from "../api/health"
import { useAuth } from "../stores/auth"

type ConnectionState = "loading" | "healthy" | "degraded" | "offline"

const auth = useAuth()
const state = ref<ConnectionState>("loading")
const serviceVersion = ref("-")
const checkedAt = ref("-")

const status = computed(() => ({
  loading: { label: "检查中", type: "warning" as const, detail: "正在确认后端与数据库状态" },
  healthy: { label: "运行正常", type: "success" as const, detail: "前端、后端与 MySQL 链路正常" },
  degraded: { label: "服务降级", type: "warning" as const, detail: "后端在线，MySQL 当前不可用" },
  offline: { label: "后端离线", type: "danger" as const, detail: "无法连接 FastAPI 服务" },
})[state.value])

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
  <div class="page-view">
    <header class="page-titlebar">
      <div>
        <h1>首页</h1>
        <p>当前账号与基础服务状态</p>
      </div>
      <el-button :icon="RefreshRight" :loading="state === 'loading'" @click="checkHealth">刷新状态</el-button>
    </header>

    <section class="identity-strip">
      <div>
        <span>当前用户</span>
        <strong>{{ auth.user.value?.display_name }}</strong>
      </div>
      <div>
        <span>账号角色</span>
        <strong>{{ auth.user.value?.role === "admin" ? "管理员" : "普通运维人员" }}</strong>
      </div>
      <div>
        <span>账号状态</span>
        <el-tag type="success" effect="plain">启用</el-tag>
      </div>
    </section>

    <section class="content-panel service-panel">
      <div class="panel-heading">
        <div>
          <h2>服务链路</h2>
          <p>{{ status.detail }}</p>
        </div>
        <el-tag :type="status.type" effect="plain">{{ status.label }}</el-tag>
      </div>
      <div class="service-chain">
        <article class="service-node" data-status="up">
          <el-icon><Monitor /></el-icon>
          <div><span>Vue 前端</span><strong>页面已加载</strong></div>
        </article>
        <span class="chain-line"></span>
        <article class="service-node" :data-status="state === 'offline' ? 'down' : state === 'loading' ? 'checking' : 'up'">
          <el-icon><Connection /></el-icon>
          <div><span>FastAPI 后端</span><strong>{{ state === "offline" ? "不可达" : serviceVersion }}</strong></div>
        </article>
        <span class="chain-line"></span>
        <article class="service-node" :data-status="state === 'healthy' ? 'up' : state === 'loading' ? 'checking' : 'down'">
          <el-icon><Coin /></el-icon>
          <div><span>MySQL 数据库</span><strong>{{ state === "healthy" ? "连接正常" : state === "loading" ? "检查中" : "连接失败" }}</strong></div>
        </article>
      </div>
      <footer class="panel-footer">
        <code>GET /api/v1/health</code>
        <span>最近检查 {{ checkedAt }}</span>
      </footer>
    </section>

    <section class="scope-note">
      <strong>阶段 3</strong>
      <span>用户认证、角色权限与智能运维问答已接入正式系统。</span>
    </section>
  </div>
</template>
