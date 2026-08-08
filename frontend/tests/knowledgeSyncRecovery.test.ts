import assert from "node:assert/strict"
import test from "node:test"

import {
  mergeReconciledDrafts,
  runKnowledgeSyncAction,
} from "../src/utils/knowledgeSyncRecovery.ts"


test("同步成功后不发起对账读取", async () => {
  let reconciliations = 0
  const result = await runKnowledgeSyncAction(
    async () => ({ id: 7, status: "synced" }),
    async () => {
      reconciliations += 1
      return null
    },
  )

  assert.deepEqual(result, { result: { id: 7, status: "synced" }, error: null })
  assert.equal(reconciliations, 0)
})


test("同步失败后只对账一次并保留原错误", async () => {
  const original = new Error("write failed")
  let reconciliations = 0
  const result = await runKnowledgeSyncAction(
    async () => { throw original },
    async () => {
      reconciliations += 1
      return { id: 7, status: "sync_failed" }
    },
  )

  assert.deepEqual(result.result, { id: 7, status: "sync_failed" })
  assert.equal(result.error, original)
  assert.equal(reconciliations, 1)
})


test("对账读取也失败时仍保留原同步错误", async () => {
  const original = new Error("write failed")
  const result = await runKnowledgeSyncAction(
    async () => { throw original },
    async () => { throw new Error("read failed") },
  )

  assert.equal(result.result, null)
  assert.equal(result.error, original)
})


test("同步失败对账只刷新目标草稿并保留其它未保存编辑", () => {
  const drafts = {
    1: { title: "目标旧标题", content: "目标旧正文" },
    2: { title: "其它未保存标题", content: "其它未保存正文" },
  }

  const result = mergeReconciledDrafts(
    drafts,
    [
      { id: 1, title: "目标服务端标题", content: "目标服务端正文" },
      { id: 2, title: "其它服务端标题", content: "其它服务端正文" },
      { id: 3, title: "新条目标题", content: "新条目正文" },
    ],
    1,
  )

  assert.deepEqual(result, {
    1: { title: "目标服务端标题", content: "目标服务端正文" },
    2: { title: "其它未保存标题", content: "其它未保存正文" },
    3: { title: "新条目标题", content: "新条目正文" },
  })
})
