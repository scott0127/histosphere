<template>
  <div class="historical-admin admin-workspace monitor-page">
    <a href="#monitor-main" class="monitor-skip-link">前往施測內容</a>
    <header class="admin-topbar monitor-topbar">
      <div class="monitor-topbar-inner">
        <NuxtLink to="/admin" class="monitor-back"><Icon name="mdi:arrow-left" class="h-4 w-4" />研究管理</NuxtLink>
        <span class="monitor-brand">Histosphere <span>施測監測</span></span>
        <button v-if="snapshot" type="button" class="monitor-text-button" @click="logout">退出管理員</button>
      </div>
    </header>

    <main id="monitor-main" class="monitor-main">
      <section v-if="!snapshot" class="monitor-login">
        <p class="monitor-eyebrow">研究者工作區</p>
        <h1>施測監測</h1>
        <p>登入管理員後，即可查看當次活動並核對作答。</p>
        <form @submit.prevent="connect" class="monitor-login-form">
          <label for="monitor-admin-key">管理員密碼</label>
          <input id="monitor-admin-key" v-model="adminKey" type="password" autocomplete="current-password" class="admin-field" :disabled="loading" />
          <button class="admin-button-primary monitor-button" :disabled="loading || !sessionId">{{ loading ? '正在載入…' : '開啟施測監測' }}</button>
        </form>
        <p v-if="!sessionId" class="monitor-muted">請先從研究管理選擇一筆活動紀錄。</p>
        <p v-if="error" role="alert" class="monitor-error">{{ error }}</p>
      </section>

      <template v-else>
        <section class="monitor-session-header">
          <div>
            <p class="monitor-eyebrow">當次施測</p>
            <h1>{{ snapshot.participant_code }} <span>{{ snapshot.event.canonical_name }}</span></h1>
            <p class="monitor-session-meta">{{ conditionText }}<span v-if="snapshot.session.is_admin_test">管理員測試</span></p>
          </div>
          <div class="monitor-sync">
            <span class="monitor-connection" :class="{ 'is-connected': connected }">{{ connected ? '同步已連線' : '同步未連線，正在重連' }}</span>
            <span>更新於 {{ shortTime(lastSyncedAt) }}</span>
            <button type="button" class="monitor-text-button" @click="refresh"><Icon name="mdi:refresh" class="h-4 w-4" />重新同步</button>
          </div>
        </section>

        <ol class="monitor-stages" aria-label="施測階段">
          <li v-for="(label, index) in stages" :key="label" :class="{ 'is-current': phase.step === index, 'is-done': phase.step > index }" :aria-current="phase.step === index ? 'step' : undefined">
            <span class="monitor-stage-number">{{ String(index + 1).padStart(2, '0') }}</span><span>{{ phase.id === 'complete' && index === 3 ? '完成' : label }}</span>
          </li>
        </ol>

        <p v-if="error" role="alert" class="monitor-error">{{ error }}</p>
        <p v-if="notice" role="status" class="monitor-notice">{{ notice }}</p>
        <div v-if="conflict" role="alert" class="monitor-error monitor-conflict">
          <p>其他分頁已更新審核結果。目前修改仍保留，請比對後重新載入已保存的版本。</p>
          <button type="button" class="monitor-text-button" @click="showReloadConfirm = true">重新載入審核</button>
        </div>

        <section v-if="countdown && ['task', 'chat', 'posttest', 'complete', 'archived'].includes(phase.id)" class="monitor-countdown" :class="`is-${countdown.state}`" aria-labelledby="monitor-countdown-title">
          <p v-if="countdown.durationLabel" class="monitor-eyebrow">{{ countdown.durationLabel }}</p>
          <h2 id="monitor-countdown-title">{{ countdown.title }}</h2>
          <p class="monitor-countdown-value" role="timer" aria-live="off" :aria-label="`${countdown.title} ${countdown.display}`">{{ countdown.display }}</p>
          <p v-if="countdown.state === 'expired'" class="monitor-countdown-expired" role="status">參考時間已到，可提醒受測者。</p>
          <p v-if="countdown.detail" class="monitor-countdown-detail">{{ countdown.detail }}</p>
        </section>

        <section v-else-if="['judging', 'preparing', 'ready', 'failed'].includes(phase.id)" class="monitor-status-panel" aria-live="polite">
          <span class="monitor-status-icon"><Icon :name="phase.id === 'failed' ? 'mdi:information-outline' : 'mdi:clock-time-eight-outline'" /></span>
          <p class="monitor-eyebrow">{{ snapshot.participant_code }}</p>
          <h2>{{ phase.label }}</h2>
          <p>{{ phaseDescription }}</p>
          <button v-if="phase.id === 'failed'" type="button" class="admin-button-primary monitor-button" :disabled="saving" @click="retry">{{ saving ? '重新處理中…' : '重試處理' }}</button>
        </section>

        <section v-if="phase.id === 'review' && selectedRow && selectedDraft" class="monitor-review-area">
          <header class="monitor-review-heading">
            <div><h2>逐題核對</h2><p>核對原始作答後，確認每一題。</p></div>
            <p class="monitor-reviewed-count">已核對 <strong>{{ reviewedCount }}</strong>／{{ questions.length }}</p>
          </header>
          <nav class="monitor-question-nav" aria-label="審核題目">
            <button v-for="(row, index) in questions" :key="row.question.id" type="button" :aria-pressed="selectedQuestionId === row.question.id"
              :class="{ 'is-selected': selectedQuestionId === row.question.id, 'is-reviewed': draftFor(row.question.id)?.reviewed }"
              @click="selectedQuestionId = row.question.id">
              <span>第 {{ index + 1 }} 題</span><Icon v-if="draftFor(row.question.id)?.reviewed" name="mdi:check" class="h-3.5 w-3.5" /><span v-else class="monitor-question-dot" />
            </button>
          </nav>
          <div class="monitor-review-grid">
            <aside class="monitor-reading" aria-label="原始閱讀材料">
              <div class="monitor-panel-title"><h3>閱讀材料</h3><span>作答當時版本</span></div>
              <div class="monitor-reading-body">
                <p v-if="readingIntroduction" class="monitor-prose">{{ readingIntroduction }}</p>
                <TaskStudentMaterials :materials="frozenTask?.evaluation_payload.materials || []" compact />
                <p v-if="!frozenTask?.evaluation_payload.materials?.length" class="monitor-muted">此題組沒有獨立閱讀材料，請核對題目內文。</p>
                <details class="monitor-full-text"><summary>完整題本文</summary><p class="monitor-prose">{{ frozenTask?.error_elicitation_task_full_text?.replace(/\{\{\s*blank:[^}]+\}\}/g, '＿＿＿') }}</p></details>
              </div>
            </aside>
            <ReviewQuestionPanel :key="selectedRow.question.id" :row="selectedRow" :draft="selectedDraft" :index="selectedIndex" :disabled="saving || conflict"
              @update="updateQuestion(selectedRow.question.id, $event)" @save="saveQuestion(selectedRow.question.id, $event)" />
          </div>
          <footer class="monitor-approval-bar">
            <div><strong>已核對 {{ reviewedCount }}／{{ questions.length }} 題</strong><p>{{ dirty ? '有尚未保存的修改' : '確認前，受測者會停留在等待畫面。' }}</p></div>
            <button type="button" class="admin-button-primary monitor-button" :disabled="!canApprove" @click="approve">{{ saving ? '正在保存…' : '確認結果並開始互動' }}</button>
          </footer>
        </section>

      </template>
    </main>
    <ConfirmActionModal :show="showReloadConfirm" title="重新載入審核" message="這會捨棄此頁尚未保存的修改，載入伺服器上最新的審核結果。" confirm-label="重新載入" cancel-label="保留修改" @confirm="reloadDrafts" @cancel="showReloadConfirm = false" />
    <ConfirmActionModal :show="Boolean(pendingNavigation)" title="修改尚未保存" message="離開會捨棄此頁尚未保存的審核修改。" confirm-label="離開" cancel-label="繼續核對" @confirm="confirmNavigation" @cancel="cancelNavigation" />
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue';
import ReviewQuestionPanel from '~/components/admin/monitor/ReviewQuestionPanel.vue';
import TaskStudentMaterials from '~/components/task-student/TaskStudentMaterials.vue';
import ConfirmActionModal from '~/components/modals/ConfirmActionModal.vue';
import { useAdminMonitor } from '~/composables/useAdminMonitor';
import { buildTaskQuestionLayout } from '~/composables/useStudentTask';
import { monitorPhase, reviewTask } from '~/utils/taskReview';
import { monitorCountdown } from '~/utils/monitorTiming';
import { conditionModeLabel } from '~/utils/adminWorkspaceState';
import type { RouteLocationRaw } from 'vue-router';
import '~/assets/css/admin-monitor.css';

useHead({ title: '施測監測 · Histosphere' });
const route = useRoute();
const sessionId = computed(() => typeof route.query.session === 'string' ? route.query.session : '');
const { adminKey, snapshot, drafts, questions, editable, loading, saving, connected, error, notice, lastSyncedAt, serverClockOffsetMs,
  dirty, conflict, reviewedCount, canApprove, connect, refresh, updateQuestion, saveQuestion, approve, retry, logout, restoreDrafts } = useAdminMonitor(sessionId);
const selectedQuestionId = ref('');
const showReloadConfirm = ref(false);
const now = ref(Date.now());
let timer: ReturnType<typeof setInterval> | undefined;
const stages = ['作答', '人工核對', 'AI 互動', '後續評量'];
const phase = computed(() => snapshot.value ? monitorPhase(snapshot.value) : { id: 'task', label: '', step: 0 });
const conditionText = computed(() => snapshot.value?.condition ? conditionModeLabel(snapshot.value.condition) : snapshot.value?.session.condition_key_snapshot || '');
const frozenTask = computed(() => snapshot.value ? reviewTask(snapshot.value) : null);
const readingIntroduction = computed(() => frozenTask.value ? buildTaskQuestionLayout(frozenTask.value).introduction : '');
const selectedIndex = computed(() => Math.max(0, questions.value.findIndex(row => row.question.id === selectedQuestionId.value)));
const selectedRow = computed(() => questions.value[selectedIndex.value]);
const draftFor = (id: string) => drafts.value.find(item => item.question_id === id);
const selectedDraft = computed(() => selectedRow.value ? draftFor(selectedRow.value.question.id) : undefined);
const countdown = computed(() => snapshot.value ? monitorCountdown(snapshot.value, now.value + serverClockOffsetMs.value) : null);
const phaseDescription = computed(() => {
  if (phase.value.id === 'failed') return snapshot.value?.attempt?.pipeline_error?.message || snapshot.value?.attempt?.pipeline_error?.detail || '系統未完成處理，受測者會繼續等待。';
  if (phase.value.id === 'ready') return 'AI 開場已準備完成；受測者銜接互動後才開始計時。';
  if (phase.value.id === 'preparing') return '人工判定已確認，系統正依最終結果準備互動內容。';
  return '系統正在整理初判，完成後即可逐題核對。';
});
const shortTime = (value?: string | null) => value ? new Intl.DateTimeFormat('zh-TW', { hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false }).format(new Date(value)) : '—';
const reloadDrafts = () => { restoreDrafts(); showReloadConfirm.value = false; };
watch(questions, rows => {
  if (!rows.some(row => row.question.id === selectedQuestionId.value)) selectedQuestionId.value = rows[0]?.question.id || '';
});
onMounted(() => { timer = setInterval(() => { now.value = Date.now(); }, 1000); });
onBeforeUnmount(() => { clearInterval(timer); navigationDecision?.(false); });

const pendingNavigation = ref<RouteLocationRaw | null>(null);
let navigationDecision: ((value: boolean) => void) | null = null;
onBeforeRouteLeave(to => {
  if (!dirty.value || !editable.value) return true;
  pendingNavigation.value = to.fullPath;
  return new Promise<boolean>(resolve => { navigationDecision = resolve; });
});
const confirmNavigation = () => { pendingNavigation.value = null; navigationDecision?.(true); navigationDecision = null; };
const cancelNavigation = () => { pendingNavigation.value = null; navigationDecision?.(false); navigationDecision = null; };
</script>
