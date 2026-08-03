<script setup lang="ts">
import { reactive, ref } from "vue"
import { useRouter } from "vue-router"
import { ElMessage } from "element-plus"

import { changePassword } from "../api/auth"
import { getApiErrorMessage } from "../api/http"
import { useAuth } from "../stores/auth"

const router = useRouter()
const auth = useAuth()
const form = reactive({ currentPassword: "", newPassword: "", confirmPassword: "" })
const loading = ref(false)
const errorMessage = ref("")

function validate(): string | null {
  if (!form.currentPassword || !form.newPassword || !form.confirmPassword) return "请完整填写密码信息"
  if (form.newPassword.length < 8 || form.newPassword.length > 128) return "新密码长度须为 8～128 位"
  if (!/[A-Za-z]/.test(form.newPassword) || !/\d/.test(form.newPassword)) return "新密码必须同时包含字母和数字"
  if (form.newPassword !== form.confirmPassword) return "两次输入的新密码不一致"
  return null
}

async function submit() {
  errorMessage.value = validate() ?? ""
  if (errorMessage.value) return
  loading.value = true
  try {
    await changePassword(form.currentPassword, form.newPassword)
    auth.signOut()
    ElMessage.success("密码修改成功，请使用新密码重新登录")
    await router.replace("/login")
  } catch (error) {
    errorMessage.value = getApiErrorMessage(error, "密码修改失败")
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="page-view narrow-view">
    <header class="page-titlebar">
      <div>
        <h1>修改密码</h1>
        <p>{{ auth.user.value?.must_change_password ? "首次登录必须完成密码修改" : "定期更新密码有助于保护账号安全" }}</p>
      </div>
    </header>

    <section class="content-panel password-panel">
      <el-alert
        v-if="auth.user.value?.must_change_password"
        title="完成修改前，仅可查看当前账号信息和访问本页面"
        type="warning"
        show-icon
        :closable="false"
      />
      <el-alert v-if="errorMessage" :title="errorMessage" type="error" show-icon :closable="false" />
      <form class="field-form" @submit.prevent="submit">
        <div class="field-row">
          <label for="current-password">当前密码</label>
          <el-input id="current-password" v-model="form.currentPassword" type="password" show-password maxlength="128" autocomplete="current-password" />
        </div>
        <div class="field-row">
          <label for="new-password">新密码</label>
          <div>
            <el-input id="new-password" v-model="form.newPassword" type="password" show-password maxlength="128" autocomplete="new-password" />
            <p class="field-hint">8～128 位，必须同时包含字母和数字</p>
          </div>
        </div>
        <div class="field-row">
          <label for="confirm-password">确认新密码</label>
          <el-input id="confirm-password" v-model="form.confirmPassword" type="password" show-password maxlength="128" autocomplete="new-password" />
        </div>
        <div class="form-actions">
          <el-button type="primary" native-type="submit" :loading="loading">保存并重新登录</el-button>
        </div>
      </form>
    </section>
  </div>
</template>
