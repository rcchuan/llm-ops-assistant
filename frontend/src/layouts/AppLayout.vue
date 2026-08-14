<script setup lang="ts">
import { computed, ref } from "vue"
import { useRoute, useRouter } from "vue-router"
import { ChatDotRound, Clock, Collection, DataAnalysis, Expand, Fold, HomeFilled, Key, Tickets, UserFilled } from "@element-plus/icons-vue"

import { useAuth } from "../stores/auth"

const collapsed = ref(false)
const route = useRoute()
const router = useRouter()
const auth = useAuth()

const roleLabel = computed(() => (auth.user.value?.role === "admin" ? "管理员" : "普通运维人员"))
const menuItems = computed(() => {
  if (auth.user.value?.must_change_password) {
    return [{ path: "/change-password", label: "修改密码", icon: Key }]
  }
  const items = [{ path: "/", label: "首页", icon: HomeFilled }]
  items.push({ path: "/chat", label: "智能问答", icon: ChatDotRound })
  items.push({ path: "/chat/history", label: "问答历史", icon: Clock })
  items.push({ path: "/work-orders", label: auth.isAdmin.value ? "工单管理" : "我的工单", icon: Tickets })
  if (auth.isAdmin.value) {
    items.push({ path: "/admin/statistics", label: "统计看板", icon: DataAnalysis })
    items.push({ path: "/admin/knowledge-entries", label: "候选知识", icon: Collection })
    items.push({ path: "/admin/users", label: "用户管理", icon: UserFilled })
  }
  items.push({ path: "/change-password", label: "修改密码", icon: Key })
  return items
})

function logout() {
  auth.signOut()
  router.push("/login")
}
</script>

<template>
  <div class="app-frame" :class="{ 'sidebar-collapsed': collapsed }">
    <header class="topbar">
      <div class="system-name">智能运维问答与工单辅助系统</div>
      <div class="current-user">
        <span class="user-name">{{ auth.user.value?.display_name }}</span>
        <span class="role-text">{{ roleLabel }}</span>
        <el-button link class="logout-button" @click="logout">退出</el-button>
      </div>
    </header>

    <aside class="sidebar">
      <el-menu :default-active="route.path" router :collapse="collapsed">
        <el-menu-item v-for="item in menuItems" :key="item.path" :index="item.path">
          <el-icon><component :is="item.icon" /></el-icon>
          <template #title>{{ item.label }}</template>
        </el-menu-item>
      </el-menu>
      <el-tooltip :content="collapsed ? '展开侧边栏' : '折叠侧边栏'" placement="right">
        <button class="collapse-button" type="button" @click="collapsed = !collapsed">
          <el-icon><component :is="collapsed ? Expand : Fold" /></el-icon>
        </button>
      </el-tooltip>
    </aside>

    <main class="workspace">
      <RouterView />
    </main>
  </div>
</template>
