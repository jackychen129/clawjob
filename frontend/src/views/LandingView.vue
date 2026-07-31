<template>
  <iframe
    class="home-iframe"
    src="/home/index.html"
    title="ClawJob"
    loading="eager"
  />
</template>

<script setup lang="ts">
/** 原版 clawjob-website（React）完整嵌入，保留动效与视觉。构建：npm run build → sync-website-home */
</script>

<style scoped>
.home-iframe {
  display: block;
  width: 100%;
  flex: 1;
  min-height: 100dvh;
  height: 100dvh;
  border: 0;
  margin: 0;
  padding: 0;
  background: #0a0a0b;
}
</style>
