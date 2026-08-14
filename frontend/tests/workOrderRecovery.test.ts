import assert from "node:assert/strict"
import test from "node:test"

import {
  findExistingWorkOrderAfterConflict,
  runWorkOrderAction,
} from "../src/utils/workOrderRecovery.ts"


test("状态写请求失败后只对账一次并保留原错误", async () => {
  const originalError = new Error("请求超时")
  let writeCount = 0
  let readCount = 0

  const outcome = await runWorkOrderAction(
    async () => { writeCount += 1; throw originalError },
    async () => { readCount += 1; return { status: "resolved" } },
  )

  assert.equal(writeCount, 1)
  assert.equal(readCount, 1)
  assert.equal(outcome.error, originalError)
  assert.deepEqual(outcome.result, { status: "resolved" })
})

test("状态写请求成功后不发起对账读取", async () => {
  let readCount = 0
  const expected = { status: "processing" }

  const outcome = await runWorkOrderAction(
    async () => expected,
    async () => { readCount += 1; return { status: "resolved" } },
  )

  assert.equal(readCount, 0)
  assert.equal(outcome.error, null)
  assert.equal(outcome.result, expected)
})

test("对账读取也失败时仍保留原写请求错误", async () => {
  const originalError = new Error("写请求失败")
  const outcome = await runWorkOrderAction(
    async () => { throw originalError },
    async () => { throw new Error("对账失败") },
  )

  assert.equal(outcome.error, originalError)
  assert.equal(outcome.result, null)
})

test("创建返回 409 时通过 links 找到已有工单", async () => {
  const conflict = { isAxiosError: true, response: { status: 409 } }
  let linksCount = 0

  const orderId = await findExistingWorkOrderAfterConflict(conflict, 7, async (ids) => {
    linksCount += 1
    assert.deepEqual(ids, [7])
    return [{ qa_record_id: 7, work_order_id: 12 }]
  })

  assert.equal(linksCount, 1)
  assert.equal(orderId, 12)
})

test("非 409 或 links 失败时不伪造已有工单", async () => {
  let linksCount = 0
  const loadLinks = async () => {
    linksCount += 1
    throw new Error("links failed")
  }

  assert.equal(await findExistingWorkOrderAfterConflict(new Error("failed"), 7, loadLinks), null)
  assert.equal(linksCount, 0)
  assert.equal(
    await findExistingWorkOrderAfterConflict(
      { isAxiosError: true, response: { status: 409 } },
      7,
      loadLinks,
    ),
    null,
  )
  assert.equal(linksCount, 1)
})
