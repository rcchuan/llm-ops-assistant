import assert from "node:assert/strict"
import test from "node:test"
import { readFile } from "node:fs/promises"

import { acceptsHealthStatus } from "../src/types/health.ts"
import { configurationLabel, formatRate, knowledgeLabels, workOrderLabels } from "../src/types/statistics.ts"

test("statistics rates show no-data and two decimal percentages", () => {
  assert.equal(formatRate(null), "暂无数据")
  assert.equal(formatRate(75), "75.00%")
  assert.equal(formatRate(16.67), "16.67%")
})

test("fixed distributions and Dify configuration wording are stable", () => {
  assert.deepEqual(Object.keys(workOrderLabels), ["pending", "processing", "resolved", "closed"])
  assert.deepEqual(Object.keys(knowledgeLabels), ["pending", "sync_failed", "synced"])
  assert.equal(configurationLabel("configured"), "配置完整")
  assert.equal(configurationLabel("not_configured"), "未配置")
})

test("health treats 503 as a readable response", () => {
  assert.equal(acceptsHealthStatus(200), true)
  assert.equal(acceptsHealthStatus(503), true)
  assert.equal(acceptsHealthStatus(500), false)
})

test("admin route and menu remain role guarded", async () => {
  const router = await readFile(new URL("../src/router/index.ts", import.meta.url), "utf8")
  const layout = await readFile(new URL("../src/layouts/AppLayout.vue", import.meta.url), "utf8")
  assert.match(router, /path: "admin\/statistics"/)
  assert.match(router, /meta: \{ adminOnly: true \}/)
  assert.match(layout, /if \(auth\.isAdmin\.value\)/)
  assert.match(layout, /label: "统计看板"/)
})
