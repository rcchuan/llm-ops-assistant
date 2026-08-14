<script setup lang="ts">
import { onMounted, reactive, ref } from "vue"
import { ElMessage, ElMessageBox } from "element-plus"
import { Plus } from "@element-plus/icons-vue"

import { getApiErrorMessage } from "../../api/http"
import { createUser, getUsers, resetUserPassword, updateUserStatus } from "../../api/users"
import type { User } from "../../types/auth"

const users = ref<User[]>([])
const loading = ref(false)
const page = ref(1)
const pageSize = ref(20)
const total = ref(0)

const createVisible = ref(false)
const createLoading = ref(false)
const createError = ref("")
const createForm = reactive({ username: "", displayName: "", password: "", confirmPassword: "" })

const resetVisible = ref(false)
const resetLoading = ref(false)
const resetError = ref("")
const resetTarget = ref<User | null>(null)
const resetForm = reactive({ password: "", confirmPassword: "" })

function formatTime(value: string | null): string {
  if (!value) return "-"
  return new Intl.DateTimeFormat("zh-CN", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hourCycle: "h23",
  }).format(new Date(value)).replace(/\//g, "-")
}

function validatePassword(password: string, confirmation: string): string | null {
  if (password.length < 8 || password.length > 128) return "密码长度须为 8～128 位"
  if (!/[A-Za-z]/.test(password) || !/\d/.test(password)) return "密码必须同时包含字母和数字"
  if (password !== confirmation) return "两次输入的密码不一致"
  return null
}

async function loadUsers() {
  loading.value = true
  try {
    const result = await getUsers(page.value, pageSize.value)
    users.value = result.items
    total.value = result.total
  } catch (error) {
    ElMessage.error(getApiErrorMessage(error, "用户列表加载失败"))
  } finally {
    loading.value = false
  }
}

function openCreate() {
  Object.assign(createForm, { username: "", displayName: "", password: "", confirmPassword: "" })
  createError.value = ""
  createVisible.value = true
}

async function submitCreate() {
  if (!/^[A-Za-z][A-Za-z0-9_]{3,31}$/.test(createForm.username)) {
    createError.value = "用户名须以字母开头，仅含字母、数字、下划线，长度 4～32 位"
    return
  }
  if (!createForm.displayName.trim()) {
    createError.value = "显示姓名不能为空"
    return
  }
  createError.value = validatePassword(createForm.password, createForm.confirmPassword) ?? ""
  if (createError.value) return
  createLoading.value = true
  try {
    await createUser({
      username: createForm.username,
      display_name: createForm.displayName,
      initial_password: createForm.password,
    })
    createVisible.value = false
    ElMessage.success("普通运维人员已创建")
    await loadUsers()
  } catch (error) {
    createError.value = getApiErrorMessage(error, "创建用户失败")
  } finally {
    createLoading.value = false
  }
}

async function changeStatus(user: User) {
  if (!user.is_active) {
    await applyStatus(user, true)
    return
  }
  try {
    await ElMessageBox.confirm(
      `禁用后，用户“${user.username}”将无法登录，已有 Token 也会立即失效。`,
      "确认禁用账号",
      { confirmButtonText: "禁用", cancelButtonText: "取消", type: "warning" },
    )
    await applyStatus(user, false)
  } catch (error) {
    if (error !== "cancel" && error !== "close") ElMessage.error("账号状态修改失败")
  }
}

async function applyStatus(user: User, isActive: boolean) {
  try {
    await updateUserStatus(user.id, isActive)
    ElMessage.success(isActive ? "账号已启用" : "账号已禁用")
    await loadUsers()
  } catch (error) {
    ElMessage.error(getApiErrorMessage(error, "账号状态修改失败"))
  }
}

function openReset(user: User) {
  resetTarget.value = user
  Object.assign(resetForm, { password: "", confirmPassword: "" })
  resetError.value = ""
  resetVisible.value = true
}

async function submitReset() {
  if (!resetTarget.value) return
  resetError.value = validatePassword(resetForm.password, resetForm.confirmPassword) ?? ""
  if (resetError.value) return
  resetLoading.value = true
  try {
    await resetUserPassword(resetTarget.value.id, resetForm.password)
    resetVisible.value = false
    ElMessage.success("密码已重置，用户下次登录必须修改密码")
    await loadUsers()
  } catch (error) {
    resetError.value = getApiErrorMessage(error, "密码重置失败")
  } finally {
    resetLoading.value = false
  }
}

onMounted(loadUsers)
</script>

<template>
  <div class="page-view user-management">
    <header class="page-titlebar">
      <div>
        <h1>用户管理</h1>
        <p>创建普通运维人员并管理账号状态与初始密码</p>
      </div>
      <el-button type="primary" :icon="Plus" @click="openCreate">创建用户</el-button>
    </header>

    <section class="content-panel table-panel">
      <el-table v-loading="loading" :data="users" row-key="id" border>
        <el-table-column prop="username" label="用户名" min-width="138" show-overflow-tooltip />
        <el-table-column prop="display_name" label="姓名" min-width="130" show-overflow-tooltip />
        <el-table-column label="角色" width="126">
          <template #default="{ row }">
            <el-tag :type="row.role === 'admin' ? 'primary' : 'info'" effect="plain">
              {{ row.role === "admin" ? "管理员" : "普通运维人员" }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="88">
          <template #default="{ row }">
            <el-tag :type="row.is_active ? 'success' : 'danger'" effect="plain">
              {{ row.is_active ? "启用" : "禁用" }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="密码状态" width="112">
          <template #default="{ row }">
            <el-tag :type="row.must_change_password ? 'warning' : 'info'" effect="plain">
              {{ row.must_change_password ? "需要改密" : "正常" }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="最近登录" width="168">
          <template #default="{ row }">{{ formatTime(row.last_login_at) }}</template>
        </el-table-column>
        <el-table-column label="创建时间" width="168">
          <template #default="{ row }">{{ formatTime(row.created_at) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="150" fixed="right">
          <template #default="{ row }">
            <template v-if="row.role === 'operator'">
              <el-button link :type="row.is_active ? 'danger' : 'primary'" @click="changeStatus(row)">
                {{ row.is_active ? "禁用" : "启用" }}
              </el-button>
              <el-button link type="primary" @click="openReset(row)">重置密码</el-button>
            </template>
            <span v-else class="muted-text">不可操作</span>
          </template>
        </el-table-column>
      </el-table>
      <footer class="table-footer">
        <span>共 {{ total }} 个用户</span>
        <el-pagination
          v-model:current-page="page"
          :page-size="pageSize"
          :total="total"
          layout="prev, pager, next"
          @current-change="loadUsers"
        />
      </footer>
    </section>

    <el-dialog v-model="createVisible" title="创建普通运维人员" width="500px" :close-on-click-modal="false">
      <el-alert v-if="createError" :title="createError" type="error" show-icon :closable="false" />
      <div class="dialog-form">
        <label>用户名<el-input v-model="createForm.username" maxlength="32" placeholder="字母开头，4～32 位" /></label>
        <label>显示姓名<el-input v-model="createForm.displayName" maxlength="64" /></label>
        <label>初始密码<el-input v-model="createForm.password" type="password" show-password maxlength="128" /></label>
        <label>确认密码<el-input v-model="createForm.confirmPassword" type="password" show-password maxlength="128" /></label>
        <p class="field-hint">用户首次登录后必须修改密码</p>
      </div>
      <template #footer>
        <el-button @click="createVisible = false">取消</el-button>
        <el-button type="primary" :loading="createLoading" @click="submitCreate">创建用户</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="resetVisible" title="重置密码" width="500px" :close-on-click-modal="false">
      <p class="dialog-target">目标用户：<strong>{{ resetTarget?.username }}</strong></p>
      <el-alert v-if="resetError" :title="resetError" type="error" show-icon :closable="false" />
      <div class="dialog-form">
        <label>新密码<el-input v-model="resetForm.password" type="password" show-password maxlength="128" /></label>
        <label>确认新密码<el-input v-model="resetForm.confirmPassword" type="password" show-password maxlength="128" /></label>
        <p class="field-hint">重置后，用户下次登录必须修改密码</p>
      </div>
      <template #footer>
        <el-button @click="resetVisible = false">取消</el-button>
        <el-button type="primary" :loading="resetLoading" @click="submitReset">确认重置</el-button>
      </template>
    </el-dialog>
  </div>
</template>
