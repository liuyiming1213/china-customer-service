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
const currentStage = ref('idle')
const stageMessage = ref('等待输入玩家来信')
const tokenCount = ref(0)
const stages = [
  { key: 'received', label: '接收来信' },
  { key: 'retrieving', label: '召回案例' },
  { key: 'generating', label: '生成回复' },
  { key: 'validating', label: '风险校验' }
]

async function* consumeSseStream(response) {
  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''
  while (true) {
    const { value, done } = await reader.read()
    buffer += decoder.decode(value || new Uint8Array(), { stream: !done })
    const frames = buffer.split('\n\n')
    buffer = frames.pop() || ''
    for (const frame of frames) {
      const eventLine = frame.split('\n').find((line) => line.startsWith('event:'))
      const dataLine = frame.split('\n').find((line) => line.startsWith('data:'))
      if (eventLine && dataLine) yield { event: eventLine.replace('event:', '').trim(), data: JSON.parse(dataLine.replace('data:', '').trim()) }
    }
    if (done) break
  }
}

async function analyzeTicket() {
  if (!message.value.trim()) return
  loading.value = true
  error.value = ''
  result.value = null
  currentStage.value = 'received'
  stageMessage.value = '正在连接客服魔法工坊……'
  tokenCount.value = 0
  try {
    const response = await fetch('/api/tickets/analyze/stream', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message: message.value, thread_id: threadId.value || null, platform: platform.value || null, app_version: appVersion.value || null })
    })
    if (!response.ok) throw new Error(await response.text())
    for await (const packet of consumeSseStream(response)) {
      if (packet.event === 'stage') { currentStage.value = packet.data.stage; stageMessage.value = packet.data.message }
      else if (packet.event === 'token') tokenCount.value = packet.data.count
      else if (packet.event === 'result') result.value = packet.data
      else if (packet.event === 'error') throw new Error(packet.data.message)
    }
  } catch (reason) { error.value = reason.message } finally { loading.value = false }
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
      <div><p class="eyebrow">✦ OTAKU SUPPORT LAB ✦</p><h1>日本游戏客服<span>魔法工坊</span></h1><p class="subtitle">让每一封日语来信，都变成可追踪、可审核的中文行动建议。</p></div>
      <div class="mascot-card"><div class="mascot">◕‿◕</div><div><strong>小樱助手</strong><small>安全审核模式 ON</small></div></div>
    </header>
    <section class="knowledge-strip"><span>知识库同步状态</span><template v-if="knowledgeStats"><b>案例 {{ knowledgeStats.support_cases }}</b><b>政策 {{ knowledgeStats.policies }}</b><b>术语 {{ knowledgeStats.terminology }}</b></template><span v-else>正在读取……</span></section>
    <section class="workspace-grid">
      <section class="panel input-panel">
        <div class="panel-heading"><div><p class="section-label">INCOMING MESSAGE</p><h2>输入玩家来信</h2></div><span class="status-dot">● 人工审核模式</span></div>
        <textarea v-model="message" placeholder="粘贴日本玩家来信……" rows="13" />
        <div class="field-grid"><label>线程 ID<input v-model="threadId" placeholder="可选" /></label><label>平台<input v-model="platform" placeholder="iOS / Android" /></label><label>应用版本<input v-model="appVersion" placeholder="例如 1.1.4" /></label></div>
        <button class="primary-button" :disabled="loading || !message.trim()" @click="analyzeTicket">{{ loading ? '魔法施放中……' : '✦ 分析并生成回复' }}</button>
        <div v-if="loading" class="stream-status"><div class="stage-track"><span v-for="stage in stages" :key="stage.key" :class="{ active: currentStage === stage.key, passed: stages.findIndex((item) => item.key === currentStage) > stages.findIndex((item) => item.key === stage.key) }">{{ stage.label }}</span></div><p>{{ stageMessage }} <small v-if="tokenCount">· 已接收 {{ tokenCount }} 个片段</small></p></div>
        <p v-if="error" class="error-message">{{ error }}</p>
      </section>
      <section class="panel result-panel">
        <div class="panel-heading"><div><p class="section-label">ASSISTANT OUTPUT</p><h2>处理结果</h2></div><span v-if="result" class="risk-badge" :class="`risk-${result.risk_level}`">{{ result.risk_level }}</span></div>
        <div v-if="!result" class="empty-state"><div class="empty-sparkle">✧</div><p>提交一封玩家来信<br>召唤回复结果</p></div>
        <div v-else class="result-content"><div class="summary-row"><strong>问题意图</strong><span>{{ result.intent }}</span></div><article><h3>中文处理建议</h3><p>{{ result.chinese_guidance }}</p></article><article><h3>日语客服回复草稿</h3><p class="japanese-text">{{ result.japanese_reply }}</p></article><article v-if="result.missing_information.length"><h3>需要补充的信息</h3><ul><li v-for="item in result.missing_information" :key="item">{{ item }}</li></ul></article><article v-if="result.quality_warnings.length"><h3>质量提醒</h3><ul class="warning-list"><li v-for="item in result.quality_warnings" :key="item">{{ item }}</li></ul></article><article><h3>检索案例</h3><div v-for="caseItem in result.retrieved_cases" :key="caseItem.case_id" class="case-card"><div><strong>{{ caseItem.case_id }}</strong><span>重排分数 {{ caseItem.rerank_score?.toFixed(3) }}</span></div><p>{{ caseItem.document.slice(0, 260) }}{{ caseItem.document.length > 260 ? '……' : '' }}</p></div></article></div>
      </section>
    </section>
  </main>
</template>
