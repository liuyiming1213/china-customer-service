<script setup>
import { ref } from 'vue'

const message = ref('')
const threadId = ref('')
const platform = ref('')
const appVersion = ref('')
const result = ref(null)
const loading = ref(false)
const error = ref('')
const knowledgeStats = ref(null)

async function analyzeTicket() {
  if (!message.value.trim()) return
  loading.value = true
  error.value = ''
  result.value = null
  try {
    const response = await fetch('/api/tickets/analyze', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        message: message.value,
        thread_id: threadId.value || null,
        platform: platform.value || null,
        app_version: appVersion.value || null
      })
    })
    if (!response.ok) throw new Error(await response.text())
    result.value = await response.json()
  } catch (reason) {
    error.value = reason.message
  } finally {
    loading.value = false
  }
}

async function loadKnowledgeStats() {
  const response = await fetch('/api/knowledge/stats')
  if (response.ok) knowledgeStats.value = await response.json()
}

loadKnowledgeStats()
</script>

<template>
  <main class="page-shell">
    <header class="hero">
      <div>
        <p class="eyebrow">CUSTOMER SERVICE AI</p>
        <h1>日本游戏客服智能工作台</h1>
        <p class="subtitle">基于历史案例检索，生成中文处理建议和日语回复草稿。</p>
      </div>
      <div v-if="knowledgeStats" class="stats-card">
        <span>案例 {{ knowledgeStats.support_cases }}</span>
        <span>政策 {{ knowledgeStats.policies }}</span>
        <span>术语 {{ knowledgeStats.terminology }}</span>
      </div>
    </header>

    <section class="workspace-grid">
      <section class="panel input-panel">
        <div class="panel-heading">
          <div>
            <p class="section-label">INCOMING MESSAGE</p>
            <h2>输入玩家来信</h2>
          </div>
          <span class="status-dot">人工审核模式</span>
        </div>
        <textarea v-model="message" placeholder="粘贴日本玩家来信……" rows="13" />
        <div class="field-grid">
          <label>线程 ID<input v-model="threadId" placeholder="可选" /></label>
          <label>平台<input v-model="platform" placeholder="iOS / Android" /></label>
          <label>应用版本<input v-model="appVersion" placeholder="例如 1.1.4" /></label>
        </div>
        <button class="primary-button" :disabled="loading || !message.trim()" @click="analyzeTicket">
          {{ loading ? '分析中……' : '分析并生成回复' }}
        </button>
        <p v-if="error" class="error-message">{{ error }}</p>
      </section>

      <section class="panel result-panel">
        <div class="panel-heading">
          <div>
            <p class="section-label">ASSISTANT OUTPUT</p>
            <h2>处理结果</h2>
          </div>
          <span v-if="result" class="risk-badge" :class="`risk-${result.risk_level}`">{{ result.risk_level }}</span>
        </div>
        <div v-if="!result" class="empty-state">提交一封玩家来信后，结果会显示在这里。</div>
        <div v-else class="result-content">
          <div class="summary-row"><strong>问题意图</strong><span>{{ result.intent }}</span></div>
          <article><h3>中文处理建议</h3><p>{{ result.chinese_guidance }}</p></article>
          <article><h3>日语客服回复草稿</h3><p class="japanese-text">{{ result.japanese_reply }}</p></article>
          <article v-if="result.missing_information.length"><h3>需要补充的信息</h3><ul><li v-for="item in result.missing_information" :key="item">{{ item }}</li></ul></article>
          <article v-if="result.quality_warnings.length"><h3>质量提醒</h3><ul class="warning-list"><li v-for="item in result.quality_warnings" :key="item">{{ item }}</li></ul></article>
          <article><h3>检索案例</h3><div v-for="caseItem in result.retrieved_cases" :key="caseItem.case_id" class="case-card"><div><strong>{{ caseItem.case_id }}</strong><span>重排分数 {{ caseItem.rerank_score?.toFixed(3) }}</span></div><p>{{ caseItem.document.slice(0, 260) }}{{ caseItem.document.length > 260 ? '……' : '' }}</p></div></article>
        </div>
      </section>
    </section>
  </main>
</template>
