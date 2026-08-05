<script setup lang="ts">
import type { ChatSource } from "../../types/chat"

defineProps<{ sources: ChatSource[] }>()
</script>

<template>
  <details class="source-list">
    <summary>参考来源（{{ sources.length }}）</summary>
    <p v-if="sources.length === 0" class="source-empty">本次回答未返回参考来源</p>
    <ol v-else>
      <li v-for="(source, index) in sources" :key="`${source.document_name}-${index}`">
        <strong>{{ source.document_name }}</strong>
        <p>{{ source.content }}</p>
      </li>
    </ol>
  </details>
</template>
