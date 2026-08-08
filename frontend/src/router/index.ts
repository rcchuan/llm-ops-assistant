import { createRouter, createWebHistory } from "vue-router"

import AppLayout from "../layouts/AppLayout.vue"
import { useAuth } from "../stores/auth"
import ChangePasswordView from "../views/ChangePasswordView.vue"
import ChatHistoryView from "../views/ChatHistoryView.vue"
import ChatView from "../views/ChatView.vue"
import HomeView from "../views/HomeView.vue"
import LoginView from "../views/LoginView.vue"
import UserManagementView from "../views/admin/UserManagementView.vue"
import KnowledgeEntriesView from "../views/admin/KnowledgeEntriesView.vue"
import WorkOrderCreateView from "../views/work-orders/WorkOrderCreateView.vue"
import WorkOrderDetailView from "../views/work-orders/WorkOrderDetailView.vue"
import WorkOrderListView from "../views/work-orders/WorkOrderListView.vue"

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
        { path: "chat", component: ChatView },
        { path: "chat/history", component: ChatHistoryView },
        { path: "work-orders", component: WorkOrderListView },
        {
          path: "work-orders/new/:qaRecordId",
          component: WorkOrderCreateView,
          meta: { operatorOnly: true },
        },
        { path: "work-orders/:id", component: WorkOrderDetailView },
        { path: "change-password", component: ChangePasswordView },
        {
          path: "admin/users",
          component: UserManagementView,
          meta: { adminOnly: true },
        },
        {
          path: "admin/knowledge-entries",
          component: KnowledgeEntriesView,
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
  if (to.meta.operatorOnly && auth.isAdmin.value) return "/work-orders"
  return true
})

export default router
