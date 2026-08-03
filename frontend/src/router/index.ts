import { createRouter, createWebHistory } from "vue-router"

import AppLayout from "../layouts/AppLayout.vue"
import { useAuth } from "../stores/auth"
import ChangePasswordView from "../views/ChangePasswordView.vue"
import HomeView from "../views/HomeView.vue"
import LoginView from "../views/LoginView.vue"
import UserManagementView from "../views/admin/UserManagementView.vue"

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: "/login", component: LoginView, meta: { public: true } },
    {
      path: "/",
      component: AppLayout,
      meta: { requiresAuth: true },
      children: [
        { path: "", component: HomeView },
        { path: "change-password", component: ChangePasswordView },
        {
          path: "admin/users",
          component: UserManagementView,
          meta: { adminOnly: true },
        },
      ],
    },
    { path: "/:pathMatch(.*)*", redirect: "/" },
  ],
})

router.beforeEach(async (to) => {
  const auth = useAuth()
  await auth.restore()

  if (to.meta.public) {
    if (!auth.user.value) return true
    return auth.user.value.must_change_password ? "/change-password" : "/"
  }
  if (!auth.user.value) return { path: "/login", query: { redirect: to.fullPath } }
  if (auth.user.value.must_change_password && to.path !== "/change-password") {
    return "/change-password"
  }
  if (to.meta.adminOnly && !auth.isAdmin.value) return "/"
  return true
})

export default router
