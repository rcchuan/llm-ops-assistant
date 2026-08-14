import { computed, readonly, ref } from "vue"

import { getMe, login as requestLogin } from "../api/auth"
import { clearAccessToken, getAccessToken, setAccessToken } from "../api/http"
import type { User } from "../types/auth"


const currentUser = ref<User | null>(null)
const initialized = ref(false)

async function signIn(username: string, password: string): Promise<User> {
  const result = await requestLogin(username, password)
  setAccessToken(result.access_token)
  currentUser.value = result.user
  initialized.value = true
  return result.user
}

async function restore(): Promise<void> {
  if (initialized.value) return
  if (!getAccessToken()) {
    initialized.value = true
    return
  }
  try {
    currentUser.value = await getMe()
  } catch {
    clearAccessToken()
    currentUser.value = null
  } finally {
    initialized.value = true
  }
}

function signOut(): void {
  clearAccessToken()
  currentUser.value = null
  initialized.value = true
}

export function useAuth() {
  return {
    user: readonly(currentUser),
    initialized: readonly(initialized),
    isAdmin: computed(() => currentUser.value?.role === "admin"),
    signIn,
    restore,
    signOut,
  }
}
