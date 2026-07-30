<template>
  <!--
    Admin 是第一版研究用簡易後台：
    使用 x-admin-key 保護，用來調整 condition 設定、task 與 persona prompt_profile。
    目前不是正式 Supabase Auth/RLS 後台，請勿把它當成 production 權限模型。
  -->
  <div class="historical-admin min-h-screen font-sans">
    <header class="admin-topbar">
      <div class="mx-auto flex max-w-7xl items-center justify-between px-5 py-3">
        <NuxtLink to="/" class="flex items-center gap-3">
          <span class="admin-back-button">
            <Icon name="mdi:arrow-left" class="h-5 w-5" />
          </span>
          <span>
            <span class="admin-brand block font-serif text-lg font-bold tracking-[0.08em]">Histosphere</span>
            <span class="admin-caption block text-xs font-semibold tracking-[0.08em]">研究者 / 老師操作端</span>
          </span>
        </NuxtLink>
        <div class="flex items-center gap-2">
          <button
            v-if="snapshot"
            type="button"
            class="admin-button-secondary inline-flex min-h-10 items-center justify-center gap-2 px-4 text-xs font-bold"
            @click="enterAdminTestMode"
          >
            <Icon name="mdi:eye" class="h-4 w-4" />
            受測者測試
          </button>
          <button
            type="button"
            class="admin-button-secondary inline-flex min-h-10 items-center justify-center gap-2 px-4 text-xs font-bold"
            @click="leaveAdminMode"
          >
            <Icon name="mdi:logout" class="h-4 w-4" />
            退出
          </button>
          <span class="admin-badge">Admin mode</span>
        </div>
      </div>
    </header>

    <main class="mx-auto max-w-7xl space-y-6 px-5 py-10 md:py-12">
      <section class="admin-hero">
        <div class="p-5 md:p-6">
          <div class="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
            <div>
              <p class="admin-kicker">Admin access</p>
              <h1 class="admin-heading mt-1 font-serif text-3xl font-bold">
                {{ snapshot ? '管理後台' : '需要 admin key' }}
              </h1>
              <p class="admin-copy mt-2 max-w-2xl text-sm font-semibold leading-7">
                {{ snapshot ? '先選擇歷史事件，再進入該事件的 task、事件資料與人物設定。' : '驗證成功後才會載入後台資料與管理工具。' }}
              </p>
              <p class="admin-caption mt-2 text-xs font-bold">
                共用研究者密碼驗證；關閉分頁或退出後會自動清除。
              </p>
            </div>
            <div class="flex w-full flex-col gap-2 sm:flex-row lg:w-[520px]">
              <input
                id="admin-key"
                v-model="adminKey"
                type="password"
                class="admin-field min-h-12 min-w-0 flex-1 px-4 text-base font-semibold"
                placeholder="管理金鑰"
              />
              <button
                class="admin-button-primary inline-flex min-h-12 items-center justify-center gap-2 px-5 text-sm font-bold"
                @click="handleLoadSnapshot"
              >
                <Icon name="mdi:database-search" class="h-5 w-5" />
                {{ snapshot ? '重新載入' : '載入資料' }}
              </button>
            </div>
          </div>
          <p v-if="error" class="admin-error mt-4 whitespace-pre-line px-3 py-2 text-sm font-semibold">
            {{ error }}
          </p>
        </div>
      </section>

      <section v-if="snapshot" class="space-y-5">
        <section class="admin-panel">
          <button class="admin-accordion-header" type="button" @click="toggleSection('participants')">
            <span>
              <span class="admin-kicker">Research dashboard</span>
              <span class="admin-accordion-title">受測者管理</span>
            </span>
            <span class="admin-accordion-meta">
              {{ participantRows.length }} 位受測者
              <Icon :name="openSections.participants ? 'mdi:chevron-down' : 'mdi:arrow-right'" class="h-5 w-5" />
            </span>
          </button>

          <div v-show="openSections.participants" class="admin-accordion-body">
            <p v-if="authUsersError" class="admin-error mb-4 whitespace-pre-line px-3 py-2 text-sm font-semibold">
              {{ authUsersError }}
            </p>
            <AdminParticipantDashboard
              :rows="participantRows"
              :auth-users="authUsers"
              :creating-participant="creatingParticipant"
              :changing-participant-status-id="changingParticipantStatusId"
              :saving-participant-id="savingParticipantId"
              :updating-timer-session-id="updatingTimerSessionId"
              :restarting-session-id="restartingSessionId"
              @create="createParticipant"
              @archive="(participant) => setParticipantArchived(participant, true)"
              @restore="(participant) => setParticipantArchived(participant, false)"
              @save="saveParticipant"
              @reset-timer="resetSessionTimer"
              @restart-session="restartSession"
            />
          </div>
        </section>

        <section class="admin-panel">
          <button class="admin-accordion-header" type="button" @click="toggleSection('logs')">
            <span>
              <span class="admin-kicker">Audit trail</span>
              <span class="admin-accordion-title">研究操作紀錄</span>
            </span>
            <span class="admin-accordion-meta">
              最近 {{ snapshot.research_logs.length }} 筆
              <Icon :name="openSections.logs ? 'mdi:chevron-down' : 'mdi:arrow-right'" class="h-5 w-5" />
            </span>
          </button>

          <div v-show="openSections.logs" class="admin-accordion-body">
            <AdminResearchLogPanel
              :events="snapshot.events"
              :logs="snapshot.research_logs"
            />
          </div>
        </section>

        <section v-if="!selectedEvent" class="admin-panel">
          <div class="admin-accordion-header">
            <span>
              <span class="admin-kicker">Admin workspace</span>
              <span class="admin-accordion-title">選擇要管理的歷史事件</span>
            </span>
            <span class="admin-accordion-meta">
              {{ snapshot.events.length }} 個事件
            </span>
          </div>

          <div class="admin-accordion-body">
            <div class="grid gap-4">
              <article
                v-for="event in snapshot.events"
                :key="event.id"
                class="admin-panel-inner p-5"
              >
                <div class="grid gap-4 lg:grid-cols-[minmax(0,1fr)_260px_140px] lg:items-center">
                  <div>
                    <div class="flex items-center gap-2">
                      <p class="admin-kicker">歷史事件</p>
                      <span v-if="event.archived_at" class="admin-badge">已封存</span>
                    </div>
                    <h2 class="admin-heading mt-1 font-serif text-2xl font-bold">{{ event.canonical_name }}</h2>
                    <p class="admin-copy mt-2 line-clamp-2 max-w-4xl text-sm font-semibold leading-7">
                      {{ event.description || event.context || '尚未建立事件描述。' }}
                    </p>
                  </div>

                  <div class="grid gap-2 text-sm">
                    <div class="admin-info-row">
                      <span>年代</span>
                      <strong>{{ eventYearRange(event) }}</strong>
                    </div>
                    <div class="admin-info-row">
                      <span>Task</span>
                      <strong>{{ event.latest_task ? `${taskQuestionCount(event.latest_task)} 題` : '未建立' }}</strong>
                    </div>
                    <div class="admin-info-row">
                      <span>人物</span>
                      <strong>{{ event.personas.length }} 人</strong>
                    </div>
                  </div>

                  <div class="grid gap-2">
                    <button
                      class="admin-button-primary inline-flex min-h-11 items-center justify-center px-4 text-sm font-bold"
                      type="button"
                      @click="selectEvent(event.id)"
                    >
                      管理
                    </button>
                    <button
                      class="admin-button-secondary inline-flex min-h-10 items-center justify-center px-4 text-xs font-bold"
                      type="button"
                      @click="setEventArchived(event, !event.archived_at)"
                    >
                      {{ event.archived_at ? '恢復事件' : '封存事件' }}
                    </button>
                  </div>
                </div>
              </article>

              <div v-if="!snapshot.events.length" class="admin-empty-state p-6">
                目前沒有歷史事件。請先在首頁建立事件素材。
              </div>
            </div>
          </div>
        </section>

        <template v-else>
        <section class="admin-panel">
          <div class="admin-accordion-header flex-col items-stretch gap-4 md:flex-row md:items-center">
            <span>
              <span class="admin-kicker">Selected event</span>
              <span class="admin-accordion-title">{{ selectedEvent.canonical_name }}</span>
            </span>
            <div class="flex flex-wrap items-center gap-2">
              <span class="admin-accordion-meta">
                {{ eventYearRange(selectedEvent) }}
              </span>
              <button class="admin-button-secondary px-3 py-2 text-xs font-bold" type="button" @click="selectedEventId = null">
                返回事件列表
              </button>
            </div>
          </div>
        </section>

        <section class="admin-panel">
          <button class="admin-accordion-header" type="button" @click="toggleSection('tasks')">
            <span>
              <span class="admin-kicker">Section 01</span>
              <span class="admin-accordion-title">管理 task</span>
            </span>
            <span class="admin-accordion-meta">
              {{ selectedEvent.latest_task ? `${taskQuestionCount(selectedEvent.latest_task)} 題` : '未建立 task' }}
              <Icon :name="openSections.tasks ? 'mdi:chevron-down' : 'mdi:arrow-right'" class="h-5 w-5" />
            </span>
          </button>

          <div v-show="openSections.tasks" class="admin-accordion-body">
            <div>
              <article v-if="selectedEvent.latest_task" class="admin-panel-inner p-5 md:p-6">
                <div class="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
                  <div>
                    <p class="admin-kicker">Task source</p>
                    <h2 class="admin-heading mt-1 font-serif text-2xl font-bold">{{ selectedEvent.canonical_name }}</h2>
                    <p class="admin-copy mt-2 max-w-3xl text-sm font-semibold leading-7">
                      {{ selectedEvent.latest_task.title || '尚未命名的任務' }}
                    </p>
                  </div>
                  <span class="admin-badge">{{ taskQuestionCount(selectedEvent.latest_task) }} 題</span>
                </div>

                <TaskControlEditor
                  :evaluation-json="taskJson[selectedEvent.latest_task.id] || '{}'"
                  class="mt-5"
                  :dirty="isTaskDirty(selectedEvent.latest_task)"
                  :saving="savingTaskId === selectedEvent.latest_task.id"
                  :task="selectedEvent.latest_task"
                  @update:evaluation-json="taskJson[selectedEvent.latest_task.id] = $event"
                  @save="saveTask(selectedEvent.latest_task)"
                />
              </article>

              <div v-else class="admin-empty-state p-5">
                這個歷史事件目前沒有可編輯的 task。
              </div>
            </div>
          </div>
        </section>

        <section class="admin-panel">
          <button class="admin-accordion-header" type="button" @click="toggleSection('events')">
            <span>
              <span class="admin-kicker">Section 02</span>
              <span class="admin-accordion-title">管理歷史事件資料</span>
            </span>
            <span class="admin-accordion-meta">
              基礎素材
              <Icon :name="openSections.events ? 'mdi:chevron-down' : 'mdi:arrow-right'" class="h-5 w-5" />
            </span>
          </button>

          <div v-show="openSections.events" class="admin-accordion-body">
            <div class="grid gap-4">
              <article class="admin-panel-inner p-5">
                  <div class="grid gap-4 lg:grid-cols-[minmax(0,1fr)_260px]">
                    <div>
                      <p class="admin-kicker">歷史事件</p>
                      <h2 class="admin-heading mt-1 font-serif text-2xl font-bold">{{ selectedEvent.canonical_name }}</h2>
                      <p class="admin-copy mt-3 text-sm font-semibold leading-7">{{ selectedEvent.description || selectedEvent.context || '尚未建立事件描述。' }}</p>
                    </div>
                    <div class="grid gap-2 text-sm">
                      <div class="admin-info-row">
                        <span>年代</span>
                        <strong>{{ eventYearRange(selectedEvent) }}</strong>
                      </div>
                      <div class="admin-info-row">
                        <span>人物</span>
                        <strong>{{ selectedEvent.personas.length }}</strong>
                      </div>
                      <div class="admin-info-row">
                        <span>Task</span>
                        <strong>{{ selectedEvent.latest_task ? '已建立' : '未建立' }}</strong>
                      </div>
                    </div>
                  </div>

                  <div class="mt-4 grid gap-3 md:grid-cols-2">
                    <label class="block">
                      <span class="admin-label">事件名稱</span>
                      <input v-model="selectedEvent.canonical_name" class="admin-field mt-1 w-full px-3 py-2 text-sm font-bold" />
                    </label>
                    <label class="block">
                      <span class="admin-label">事件期間</span>
                      <input :value="eventYearRange(selectedEvent)" class="admin-field mt-1 w-full px-3 py-2 text-sm" disabled />
                    </label>
                    <label class="block md:col-span-2">
                      <span class="admin-label">事件描述</span>
                      <textarea v-model="selectedEvent.description" rows="4" class="admin-textarea mt-1 w-full px-3 py-2 text-sm leading-6" />
                    </label>
                    <label class="block md:col-span-2">
                      <span class="admin-label">背景脈絡</span>
                      <textarea v-model="selectedEvent.context" rows="4" class="admin-textarea mt-1 w-full px-3 py-2 text-sm leading-6" />
                    </label>
                  </div>

                  <div class="mt-4 flex justify-end">
                    <button class="admin-button-secondary px-3 py-2 text-xs font-bold" type="button" @click="saveEvent(selectedEvent)">
                      儲存事件資料
                    </button>
                  </div>
                </article>
            </div>
          </div>
        </section>

        <section class="admin-panel">
          <button class="admin-accordion-header" type="button" @click="toggleSection('personas')">
            <span>
              <span class="admin-kicker">Section 03</span>
              <span class="admin-accordion-title">管理歷史人物與 prompt</span>
            </span>
            <span class="admin-accordion-meta">
              {{ selectedEvent.personas.length }} 個人物
              <Icon :name="openSections.personas ? 'mdi:chevron-down' : 'mdi:arrow-right'" class="h-5 w-5" />
            </span>
          </button>

          <div v-show="openSections.personas" class="admin-accordion-body">
            <div class="grid gap-5 xl:grid-cols-[minmax(0,1fr)_420px]">
              <section class="space-y-4">
                <article class="admin-panel-inner p-5">
                  <div class="flex flex-col gap-2 md:flex-row md:items-start md:justify-between">
                    <div>
                      <p class="admin-kicker">歷史人物</p>
                      <h2 class="admin-heading mt-1 font-serif text-2xl font-bold">{{ selectedEvent.canonical_name }}</h2>
                      <p class="admin-caption mt-2 text-xs">同一事件最多只能啟用一位人物；封存不會刪除既有研究資料。</p>
                    </div>
                    <div class="flex items-center gap-2">
                      <span class="admin-badge">{{ selectedEvent.personas.length }} 人</span>
                      <button
                        type="button"
                        class="admin-button-secondary inline-flex min-h-10 items-center justify-center gap-2 px-3 text-xs font-bold"
                        :disabled="creatingPersona"
                        @click="createPersona(selectedEvent.id)"
                      >
                        <Icon name="mdi:account-plus-outline" class="h-4 w-4" />
                        {{ creatingPersona ? '建立中' : '新增人物' }}
                      </button>
                    </div>
                  </div>

                  <div class="mt-4 space-y-3">
                    <div v-for="persona in selectedEvent.personas" :key="persona.id" class="admin-subpanel p-4">
                      <div class="flex flex-col gap-4 md:flex-row">
                        <div class="shrink-0">
                          <img
                            v-if="persona.avatar_url"
                            :src="persona.avatar_url"
                            :alt="`${persona.name} 肖像`"
                            class="h-24 w-24 rounded-md border border-[var(--admin-border)] object-cover"
                          />
                          <div
                            v-else
                            class="flex h-24 w-24 items-center justify-center rounded-md border border-dashed border-[var(--admin-border)] bg-[var(--admin-surface-muted)] text-2xl font-bold text-[var(--admin-soft)]"
                          >
                            {{ persona.name.slice(0, 1) }}
                          </div>
                        </div>
                        <div class="min-w-0 flex-1">
                          <div class="flex items-center gap-2">
                            <input v-model="persona.name" class="admin-field min-w-0 flex-1 px-3 py-2 text-sm font-bold" />
                            <span
                              :class="[
                                'admin-badge whitespace-nowrap',
                                persona.archived_at ? 'opacity-60' : ''
                              ]"
                            >
                              {{ personaStatusLabel(persona) }}
                            </span>
                          </div>
                          <input v-model="persona.role" class="admin-field mt-2 w-full px-3 py-2 text-sm" placeholder="角色定位" />
                          <input v-model="persona.avatar_url" class="admin-field mt-2 w-full px-3 py-2 text-xs" placeholder="/images/personas/portrait.png" />
                        </div>
                      </div>
                      <textarea v-model="persona.biography" rows="3" class="admin-textarea mt-3 w-full px-3 py-2 text-sm leading-6" />
                      <label class="admin-label mt-3 block">prompt_profile JSON</label>
                      <textarea v-model="personaJson[persona.id]" rows="5" class="admin-textarea admin-code-editor mt-1 w-full px-3 py-2 font-mono text-xs leading-5" />
                      <div class="mt-3 flex flex-wrap items-center justify-end gap-2">
                        <button
                          v-if="persona.archived_at"
                          type="button"
                          class="admin-button-secondary px-3 py-2 text-xs font-bold"
                          :disabled="changingPersonaStatusId === persona.id"
                          @click="restorePersona(persona)"
                        >
                          恢復
                        </button>
                        <template v-else>
                          <button
                            type="button"
                            class="admin-button-secondary px-3 py-2 text-xs font-bold"
                            :disabled="changingPersonaStatusId === persona.id"
                            @click="setPersonaActive(persona, !persona.active)"
                          >
                            {{ persona.active ? '停用' : '啟用' }}
                          </button>
                          <button
                            type="button"
                            class="admin-button-secondary px-3 py-2 text-xs font-bold"
                            :disabled="changingPersonaStatusId === persona.id"
                            @click="confirmArchivePersona(persona)"
                          >
                            封存
                          </button>
                          <button
                            class="admin-button-primary px-3 py-2 text-xs font-bold"
                            :disabled="savingPersonaId === persona.id"
                            @click="savePersona(persona)"
                          >
                            {{ savingPersonaId === persona.id ? '儲存中' : '儲存人物' }}
                          </button>
                        </template>
                      </div>
                    </div>

                    <div v-if="!selectedEvent.personas.length" class="admin-empty-state p-5">
                      這個事件目前沒有歷史人物資料。
                    </div>
                  </div>
                </article>
              </section>

              <section class="admin-panel-inner admin-panel-muted p-5">
                <div class="flex items-start justify-between gap-4">
                  <div>
                    <p class="admin-kicker">Condition design</p>
                    <h2 class="admin-heading mt-1 font-serif text-2xl font-bold">條件設定</h2>
                  </div>
                  <span class="admin-code-badge">2x2</span>
                </div>

                <div class="mt-4 grid grid-cols-4 gap-2">
                  <button
                    v-for="condition in promptConditions"
                    :key="condition.id"
                    type="button"
                    :title="conditionModeLabel(condition)"
                    :aria-label="conditionModeLabel(condition)"
                    :class="[
                      'condition-tab px-3 py-3 text-center text-xs font-black',
                      selectedCondition?.id === condition.id
                        ? 'condition-tab-active'
                        : 'condition-tab-idle'
                    ]"
                    @click="selectedConditionId = condition.id"
                  >
                    <span class="block font-mono text-sm">{{ conditionOrdinal(condition) }}</span>
                    <span class="admin-caption mt-1 block text-[11px] font-bold">模式</span>
                  </button>
                </div>

                <div v-if="selectedCondition" class="mt-5 space-y-4">
                  <label class="block">
                    <span class="admin-label">活動名稱</span>
                    <input
                      v-model="selectedCondition.label"
                      class="admin-field mt-1 w-full px-3 py-2 text-sm font-bold"
                    />
                  </label>

                  <label class="block">
                    <span class="admin-label">研究者備註</span>
                    <textarea
                      v-model="selectedCondition.description"
                      rows="4"
                      class="admin-textarea mt-1 w-full px-3 py-2 text-sm leading-6"
                    />
                  </label>

                  <button class="admin-button-primary w-full px-3 py-3 text-xs font-bold" @click="saveCondition(selectedCondition)">
                    儲存 condition 設定
                  </button>

                  <div class="admin-subpanel p-4">
                    <div class="flex items-center justify-between gap-3">
                      <span>
                        <span class="admin-label block">後端 prompt 預覽</span>
                        <span class="admin-caption mt-1 block text-xs">只讀，來自後端 PromptService</span>
                      </span>
                      <span class="flex items-center gap-2">
                        <button
                          class="admin-button-secondary px-3 py-2 text-xs font-bold"
                          type="button"
                          :disabled="promptPreviewLoading"
                          @click="loadPromptPreview(selectedEvent, selectedCondition)"
                        >
                          {{ promptPreviewLoading ? '載入中' : '預覽' }}
                        </button>
                        <button
                          class="admin-button-primary px-3 py-2 text-xs font-bold"
                          type="button"
                          :disabled="promptDryRunLoading"
                          @click="runPromptDryRun(selectedEvent, selectedCondition)"
                        >
                          {{ promptDryRunLoading ? '推論中' : '執行測試' }}
                        </button>
                      </span>
                    </div>
                    <textarea
                      v-model="promptPreviewMessage"
                      rows="2"
                      class="admin-textarea mt-3 w-full px-3 py-2 text-xs leading-5"
                    />
                    <pre
                      v-if="promptPreview"
                      class="admin-code-editor mt-3 max-h-[360px] overflow-auto whitespace-pre-wrap rounded-md border border-[var(--admin-border)] bg-[var(--admin-panel)] p-3 text-xs leading-5"
                    >{{ promptPreview.prompt }}</pre>
                    <div v-if="promptDryRun" class="mt-3 rounded-md border border-[var(--admin-border)] bg-[var(--admin-surface)] p-3">
                      <span class="admin-label block">Dry-run 回覆（未寫入對話）</span>
                      <p class="admin-copy mt-2 whitespace-pre-wrap text-sm leading-6">{{ promptDryRun.response }}</p>
                    </div>
                  </div>
                </div>
              </section>
            </div>
          </div>
        </section>
        </template>
      </section>
    </main>
  </div>
</template>

<script setup lang="ts">
// 這個頁面刻意把 task/persona 的 JSON 欄位攤開給研究者編輯，
// 方便在實驗前快速調 persona prompt_profile 與 task evaluation_payload。
import { computed, onBeforeUnmount, onMounted, ref } from 'vue';
import type { Persona } from '~/types';
import { buildParticipantDashboardRows } from '~/utils/adminParticipantDashboard';

definePageMeta({
  layout: false,
  name: 'admin',
});

type AdminSectionKey = 'participants' | 'logs' | 'tasks' | 'events' | 'personas';

const openSections = ref<Record<AdminSectionKey, boolean>>({
  participants: true,
  logs: false,
  tasks: true,
  events: true,
  personas: true,
});

const { enterAdminMode, exitAdminMode, initAdminMode, setAdminViewMode } = useAdminMode();
const {
  adminKey,
  archivePersona,
  authUsers,
  authUsersError,
  changingParticipantStatusId,
  changingPersonaStatusId,
  createPersona,
  createParticipant,
  creatingPersona,
  creatingParticipant,
  conditionModeLabel,
  conditionOrdinal,
  error,
  eventYearRange,
  hasUnsavedTaskChanges,
  isTaskDirty,
  loadSnapshot,
  loadPromptPreview,
  personaJson,
  promptDryRun,
  promptDryRunLoading,
  promptPreview,
  promptPreviewLoading,
  promptPreviewMessage,
  promptConditions,
  resetWorkspace,
  restartSession,
  restartingSessionId,
  restorePersona,
  restoreStoredAdminKey,
  runPromptDryRun,
  saveCondition,
  saveEvent,
  setEventArchived,
  savePersona,
  savingPersonaId,
  saveParticipant,
  setParticipantArchived,
  setPersonaActive,
  saveTask,
  savingTaskId,
  resetSessionTimer,
  savingParticipantId,
  selectedCondition,
  selectedConditionId,
  selectedEvent,
  selectedEventId,
  snapshot,
  taskJson,
  taskQuestionCount,
  updatingTimerSessionId,
} = useAdminWorkspace();

const participantRows = computed(() => {
  return snapshot.value ? buildParticipantDashboardRows(snapshot.value, authUsers.value) : [];
});

const personaStatusLabel = (persona: Persona) => {
  if (persona.archived_at) return '已封存';
  return persona.active ? '使用中' : '已停用';
};

const confirmArchivePersona = async (persona: Persona) => {
  if (import.meta.client && !window.confirm(`確定封存「${persona.name}」？既有研究資料會保留。`)) return;
  await archivePersona(persona);
};

const allowRouteLeave = ref(false);
const confirmDiscardTaskDrafts = () => {
  if (!hasUnsavedTaskChanges.value || !import.meta.client) return true;
  return window.confirm('Task 尚有未儲存變更。確定要離開並放棄這些變更嗎？');
};

const handleBeforeUnload = (event: BeforeUnloadEvent) => {
  if (!hasUnsavedTaskChanges.value) return;
  event.preventDefault();
  event.returnValue = '';
};

onMounted(async () => {
  window.addEventListener('beforeunload', handleBeforeUnload);
  initAdminMode();
  restoreStoredAdminKey();
  if (adminKey.value && await loadSnapshot()) {
    enterAdminMode();
  }
});

onBeforeUnmount(() => {
  window.removeEventListener('beforeunload', handleBeforeUnload);
});

onBeforeRouteLeave(() => {
  if (allowRouteLeave.value) return true;
  return confirmDiscardTaskDrafts();
});

const handleLoadSnapshot = async () => {
  if (await loadSnapshot()) {
    enterAdminMode();
  }
};

const enterAdminTestMode = async () => {
  if (!confirmDiscardTaskDrafts()) return;
  allowRouteLeave.value = true;
  enterAdminMode();
  setAdminViewMode('admin_testmode');
  await navigateTo('/');
};

const leaveAdminMode = async () => {
  if (!confirmDiscardTaskDrafts()) return;
  allowRouteLeave.value = true;
  resetWorkspace();
  exitAdminMode();
  await navigateTo('/');
};

const toggleSection = (section: AdminSectionKey) => {
  openSections.value[section] = !openSections.value[section];
};

const selectEvent = (eventId: string) => {
  selectedEventId.value = eventId;
  openSections.value = {
    participants: true,
    logs: false,
    tasks: true,
    events: true,
    personas: true,
  };
};

</script>
