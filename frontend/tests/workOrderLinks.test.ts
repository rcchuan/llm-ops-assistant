import assert from "node:assert/strict"
import test from "node:test"

import { hasKnownWorkOrderLink } from "../src/utils/workOrderLinks.ts"


test("只有成功查询到映射项时才显示工单入口", () => {
  assert.equal(hasKnownWorkOrderLink({}, 1), false)
  assert.equal(hasKnownWorkOrderLink({ 1: null }, 1), true)
  assert.equal(hasKnownWorkOrderLink({ 1: 9 }, 1), true)
})
