<script setup lang="ts">
// 此页面负责项目初始化阶段的运行状态展示，不承载聊天界面。
import { onMounted, ref } from 'vue'
import { apiBaseUrl, fetchHealth } from './services/health'
import type { HealthResponse } from './types/health'

const health = ref<HealthResponse | null>(null)
const loading = ref(false)
const error = ref('')
const checkedAt = ref('')

/** 检查后端连接，并让页面展示成功状态或可读错误。 */
async function checkBackend() {
  // 避免用户连续点击造成并发健康检查。
  if (loading.value) return
  loading.value = true
  health.value = null
  error.value = ''
  try {
    health.value = await fetchHealth()
  } catch (err) {
    error.value = err instanceof Error ? err.message : '无法连接后端服务'
  } finally {
    checkedAt.value = new Date().toLocaleTimeString('zh-CN')
    loading.value = false
  }
}

// 页面加载后立即探测一次，用户也可以通过按钮手动重试。
onMounted(checkBackend)
</script>

<template>
  <!-- 页面工作台：连接状态在后端不可用时提供可重试入口。 -->
  <div class="workspace">
    <header class="topbar">
      <a class="brand" href="/"><span class="brand-mark">e</span> 电商智能客服</a>
      <span class="phase-badge">阶段 01 / 项目初始化</span>
    </header>
    <main>
      <section class="intro">
        <p class="eyebrow">CUSTOMER SERVICE WORKSPACE</p>
        <h1>从连接开始，<br />构建智能服务。</h1>
        <p class="description">欢迎来到电商智能客服项目工作台。先确认运行环境，<br class="desktop-break" />再一步步接入业务数据、知识库与 Agent 能力。</p>
      </section>
      <section class="connection-card" aria-labelledby="connection-title">
        <div class="card-heading"><h2 id="connection-title">服务连接</h2><span class="card-label">LIVE STATUS</span></div>
        <div class="connection-content">
          <div class="status-block" aria-live="polite">
            <span class="status-dot" :class="{ online: health, offline: error }"></span>
            <div>
              <h3>{{ loading ? '正在检查后端服务…' : health ? '后端服务已连接' : '后端服务未连接' }}</h3>
              <p v-if="health">{{ health.service }} · v{{ health.version }}</p>
              <p v-else-if="error">{{ error }} 请检查后端启动状态及 API 地址。</p>
              <p v-else>正在准备连接</p>
            </div>
          </div>
          <button :disabled="loading" @click="checkBackend">{{ loading ? '检查中…' : '重新检查' }} <span aria-hidden="true">↗</span></button>
        </div>
        <div class="connection-meta"><code>{{ apiBaseUrl }}/health</code><span v-if="checkedAt">上次检查 {{ checkedAt }}</span></div>
      </section>
      <!-- 仅展示分阶段建设进度，不代表这些后续功能已经实现。 -->
      <section class="milestones" aria-labelledby="milestone-title">
        <div class="section-heading"><h2 id="milestone-title">构建进度</h2><span>每一阶段，独立验证</span></div>
        <div class="milestone-grid">
          <article class="milestone current"><span class="step">01</span><span class="tag active">当前阶段</span><h3>基础运行环境</h3><p>Vue 首页、FastAPI 接口与服务健康检查。</p></article>
          <article class="milestone"><span class="step">02</span><span class="tag">待开始</span><h3>数据库与业务数据</h3><p>准备用户、商品和订单等基础业务数据。</p></article>
          <article class="milestone"><span class="step">03+</span><span class="tag">后续阶段</span><h3>智能客服能力</h3><p>逐步实现对话、知识检索和工具调用。</p></article>
        </div>
      </section>
    </main>
    <footer><span>电商智能客服 · 学习与作品展示</span><span>Vue 3 + TypeScript / FastAPI</span></footer>
  </div>
</template>
