<template>
  <section class="participant-dashboard">
    <div class="participant-toolbar">
      <div class="participant-counts">
        <span class="participant-count">啟用 {{ activeCount }} 位</span>
        <span class="participant-count">封存 {{ archivedCount }} 位</span>
        <label class="participant-archive-filter">
          <input v-model="showArchived" type="checkbox" class="h-4 w-4 accent-[var(--admin-coffee)]" />
          顯示封存
        </label>
      </div>
      <button type="button" class="admin-button-primary participant-create-button" @click="openCreateForm">
        <Icon name="mdi:account-plus-outline" class="h-4 w-4" />
        新增受測者
      </button>
    </div>

    <div class="participant-search-row">
      <label class="participant-search">
        <span class="admin-label">搜尋受測者與對話</span>
        <span class="participant-search-control">
          <Icon name="mdi:magnify" class="participant-search-icon" aria-hidden="true" />
          <input
            v-model="searchQuery"
            type="search"
            class="admin-field min-h-10 w-full text-sm"
            placeholder="受測者代號、歷史事件或 Session ID"
          />
        </span>
      </label>
      <p class="participant-search-count" aria-live="polite">顯示 {{ visibleRows.length }} / {{ rows.length }} 位</p>
      <button v-if="searchQuery" type="button" class="participant-text-button" @click="searchQuery = ''">清除搜尋</button>
    </div>

    <div class="participant-list">
      <article v-for="row in visibleRows" :key="row.participant.id" class="participant-card">
        <header class="participant-identity">
          <div class="participant-identity-copy">
            <p class="participant-eyebrow">受測者</p>
            <h3 class="participant-code">{{ row.participant.code }}</h3>
          </div>
          <div class="participant-status-actions">
            <span class="participant-status" :class="{ 'is-active': row.participant.status === 'active' }">
              {{ participantStatusLabel(row.participant.status) }}
            </span>
            <button
              v-if="row.participant.status === 'archived'"
              type="button"
              class="participant-text-button"
              :disabled="changingParticipantStatusId === row.participant.id"
              @click="$emit('restore', row.participant)"
            >恢復</button>
            <button
              v-else
              type="button"
              class="participant-text-button"
              :disabled="changingParticipantStatusId === row.participant.id"
              @click="archiveTarget = row"
            >封存</button>
          </div>
        </header>

        <div class="participant-account">
          <button type="button" class="participant-binding" :class="{ 'is-unbound': !row.isBound }" @click="openEditor(row)">
            <Icon :name="row.isBound ? 'mdi:link-variant' : 'mdi:link-variant-plus'" class="h-4 w-4" />
            {{ row.isBound ? '已綁定' : '未綁定，選擇帳號' }}
          </button>
          <span v-if="row.authUser?.email" class="participant-email">{{ row.authUser.email }}</span>
          <span v-else-if="row.participant.auth_user_id" class="participant-session-id">{{ shortId(row.participant.auth_user_id) }}</span>
        </div>

        <div class="participant-activities">
          <button
            v-for="(activity, index) in row.activities"
            :key="activity.key"
            type="button"
            class="participant-activity"
            :class="{ 'is-selected': selectedActivity(row)?.key === activity.key }"
            :aria-expanded="selectedActivity(row)?.key === activity.key"
            :aria-controls="`${row.participant.id}-activity-records`"
            :aria-label="`查看 ${row.participant.code} ${activity.eventName} ${activity.code} 的活動紀錄`"
            :title="`${activity.code} ${activity.label}`"
            @click="toggleActivity(row, activity.key)"
          >
            <span class="participant-activity-order">{{ activity.isAssigned ? String(index + 1).padStart(2, '0') : '先前' }}</span>
            <span class="participant-activity-copy">
              <span class="participant-activity-name">{{ activity.eventName }}</span>
              <span class="participant-activity-mode">{{ activity.code }} {{ activityModeLabels[activity.code] || activity.label }}</span>
              <span class="participant-activity-summary">{{ activity.sessionHistory.length ? `${activity.sessionHistory.length} 筆紀錄 · ${activity.stage === 'not_started' ? '僅有封存紀錄' : participantStageLabels[activity.stage]}` : '尚未開始 · 點選查看' }}</span>
            </span>
            <Icon :name="selectedActivity(row)?.key === activity.key ? 'mdi:chevron-up' : 'mdi:chevron-down'" class="h-4 w-4 shrink-0" />
          </button>
        </div>

        <div class="participant-support-row">
          <div class="participant-support-actions">
            <button v-if="!row.assignedConditions.length" type="button" class="participant-text-button" @click="openEditor(row)">尚未分派活動</button>
            <button
              v-else
              type="button"
              class="participant-text-button"
              :aria-label="`重新分配 ${row.participant.code} 的活動`"
              :disabled="savingParticipantId === row.participant.id"
              @click="openEditor(row)"
            >
              <Icon name="mdi:pencil-outline" class="h-4 w-4" />
              重新分配
            </button>
            <button
              v-if="row.participant.status === 'active'"
              type="button"
              class="participant-text-button"
              :aria-label="`模擬受測者 ${row.participant.code}`"
              @click="$emit('preview', row.participant)"
            >
              <Icon name="mdi:eye-outline" class="h-4 w-4" />
              模擬此受測者
            </button>
          </div>
          <p class="participant-last-active">{{ row.updatedAt ? `最後活動 ${formatDate(row.updatedAt)}` : '尚無活動紀錄' }}</p>
        </div>

        <div class="participant-progress-row">
          <p class="participant-progress-label">{{ activityProgressLabel(row) }}</p>
          <div v-if="selectedActivity(row)" class="participant-progress">
            <span
              v-for="stage in stages"
              :key="stage"
              class="participant-progress-step"
              :class="{ 'is-current': selectedActivity(row)?.stage === stage }"
            >{{ participantStageLabels[stage] }}</span>
          </div>
        </div>

        <p v-if="row.activities.length && !selectedActivity(row)" class="participant-hint">點選事件查看紀錄、對話與數據。</p>
        <div v-if="selectedActivity(row)" :id="`${row.participant.id}-activity-records`" class="participant-records">
          <div class="participant-records-heading">
            <div class="min-w-0">
              <p class="participant-eyebrow">活動紀錄</p>
              <h4 class="participant-records-title">{{ selectedActivity(row)?.eventName }} <span :title="selectedActivity(row)?.label">{{ selectedActivity(row)?.code }} {{ activityModeLabels[selectedActivity(row)?.code || ''] || selectedActivity(row)?.label }}</span></h4>
            </div>
            <span class="participant-record-count">{{ selectedActivity(row)?.sessionHistory.length }} 筆</span>
          </div>
          <p v-if="!selectedActivity(row)?.sessionHistory.length" class="admin-empty-state mt-3 p-4 text-sm" role="status">
            {{ selectedActivity(row)?.eventId ? '此受測者尚未開始這個活動，目前沒有對話或量化數據。' : '此模式尚未指定歷史事件，請使用「重新分配」設定活動。' }}
          </p>
          <div class="participant-record-list">
            <div v-for="item in selectedActivity(row)?.sessionHistory" :key="item.session.id" class="participant-record">
              <div class="participant-record-info">
                <div class="participant-record-status">
                  <span>{{ latestActivitySessionId(row) === item.session.id ? '最新紀錄' : '歷史紀錄' }}<span v-if="item.session.status === 'archived'"> · 已封存</span></span>
                  <span class="participant-record-state">{{ sessionStatusLabel(item.session.status) }}</span>
                </div>
                <p class="participant-record-meta">{{ formatDate(item.session.created_at) }} <span class="participant-session-id">{{ shortId(item.session.id) }}</span></p>
                <p class="participant-record-meta">{{ sessionTimerLabel(item.session) }}</p>
              </div>
              <div class="participant-record-actions">
                <NuxtLink
                  v-if="item.session.status !== 'archived'"
                  :to="{ path: '/admin-monitor', query: { session: item.session.id } }"
                  class="admin-button-secondary participant-record-button inline-flex items-center gap-2"
                  :aria-label="`監測 ${row.participant.code} ${item.eventName} 的施測與審核`"
                >
                  <Icon name="mdi:eye-outline" class="h-4 w-4" />
                  施測監測
                </NuxtLink>
                <button
                  type="button"
                  class="admin-button-primary participant-record-button"
                  :aria-label="`查看 ${row.participant.code} ${item.eventName} ${shortId(item.session.id)} 的對話與數據`"
                  @click="$emit('view-research', item.session.id)"
                >
                  <Icon name="mdi:file-document-outline" class="h-4 w-4" />
                  對話與數據
                </button>
                <button
                  type="button"
                  class="admin-button-secondary participant-record-button"
                  :disabled="item.session.status === 'archived' || !canResetTimer(item.session) || updatingTimerSessionId === item.session.id"
                  :title="canResetTimer(item.session) ? '從現在重新開始五分鐘倒數' : '進入 Chat 後才會自動開始倒數'"
                  @click="$emit('reset-timer', item.session.id)"
                >
                  <Icon :name="updatingTimerSessionId === item.session.id ? 'mdi:loading' : 'mdi:timer-refresh-outline'" class="h-4 w-4" :class="{ 'animate-spin': updatingTimerSessionId === item.session.id }" />
                  重置 05:00
                </button>
                <button
                  type="button"
                  class="participant-text-button participant-restart-button"
                  :disabled="item.session.status === 'archived' || restartingSessionId === item.session.id"
                  @click="restartTarget = item"
                >
                  <Icon :name="restartingSessionId === item.session.id ? 'mdi:loading' : 'mdi:restart'" class="h-4 w-4" :class="{ 'animate-spin': restartingSessionId === item.session.id }" />
                  封存並重建
                </button>
              </div>
            </div>
          </div>
        </div>
      </article>
    </div>

    <div v-if="!visibleRows.length" class="admin-empty-state p-5">
      {{ rows.length ? '目前沒有符合篩選條件的受測者。' : '目前沒有受測者資料。' }}
    </div>

    <Transition
      enter-active-class="transition-opacity duration-150"
      leave-active-class="transition-opacity duration-150"
      enter-from-class="opacity-0"
      leave-to-class="opacity-0"
    >
      <div
        v-if="showCreateForm"
        role="dialog"
        aria-modal="true"
        aria-labelledby="participant-create-title"
        class="participant-dialog-backdrop fixed inset-0 z-50 flex items-center justify-center p-4"
        @click.self="closeCreateForm"
      >
        <article class="participant-dialog max-h-[90dvh] w-full max-w-2xl overflow-y-auto p-5">
          <div class="flex items-start justify-between gap-4">
            <div>
              <p class="admin-kicker">Participant registry</p>
              <h3 id="participant-create-title" class="admin-heading mt-1 font-serif text-2xl font-bold">新增受測者</h3>
            </div>
            <button type="button" class="admin-button-secondary px-3 py-2 text-xs font-bold" @click="closeCreateForm">
              關閉
            </button>
          </div>

          <div class="mt-5 grid gap-5">
            <label class="block">
              <span class="admin-label">受測者代號</span>
              <input
                v-model="createCode"
                class="admin-field mt-1 w-full px-3 py-2 text-sm font-bold uppercase"
                placeholder="例如 P006"
              />
            </label>

            <label class="block">
              <span class="admin-label">Auth 帳號（可稍後綁定）</span>
              <select v-model="createAuthUserId" class="admin-field mt-1 w-full px-3 py-2 text-sm font-bold">
                <option value="">暫不綁定</option>
                <option
                  v-for="user in unboundAuthUsers"
                  :key="user.id"
                  :value="user.id"
                >
                  {{ user.email || shortId(user.id) }}
                </option>
              </select>
            </label>

            <fieldset :disabled="creatingParticipant">
              <legend class="admin-label">活動與執行順序</legend>
              <p class="admin-caption mt-1 text-xs leading-6">每個活動指定一個歷史事件與模式，受測者依序完成。草稿教材可供管理員測試；正式使用前需另外鎖定教材。</p>
              <div class="mt-3 grid gap-3">
                <div v-for="(activity, index) in createActivities" :key="index" class="rounded-[9px] border border-[var(--admin-border)] bg-[var(--admin-surface-muted)] p-3">
                  <div class="mb-2 flex items-center justify-between gap-2">
                    <span class="text-sm font-black text-[var(--admin-coffee)]">第 {{ index + 1 }} 個活動</span>
                    <div class="flex items-center gap-1">
                      <button type="button" class="admin-button-secondary inline-flex h-8 w-8 items-center justify-center p-0" :disabled="index === 0" :aria-label="`第 ${index + 1} 個活動往前移`" @click="moveActivity(createActivities, index, -1)">
                        <Icon name="mdi:arrow-up" class="h-4 w-4" />
                      </button>
                      <button type="button" class="admin-button-secondary inline-flex h-8 w-8 items-center justify-center p-0" :disabled="index === createActivities.length - 1" :aria-label="`第 ${index + 1} 個活動往後移`" @click="moveActivity(createActivities, index, 1)">
                        <Icon name="mdi:arrow-down" class="h-4 w-4" />
                      </button>
                      <button type="button" class="admin-button-secondary inline-flex h-8 w-8 items-center justify-center p-0" :aria-label="`移除第 ${index + 1} 個活動`" @click="createActivities.splice(index, 1)">
                        <Icon name="mdi:close" class="h-4 w-4" />
                      </button>
                    </div>
                  </div>
                  <div class="grid gap-3 sm:grid-cols-2">
                    <label class="block">
                      <span class="admin-label">歷史事件</span>
                      <select v-model="activity.event_id" :aria-label="`第 ${index + 1} 個活動的歷史事件`" class="admin-field mt-1 min-h-10 w-full px-3 py-2 text-sm font-bold">
                        <option value="">請選擇歷史事件</option>
                        <option v-if="activity.event_id && !availableEvents.some(item => item.id === activity.event_id)" :value="activity.event_id" disabled>原事件已封存或不存在</option>
                        <option v-for="event in availableEvents" :key="event.id" :value="event.id" :disabled="createActivities.some((item, otherIndex) => otherIndex !== index && item.event_id === event.id)">
                          {{ event.canonical_name }}{{ event.materials_locked_at ? '' : '（草稿）' }}
                        </option>
                      </select>
                    </label>
                    <label class="block">
                      <span class="admin-label">模式</span>
                      <select v-model="activity.condition_code" :aria-label="`第 ${index + 1} 個活動的模式`" class="admin-field mt-1 min-h-10 w-full px-3 py-2 text-sm font-bold">
                        <option value="">請選擇模式</option>
                        <option v-for="condition in conditionOptions" :key="condition.code" :value="condition.code" :disabled="createActivities.some((item, otherIndex) => otherIndex !== index && item.condition_code === condition.code)">
                          {{ condition.code }} {{ condition.label }}
                        </option>
                      </select>
                    </label>
                  </div>
                </div>
              </div>
              <p v-if="!createActivities.length" class="admin-caption mt-3 text-sm">尚未分派活動，可稍後設定。</p>
              <button type="button" class="admin-button-secondary mt-3 inline-flex min-h-10 items-center gap-2 px-3 text-sm font-bold" :disabled="createActivities.length >= 4" @click="addActivity(createActivities)">
                <Icon name="mdi:plus" class="h-4 w-4" />新增活動
              </button>
              <p v-if="createValidationError" role="alert" class="admin-caption mt-2 text-sm">{{ createValidationError }}</p>
            </fieldset>
          </div>

          <div class="mt-6 flex justify-end gap-2">
            <button type="button" class="admin-button-secondary px-4 py-2 text-sm font-bold" @click="closeCreateForm">
              取消
            </button>
            <button
              type="button"
              class="admin-button-primary inline-flex min-h-10 items-center gap-2 px-4 text-sm font-bold"
              :disabled="creatingParticipant || !createCode.trim() || Boolean(createValidationError)"
              @click="submitCreateForm"
            >
              <Icon :name="creatingParticipant ? 'mdi:loading' : 'mdi:account-plus-outline'" class="h-4 w-4" :class="{ 'animate-spin': creatingParticipant }" />
              建立
            </button>
          </div>
          <p v-if="createAttempted && operationError" role="alert" class="admin-error mt-3 whitespace-pre-line px-3 py-2 text-sm">{{ operationError }}</p>
        </article>
      </div>
    </Transition>

    <Transition
      enter-active-class="transition-opacity duration-150"
      leave-active-class="transition-opacity duration-150"
      enter-from-class="opacity-0"
      leave-to-class="opacity-0"
    >
      <div
        v-if="editingRow"
        role="dialog"
        aria-modal="true"
        aria-labelledby="participant-editor-title"
        class="participant-dialog-backdrop fixed inset-0 z-50 flex items-center justify-center p-4"
        @click.self="closeEditor"
      >
        <article class="participant-dialog max-h-[90dvh] w-full max-w-2xl overflow-y-auto p-5">
          <div class="flex items-start justify-between gap-4">
            <div class="min-w-0 [overflow-wrap:anywhere]">
              <p class="admin-kicker">受測者設定</p>
              <h3 id="participant-editor-title" class="admin-heading mt-1 font-serif text-2xl font-bold">{{ editingRow.participant.code }} · 帳號與活動分派</h3>
            </div>
            <button type="button" class="admin-button-secondary shrink-0 px-3 py-2 text-xs font-bold" @click="closeEditor">
              關閉
            </button>
          </div>

          <div class="mt-5 grid gap-5">
            <label class="block">
              <span class="admin-label">Auth 帳號</span>
              <select v-model="draftAuthUserId" class="admin-field mt-1 w-full px-3 py-2 text-sm font-bold">
                <option value="">不綁定</option>
                <option
                  v-for="user in selectableAuthUsers"
                  :key="user.id"
                  :value="user.id"
                  :disabled="Boolean(user.bound_participant_id && user.bound_participant_id !== editingRow.participant.id)"
                >
                  {{ user.email || shortId(user.id) }}
                  {{ user.bound_participant_code && user.bound_participant_id !== editingRow.participant.id ? `（已綁定 ${user.bound_participant_code}）` : '' }}
                </option>
              </select>
              <p v-if="!authUsers.length" class="admin-caption mt-2 text-xs font-bold">
                尚未載入 Auth users，請確認 admin key 與 Supabase Auth 狀態。
              </p>
            </label>

            <label class="block">
              <span class="admin-label">或手動輸入 Auth user id</span>
              <input
                v-model="draftAuthUserId"
                class="admin-field mt-1 w-full px-3 py-2 font-mono text-xs"
                placeholder="Supabase Auth user UUID"
              />
            </label>

            <fieldset :disabled="savingParticipantId === editingRow.participant.id">
              <legend class="admin-label">活動與執行順序</legend>
              <p class="admin-caption mt-1 text-xs leading-6">每個活動指定一個歷史事件與模式，受測者依序完成。草稿教材可供管理員測試；正式使用前需另外鎖定教材。</p>
              <div class="mt-3 grid gap-3">
                <div v-for="(activity, index) in draftActivities" :key="index" class="rounded-[9px] border border-[var(--admin-border)] bg-[var(--admin-surface-muted)] p-3">
                  <div class="mb-2 flex items-center justify-between gap-2">
                    <span class="text-sm font-black text-[var(--admin-coffee)]">第 {{ index + 1 }} 個活動</span>
                    <div class="flex items-center gap-1">
                      <button type="button" class="admin-button-secondary inline-flex h-8 w-8 items-center justify-center p-0" :disabled="index === 0" :aria-label="`第 ${index + 1} 個活動往前移`" @click="moveActivity(draftActivities, index, -1)">
                        <Icon name="mdi:arrow-up" class="h-4 w-4" />
                      </button>
                      <button type="button" class="admin-button-secondary inline-flex h-8 w-8 items-center justify-center p-0" :disabled="index === draftActivities.length - 1" :aria-label="`第 ${index + 1} 個活動往後移`" @click="moveActivity(draftActivities, index, 1)">
                        <Icon name="mdi:arrow-down" class="h-4 w-4" />
                      </button>
                      <button type="button" class="admin-button-secondary inline-flex h-8 w-8 items-center justify-center p-0" :aria-label="`移除第 ${index + 1} 個活動`" @click="draftActivities.splice(index, 1)">
                        <Icon name="mdi:close" class="h-4 w-4" />
                      </button>
                    </div>
                  </div>
                  <div class="grid gap-3 sm:grid-cols-2">
                    <label class="block">
                      <span class="admin-label">歷史事件</span>
                      <select v-model="activity.event_id" :aria-label="`第 ${index + 1} 個活動的歷史事件`" class="admin-field mt-1 min-h-10 w-full px-3 py-2 text-sm font-bold">
                        <option value="">請選擇歷史事件</option>
                        <option v-if="activity.event_id && !availableEvents.some(item => item.id === activity.event_id)" :value="activity.event_id" disabled>原事件已封存或不存在</option>
                        <option v-for="event in availableEvents" :key="event.id" :value="event.id" :disabled="draftActivities.some((item, otherIndex) => otherIndex !== index && item.event_id === event.id)">
                          {{ event.canonical_name }}{{ event.materials_locked_at ? '' : '（草稿）' }}
                        </option>
                      </select>
                    </label>
                    <label class="block">
                      <span class="admin-label">模式</span>
                      <select v-model="activity.condition_code" :aria-label="`第 ${index + 1} 個活動的模式`" class="admin-field mt-1 min-h-10 w-full px-3 py-2 text-sm font-bold">
                        <option value="">請選擇模式</option>
                        <option v-for="condition in conditionOptions" :key="condition.code" :value="condition.code" :disabled="draftActivities.some((item, otherIndex) => otherIndex !== index && item.condition_code === condition.code)">
                          {{ condition.code }} {{ condition.label }}
                        </option>
                      </select>
                    </label>
                  </div>
                </div>
              </div>
              <p v-if="!draftActivities.length" class="admin-caption mt-3 text-sm">尚未分派活動，可稍後設定。</p>
              <button type="button" class="admin-button-secondary mt-3 inline-flex min-h-10 items-center gap-2 px-3 text-sm font-bold" :disabled="draftActivities.length >= 4" @click="addActivity(draftActivities)">
                <Icon name="mdi:plus" class="h-4 w-4" />新增活動
              </button>
              <p v-if="draftValidationError" role="alert" class="admin-caption mt-2 text-sm">{{ draftValidationError }}</p>
            </fieldset>
          </div>

          <div class="mt-6 flex justify-end gap-2">
            <button type="button" class="admin-button-secondary px-4 py-2 text-sm font-bold" @click="closeEditor">
              取消
            </button>
            <button
              type="button"
              class="admin-button-primary inline-flex min-h-10 items-center gap-2 px-4 text-sm font-bold"
              :disabled="savingParticipantId === editingRow.participant.id || Boolean(draftValidationError)"
              @click="saveEditor"
            >
              <Icon :name="savingParticipantId === editingRow.participant.id ? 'mdi:loading' : 'mdi:content-save-outline'" class="h-4 w-4" :class="{ 'animate-spin': savingParticipantId === editingRow.participant.id }" />
              儲存
            </button>
          </div>
          <p v-if="saveAttempted && operationError" role="alert" class="admin-error mt-3 whitespace-pre-line px-3 py-2 text-sm">{{ operationError }}</p>
        </article>
      </div>
    </Transition>

    <ConfirmActionModal
      :show="Boolean(restartTarget)"
      title="重新建立 Session"
      :message="restartConfirmationMessage"
      eyebrow="受測者流程"
      icon="mdi:restart-alert"
      confirm-label="封存並重建"
      cancel-label="取消"
      @confirm="confirmRestart"
      @cancel="restartTarget = null"
    />

    <ConfirmActionModal
      :show="Boolean(archiveTarget)"
      title="封存受測者"
      :message="archiveConfirmationMessage"
      eyebrow="Participant registry"
      icon="mdi:archive-arrow-down-outline"
      confirm-label="封存"
      cancel-label="取消"
      @confirm="confirmArchive"
      @cancel="archiveTarget = null"
    />
  </section>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue';
import { useBodyScrollLock } from '~/composables/useBodyScrollLock';
import ConfirmActionModal from '~/components/modals/ConfirmActionModal.vue';
import type { AdminAuthUserSummary, ExperimentSession, HistoricalEvent, Participant } from '~/types';
import type { ParticipantCreateInput, ParticipantUpdateInput } from '~/utils/histosphereApi';
import {
  conditionDisplayLabel,
  conditionName,
  buildParticipantActivityDraft,
  participantActivityAssignmentInput,
  validateParticipantActivityDraft,
  filterParticipantDashboardRows,
  participantConditionLabels,
  participantStageLabels,
  type ParticipantDashboardRow,
  type ParticipantSessionSummary,
  type ParticipantStage,
  type ParticipantActivityDraft,
} from '~/utils/adminParticipantDashboard';

const props = defineProps<{
  rows: ParticipantDashboardRow[];
  events: HistoricalEvent[];
  operationError?: string | null;
  authUsers: AdminAuthUserSummary[];
  creatingParticipant: boolean;
  changingParticipantStatusId: string | null;
  savingParticipantId: string | null;
  updatingTimerSessionId: string | null;
  restartingSessionId: string | null;
}>();

const emit = defineEmits<{
  (event: 'create', payload: ParticipantCreateInput): void;
  (event: 'archive', participant: Participant): void;
  (event: 'restore', participant: Participant): void;
  (event: 'save', participantId: string, payload: ParticipantUpdateInput): void;
  (event: 'preview', participant: Participant): void;
  (event: 'reset-timer', sessionId: string): void;
  (event: 'restart-session', sessionId: string): void;
  (event: 'view-research', sessionId: string): void;
}>();

const stages: ParticipantStage[] = ['not_started', 'task', 'chat', 'completed'];
const activityModeLabels: Record<string, string> = {
  '01': '基準',
  '02': '錯誤學習',
  '03': '角色扮演',
  '04': '錯誤學習＋角色扮演',
};
const showArchived = ref(false);
const searchQuery = ref('');
const selectedActivityKeys = ref<Record<string, string>>({});
const showCreateForm = ref(false);
const createCode = ref('');
const createAuthUserId = ref('');
const createActivities = ref<ParticipantActivityDraft[]>([]);
const createAttempted = ref(false);
const editingRow = ref<ParticipantDashboardRow | null>(null);
const draftAuthUserId = ref('');
const draftActivities = ref<ParticipantActivityDraft[]>([]);
const saveAttempted = ref(false);
const restartTarget = ref<ParticipantSessionSummary | null>(null);
const archiveTarget = ref<ParticipantDashboardRow | null>(null);

useBodyScrollLock(() => Boolean(showCreateForm.value || editingRow.value || archiveTarget.value || restartTarget.value));

const selectedActivity = (row: ParticipantDashboardRow) => row.activities.find((activity) => activity.key === selectedActivityKeys.value[row.participant.id]);
const activityProgressLabel = (row: ParticipantDashboardRow) => selectedActivity(row)
  ? '所選活動進度'
  : `已完成 ${row.conditionProgress.filter((activity) => activity.stage === 'completed').length} / ${row.assignedConditions.length} 個分派活動`;
const toggleActivity = (row: ParticipantDashboardRow, activityKey: string) => {
  selectedActivityKeys.value[row.participant.id] = selectedActivity(row)?.key === activityKey ? '' : activityKey;
};
const latestActivitySessionId = (row: ParticipantDashboardRow) => {
  const sessions = selectedActivity(row)?.sessionHistory || [];
  return (sessions.find((item) => item.session.status !== 'archived') || sessions[0])?.session.id;
};

const visibleRows = computed(() => filterParticipantDashboardRows(props.rows, showArchived.value, searchQuery.value));
const activeCount = computed(() => props.rows.filter((row) => row.participant.status === 'active').length);
const archivedCount = computed(() => props.rows.filter((row) => row.participant.status === 'archived').length);
const unboundAuthUsers = computed(() => props.authUsers.filter((user) => !user.bound_participant_id));
const availableEvents = computed(() => props.events.filter((event) => !event.archived_at));
const createValidationError = computed(() => validateParticipantActivityDraft(createActivities.value, props.events));
const draftValidationError = computed(() => validateParticipantActivityDraft(draftActivities.value, props.events));

const archiveConfirmationMessage = computed(() => {
  if (!archiveTarget.value) return '';
  return `封存 ${archiveTarget.value.participant.code} 後將停止其實驗存取；Auth 綁定、Session、Task、Chat 與研究紀錄都會保留。`;
});

const restartConfirmationMessage = computed(() => {
  if (!restartTarget.value) return '';
  return `這會封存「${restartTarget.value.eventName}」的舊 session 與對話，保留所有研究資料，再建立一筆新的 ${restartTarget.value.conditionCode} session。`;
});

const conditionOptions = computed(() => {
  return Object.keys(participantConditionLabels).map((code) => ({
    code,
    label: conditionName(code),
    display: conditionDisplayLabel(code),
  }));
});

const selectableAuthUsers = computed(() => {
  const currentAuthId = editingRow.value?.participant.auth_user_id;
  return props.authUsers.filter((user) => {
    return !user.bound_participant_id
      || user.bound_participant_id === editingRow.value?.participant.id
      || user.id === currentAuthId;
  });
});

const openCreateForm = () => {
  createCode.value = '';
  createAuthUserId.value = '';
  createActivities.value = [];
  createAttempted.value = false;
  showCreateForm.value = true;
};

const closeCreateForm = () => {
  if (props.creatingParticipant) return;
  showCreateForm.value = false;
  createCode.value = '';
  createAuthUserId.value = '';
  createActivities.value = [];
  createAttempted.value = false;
};

const submitCreateForm = () => {
  const code = createCode.value.trim().toUpperCase();
  if (!code || props.creatingParticipant || createValidationError.value) return;
  createAttempted.value = true;
  emit('create', {
    code,
    auth_user_id: createAuthUserId.value || null,
    ...participantActivityAssignmentInput(createActivities.value, props.events),
  });
};

const openEditor = (row: ParticipantDashboardRow) => {
  editingRow.value = row;
  draftAuthUserId.value = row.participant.auth_user_id || '';
  draftActivities.value = buildParticipantActivityDraft(row.participant);
  saveAttempted.value = false;
};

const closeEditor = () => {
  if (props.savingParticipantId === editingRow.value?.participant.id) return;
  editingRow.value = null;
  draftAuthUserId.value = '';
  draftActivities.value = [];
  saveAttempted.value = false;
};

const addActivity = (activities: ParticipantActivityDraft[]) => {
  if (activities.length >= 4) return;
  const unusedCode = conditionOptions.value.find((condition) => !activities.some((activity) => activity.condition_code === condition.code));
  activities.push({ event_id: '', condition_code: unusedCode?.code || '' });
};

const moveActivity = (activities: ParticipantActivityDraft[], index: number, direction: -1 | 1) => {
  const targetIndex = index + direction;
  if (targetIndex < 0 || targetIndex >= activities.length) return;
  const [activity] = activities.splice(index, 1);
  if (!activity) return;
  activities.splice(targetIndex, 0, activity);
};

const saveEditor = () => {
  if (!editingRow.value || props.savingParticipantId || draftValidationError.value) return;
  saveAttempted.value = true;
  emit('save', editingRow.value.participant.id, {
    auth_user_id: draftAuthUserId.value || null,
    ...participantActivityAssignmentInput(draftActivities.value, props.events),
  });
};

watch(() => props.savingParticipantId, (current, previous) => {
  if (saveAttempted.value && previous === editingRow.value?.participant.id && !current && !props.operationError) closeEditor();
});

watch(() => props.creatingParticipant, (current, previous) => {
  if (createAttempted.value && previous && !current && !props.operationError) closeCreateForm();
});

const shortId = (id: string) => {
  return `${id.slice(0, 8)}...${id.slice(-4)}`;
};

const formatDate = (value: string) => {
  return new Intl.DateTimeFormat('zh-TW', {
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  }).format(new Date(value));
};

const canResetTimer = (session: ExperimentSession) => {
  return session.status === 'conversation_started'
    || (session.status === 'completed' && session.completion_reason === 'timer_elapsed');
};

const sessionTimerLabel = (session: ExperimentSession) => {
  if (session.timer_ends_at) {
    const prefix = session.status === 'completed' ? '已結束' : '倒數至';
    return `${prefix} ${formatDate(session.timer_ends_at)}`;
  }
  return `${sessionStatusLabel(session.status)} · Chat 後自動倒數`;
};

const confirmRestart = () => {
  if (!restartTarget.value) return;
  emit('restart-session', restartTarget.value.session.id);
  restartTarget.value = null;
};

const confirmArchive = () => {
  if (!archiveTarget.value) return;
  emit('archive', archiveTarget.value.participant);
  archiveTarget.value = null;
};

const participantStatusLabel = (status: Participant['status']) => {
  if (status === 'archived') return '已封存';
  if (status === 'completed') return '已完成';
  if (status === 'excluded') return '已排除';
  return '使用中';
};

const sessionStatusLabel = (status: string) => {
  if (status === 'archived') return '已封存';
  if (status === 'completed') return '已完成';
  if (status === 'conversation_started') return 'Chat';
  if (status === 'task_submitted') return 'Task 已提交';
  return 'Task';
};
</script>

<style scoped>
.participant-dashboard {
  display: grid;
  gap: 28px;
  color: var(--admin-text, #292d29);
}

.participant-toolbar,
.participant-counts,
.participant-search-row,
.participant-status-actions,
.participant-account,
.participant-support-row,
.participant-support-actions,
.participant-progress-row,
.participant-records-heading,
.participant-record-status,
.participant-record-actions {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 12px;
}

.participant-toolbar,
.participant-support-row,
.participant-records-heading {
  justify-content: space-between;
}

.participant-counts { gap: 16px; }

.participant-count,
.participant-archive-filter,
.participant-search-count,
.participant-last-active,
.participant-progress-label,
.participant-hint,
.participant-record-count,
.participant-record-meta {
  color: var(--admin-copy, #73796f);
  font-size: 13px;
  font-weight: 400;
  line-height: 1.6;
}

.participant-archive-filter {
  display: inline-flex;
  min-height: 36px;
  align-items: center;
  gap: 8px;
  cursor: pointer;
}

.participant-create-button,
.participant-record-button,
.participant-text-button,
.participant-binding {
  display: inline-flex;
  min-height: 38px;
  align-items: center;
  justify-content: center;
  gap: 7px;
  padding: 8px 12px;
  font-size: 14px;
  font-weight: 500;
  line-height: 1.5;
  white-space: nowrap;
}

.participant-create-button { min-height: 40px; }

.participant-text-button,
.participant-binding {
  border: 1px solid transparent;
  border-radius: 6px;
  background: transparent;
  color: var(--admin-copy, #73796f);
  cursor: pointer;
}

.participant-text-button:hover:not(:disabled),
.participant-binding:hover {
  background: var(--admin-surface-muted, #f5f0ea);
  color: var(--admin-coffee, #7b5d49);
}

.participant-text-button:focus-visible,
.participant-binding:focus-visible,
.participant-activity:focus-visible {
  outline: 2px solid var(--admin-coffee-muted, #b29e8f);
  outline-offset: 3px;
}

.participant-text-button:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}

.participant-search-row { align-items: flex-end; }
.participant-search { flex: 1 1 300px; max-width: 540px; min-width: 0; }
.participant-search-control { position: relative; display: block; margin-top: 4px; }
.participant-search-control .admin-field { padding-inline: 36px 12px; }
.participant-search-icon { position: absolute; top: 50%; left: 12px; width: 16px; height: 16px; color: var(--admin-coffee-muted, #a88d7b); pointer-events: none; transform: translateY(-50%); }
.participant-search-count { padding-bottom: 10px; }
.participant-list { display: grid; gap: 28px; }

.participant-card {
  min-width: 0;
  padding: 28px 0 0;
  border-top: 1px solid var(--admin-border-soft, #ede8e1);
  background: transparent;
}

.participant-identity {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 12px 24px;
}

.participant-identity-copy { min-width: 0; }

.participant-eyebrow {
  color: var(--admin-copy, #73796f);
  font-size: 12px;
  font-weight: 500;
  line-height: 1.5;
  letter-spacing: 0.04em;
}

.participant-code {
  margin-top: 5px;
  color: var(--admin-text, #292d29);
  font-size: 22px;
  font-weight: 600;
  line-height: 1.3;
  letter-spacing: 0;
  overflow-wrap: anywhere;
}

.participant-status-actions { flex-shrink: 0; gap: 8px; }

.participant-status {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  color: var(--admin-copy, #73796f);
  font-size: 13px;
  line-height: 1.5;
}

.participant-status::before {
  width: 5px;
  height: 5px;
  border-radius: 50%;
  background: #b1a79f;
  content: '';
}

.participant-status.is-active { color: var(--admin-coffee, #7b5d49); }
.participant-status.is-active::before { background: var(--admin-coffee-muted, #a38c7a); }
.participant-account { margin-top: 7px; gap: 4px 10px; }
.participant-binding { min-height: 28px; padding: 3px 6px; margin-left: -6px; font-size: 13px; }
.participant-binding.is-unbound { color: #746135; background: #f7f2e7; }
.participant-email { min-width: 0; color: var(--admin-copy, #73796f); font-size: 13px; overflow-wrap: anywhere; }
.participant-session-id { color: var(--admin-copy, #73796f); font-family: 'SFMono-Regular', Consolas, monospace; font-size: 11px; }

.participant-activities {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 16px;
  margin-top: 24px;
}

.participant-activities:empty { display: none; }

.participant-activity {
  display: flex;
  min-width: 0;
  align-items: flex-start;
  gap: 12px;
  padding: 20px;
  border: 1px solid var(--admin-border-soft, #ede8e1);
  border-radius: 16px;
  background: var(--admin-surface-muted, #f8f5f0);
  color: var(--admin-text, #292d29);
  text-align: left;
  cursor: pointer;
  box-shadow: var(--admin-edge-light, inset 0 1px 0 rgba(255, 255, 255, 0.88));
  transition: border-color 160ms ease, background-color 160ms ease, box-shadow 160ms ease;
}

.participant-activity:hover { background: #f2eee7; border-color: var(--admin-border, #d6cec4); }
.participant-activity.is-selected { border-color: #b5c0aa; background: #f0f3ec; color: var(--admin-coffee, #7b5d49); box-shadow: var(--admin-edge-light), 0 2px 4px rgba(77, 92, 65, 0.035); }
.participant-activity > .iconify { margin-top: 3px; }
.participant-activity-order { display: inline-flex; min-width: 30px; height: 30px; flex-shrink: 0; align-items: center; justify-content: center; padding-inline: 6px; border: 1px solid var(--admin-border-soft); border-radius: 9px; background: var(--admin-surface, #fffdf8); color: var(--admin-coffee, #7b5d4b); box-shadow: var(--admin-edge-light); font-size: 12px; font-weight: 500; font-variant-numeric: tabular-nums; }
.participant-activity.is-selected .participant-activity-order { border-color: #d4ddcc; background: #e7eddf; color: #526248; }
.participant-activity-copy { display: grid; min-width: 0; flex: 1; gap: 5px; overflow-wrap: anywhere; }
.participant-activity-name { font-size: 16px; font-weight: 600; line-height: 1.5; }
.participant-activity-mode { color: var(--admin-copy, #73796f); font-size: 13px; line-height: 1.5; }
.participant-activity-summary { margin-top: 5px; color: var(--admin-copy, #73796f); font-size: 13px; line-height: 1.5; }
.participant-activity.is-selected .participant-activity-summary { color: var(--admin-coffee, #7b5d49); }
.participant-support-row { margin-top: 10px; gap: 4px 12px; }
.participant-support-actions { gap: 2px; margin-left: -9px; }
.participant-support-actions .participant-text-button { padding-inline: 9px; }
.participant-last-active { font-size: 13px; }

.participant-progress-row {
  justify-content: space-between;
  gap: 10px 20px;
  margin-top: 18px;
  padding-top: 16px;
  border-top: 1px solid var(--admin-border-soft, #e5e7e0);
}

.participant-progress { display: flex; flex-wrap: wrap; gap: 6px; }
.participant-progress-step { display: inline-flex; align-items: center; gap: 6px; color: var(--admin-soft, #9a9188); font-size: 13px; }
.participant-progress-step:not(:last-child)::after { width: 20px; height: 1px; margin-right: 2px; background: var(--admin-border, #e6ded5); content: ''; }
.participant-progress-step.is-current { color: var(--admin-coffee, #7b5d49); font-weight: 600; }
.participant-progress-step.is-current::before { width: 5px; height: 5px; flex-shrink: 0; border-radius: 50%; background: var(--admin-coffee, #7b5d4b); box-shadow: 0 0 0 3px var(--admin-coffee-soft, #ede3da); content: ''; }
.participant-hint { margin-top: 8px; font-size: 13px; }
.participant-records { margin-top: 22px; }
.participant-records-heading { gap: 12px; }
.participant-records-title { display: flex; flex-wrap: wrap; align-items: baseline; gap: 4px 10px; margin-top: 4px; font-size: 16px; font-weight: 500; line-height: 1.6; }
.participant-records-title > span { color: var(--admin-copy, #73796f); font-size: 13px; font-weight: 400; }
.participant-record-count { flex-shrink: 0; }
.participant-record-list { margin-top: 12px; }

.participant-record {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 16px 24px;
  padding: 16px 0;
  border-top: 1px solid var(--admin-border-soft, #e5e7e0);
}

.participant-record:last-child { padding-bottom: 0; }
.participant-record-info { min-width: 0; }
.participant-record-status { gap: 10px; font-size: 13px; font-weight: 500; }
.participant-record-state { padding: 3px 9px; border-radius: 999px; background: var(--admin-surface-muted, #f4eee6); color: var(--admin-coffee, #7b5d49); font-size: 13px; font-weight: 400; }
.participant-record-meta { display: flex; flex-wrap: wrap; gap: 6px 12px; margin-top: 5px; font-size: 13px; }
.participant-record-actions { gap: 8px; }
.participant-record-button { min-height: 38px; }
.participant-restart-button { font-size: 13px; }
.participant-dialog-backdrop { background: rgba(47, 41, 36, 0.28); }
.participant-dialog { border: 1px solid var(--admin-border, #e5e7e0); border-radius: var(--admin-radius-panel, 22px); background: var(--admin-surface, #fffdf9); box-shadow: var(--admin-edge-light), 0 20px 64px rgba(65, 55, 47, 0.14); }

@media (prefers-reduced-motion: reduce) {
  .participant-activity { transition: none; }
}

@media (max-width: 767px) {
  .participant-dashboard { gap: 20px; }
  .participant-search { flex-basis: 100%; max-width: none; }
  .participant-search-count { padding-bottom: 0; }
  .participant-search-row { gap: 4px 12px; align-items: center; }
  .participant-card { padding: 24px 0 0; }
  .participant-activities { grid-template-columns: 1fr; }
  .participant-progress-row { align-items: flex-start; flex-direction: column; }
  .participant-record { align-items: flex-start; flex-direction: column; }
  .participant-record-actions { width: 100%; }
  .participant-counts { gap: 4px 12px; }
}

@media (max-width: 479px) {
  .participant-code { font-size: 20px; }
  .participant-activity { padding: 18px 14px; gap: 10px; }
  .participant-create-button { min-height: 44px; }
  .participant-record-button { flex: 1 1 auto; min-height: 44px; }
  .participant-restart-button { min-height: 40px; }
}
</style>
