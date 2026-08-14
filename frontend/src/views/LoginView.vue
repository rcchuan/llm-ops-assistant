<script setup lang="ts">
import { reactive, ref } from "vue"
import { useRouter } from "vue-router"
import { Lock, User } from "@element-plus/icons-vue"

import { getApiErrorMessage } from "../api/http"
import { useAuth } from "../stores/auth"

const router = useRouter()
const auth = useAuth()
const form = reactive({ username: "", password: "" })
const loading = ref(false)
const errorMessage = ref("")

async function submit() {
  errorMessage.value = ""
  if (!form.username.trim() || !form.password) {
    errorMessage.value = "请输入用户名和密码"
    return
  }
  loading.value = true
  try {
    const user = await auth.signIn(form.username, form.password)
    await router.replace(user.must_change_password ? "/change-password" : "/")
  } catch (error) {
    errorMessage.value = getApiErrorMessage(error, "登录失败，请检查服务状态")
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <main class="login-page">
    <section class="login-panel">
      <div class="login-heading">
        <span class="product-mark">OPS</span>
        <div>
          <h1>智能运维问答与工单辅助系统</h1>
          <p>用户身份认证</p>
        </div>
      </div>

      <el-alert v-if="errorMessage" :title="errorMessage" type="error" show-icon :closable="false" />
      <form class="login-form" @submit.prevent="submit">
        <label for="username">用户名</label>
        <el-input
          id="username"
          v-model="form.username"
          data-testid="login-username"
          :prefix-icon="User"
          maxlength="32"
          autocomplete="username"
          placeholder="请输入用户名"
        />
        <label for="password">密码</label>
        <el-input
          id="password"
          v-model="form.password"
          data-testid="login-password"
          :prefix-icon="Lock"
          type="password"
          maxlength="128"
          autocomplete="current-password"
          show-password
          placeholder="请输入密码"
        />
        <el-button
          data-testid="login-submit"
          type="primary"
          native-type="submit"
          :loading="loading"
        >
          登录
        </el-button>
      </form>
    </section>
  </main>
</template>
