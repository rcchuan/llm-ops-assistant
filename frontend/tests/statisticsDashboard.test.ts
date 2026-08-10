import assert from "node:assert/strict"
import test from "node:test"

import { loadAdminDashboard } from "../src/utils/statisticsDashboard.ts"

test("loads statistics and health concurrently when both succeed", async () => {
  let statisticsCalls = 0
  let healthCalls = 0
  const statistics = { qa: { total_count: 10 } }
  const health = { status: "ok", database: { status: "up" } }

  const result = await loadAdminDashboard(
    async () => { statisticsCalls += 1; return statistics },
    async () => { healthCalls += 1; return health },
  )

  assert.deepEqual(result, {
    statistics: { data: statistics, error: null },
    health: { data: health, error: null },
  })
  assert.equal(statisticsCalls, 1)
  assert.equal(healthCalls, 1)
})

test("keeps statistics when health network request fails", async () => {
  const statistics = { qa: { total_count: 10 } }
  const result = await loadAdminDashboard(
    async () => statistics,
    async () => { throw new Error("network down") },
  )

  assert.deepEqual(result.statistics, { data: statistics, error: null })
  assert.deepEqual(result.health, { data: null, error: "健康检查失败" })
})

test("keeps healthy service state when statistics fails", async () => {
  const health = { status: "ok", database: { status: "up" } }
  const result = await loadAdminDashboard(
    async () => { throw new Error("statistics failed") },
    async () => health,
  )

  assert.deepEqual(result.statistics, { data: null, error: "统计数据加载失败" })
  assert.deepEqual(result.health, { data: health, error: null })
})

test("keeps readable 503 health body when statistics fails", async () => {
  const degradedHealth = { status: "degraded", database: { status: "down" } }
  const result = await loadAdminDashboard(
    async () => { throw new Error("database unavailable") },
    async () => degradedHealth,
  )

  assert.deepEqual(result.statistics, { data: null, error: "统计数据加载失败" })
  assert.deepEqual(result.health, { data: degradedHealth, error: null })
})

test("each refresh requests statistics and health exactly once", async () => {
  let statisticsCalls = 0
  let healthCalls = 0
  const refresh = () => loadAdminDashboard(
    async () => { statisticsCalls += 1; return "statistics" },
    async () => { healthCalls += 1; return "health" },
  )

  await refresh()
  await refresh()

  assert.equal(statisticsCalls, 2)
  assert.equal(healthCalls, 2)
})
