<template>
  <div class="min-h-screen bg-slate-50 font-sans text-slate-950">
    <header class="border-b border-slate-200 bg-white">
      <div class="mx-auto flex max-w-6xl items-center justify-between px-5 py-4">
        <NuxtLink to="/" class="inline-flex items-center gap-2 text-sm font-semibold text-slate-600 hover:text-slate-950">
          <Icon name="mdi:arrow-left" class="h-5 w-5" />
          回首頁
        </NuxtLink>
        <h1 class="font-bold">Histosphere Admin</h1>
      </div>
    </header>

    <main class="mx-auto max-w-6xl space-y-6 px-5 py-8">
      <section class="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
        <label class="text-sm font-semibold text-slate-700" for="admin-key">Admin key</label>
        <div class="mt-2 flex flex-col gap-2 sm:flex-row">
          <input
            id="admin-key"
            v-model="adminKey"
            type="password"
            class="min-w-0 flex-1 rounded-lg border border-slate-300 px-4 py-3 outline-none focus:border-teal-600 focus:ring-4 focus:ring-teal-100"
            placeholder="HISTOSPHERE_ADMIN_KEY"
          />
          <button
            class="inline-flex items-center justify-center gap-2 rounded-lg bg-slate-950 px-4 py-3 text-sm font-semibold text-white hover:bg-slate-800"
            @click="loadSnapshot"
          >
            <Icon name="mdi:database-search" class="h-5 w-5" />
            載入後台資料
          </button>
        </div>
        <p v-if="error" class="mt-3 rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">{{ error }}</p>
      </section>

      <section v-if="snapshot" class="grid gap-6 lg:grid-cols-[360px_minmax(0,1fr)]">
        <aside class="space-y-4">
          <div class="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
            <h2 class="font-bold">2x2 Conditions</h2>
            <div class="mt-4 space-y-3">
              <article v-for="condition in snapshot.conditions" :key="condition.id" class="rounded-lg border border-slate-200 p-3">
                <input v-model="condition.label" class="w-full rounded border border-slate-200 px-2 py-1 text-sm font-semibold" />
                <textarea v-model="condition.description" rows="3" class="mt-2 w-full rounded border border-slate-200 px-2 py-1 text-sm leading-6" />
                <div class="mt-2 grid grid-cols-2 gap-2 text-xs">
                  <label class="flex items-center gap-2">
                    <input v-model="condition.ebl_enabled" type="checkbox" />
                    EBL
                  </label>
                  <label class="flex items-center gap-2">
                    <input v-model="condition.roleplay_enabled" type="checkbox" />
                    Role-play
                  </label>
                  <select v-model="condition.response_policy" class="rounded border border-slate-200 px-2 py-1">
                    <option value="direct">direct</option>
                    <option value="scaffold">scaffold</option>
                  </select>
                  <label class="flex items-center gap-2">
                    <input v-model="condition.active" type="checkbox" />
                    active
                  </label>
                </div>
                <button class="mt-3 rounded-lg border border-teal-300 px-3 py-2 text-xs font-bold text-teal-700 hover:bg-teal-50" @click="saveCondition(condition)">
                  儲存 condition
                </button>
              </article>
            </div>
          </div>

          <div class="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
            <h2 class="font-bold">Research logs</h2>
            <div class="mt-3 max-h-96 space-y-2 overflow-auto text-xs">
              <div v-for="log in snapshot.research_logs" :key="String(log.id)" class="rounded border border-slate-200 p-2">
                <p class="font-semibold text-slate-800">{{ log.action_type }}</p>
                <p class="text-slate-500">{{ log.created_at }}</p>
              </div>
            </div>
          </div>
        </aside>

        <section class="space-y-4">
          <article v-for="event in snapshot.events" :key="event.id" class="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
            <div class="flex flex-col gap-2 md:flex-row md:items-start md:justify-between">
              <div>
                <h2 class="text-xl font-bold">{{ event.canonical_name }}</h2>
                <p class="mt-1 text-sm leading-6 text-slate-600">{{ event.description || event.context }}</p>
              </div>
              <span class="rounded-full bg-slate-100 px-3 py-1 text-xs font-semibold text-slate-600">
                {{ event.personas.length }} personas
              </span>
            </div>

            <div v-if="event.latest_task" class="mt-5 rounded-lg border border-slate-200 p-4">
              <h3 class="font-bold">Task</h3>
              <input v-model="event.latest_task.title" class="mt-3 w-full rounded border border-slate-200 px-3 py-2 text-sm font-semibold" />
              <textarea v-model="event.latest_task.display_text" rows="4" class="mt-2 w-full rounded border border-slate-200 px-3 py-2 text-sm leading-6" />
              <textarea v-model="event.latest_task.story_text" rows="4" class="mt-2 w-full rounded border border-slate-200 px-3 py-2 text-sm leading-6" />
              <label class="mt-2 block text-xs font-semibold text-slate-500">evaluation_payload JSON</label>
              <textarea v-model="taskJson[event.latest_task.id]" rows="4" class="mt-1 w-full rounded border border-slate-200 px-3 py-2 font-mono text-xs leading-5" />
              <button class="mt-3 rounded-lg bg-slate-950 px-3 py-2 text-xs font-bold text-white hover:bg-slate-800" @click="saveTask(event.latest_task)">
                儲存 task
              </button>
            </div>

            <div class="mt-5 grid gap-3 md:grid-cols-2">
              <div v-for="persona in event.personas" :key="persona.id" class="rounded-lg border border-slate-200 p-4">
                <input v-model="persona.name" class="w-full rounded border border-slate-200 px-3 py-2 text-sm font-semibold" />
                <input v-model="persona.role" class="mt-2 w-full rounded border border-slate-200 px-3 py-2 text-sm" placeholder="role" />
                <textarea v-model="persona.biography" rows="3" class="mt-2 w-full rounded border border-slate-200 px-3 py-2 text-sm leading-6" />
                <label class="mt-2 block text-xs font-semibold text-slate-500">prompt_profile JSON</label>
                <textarea v-model="personaJson[persona.id]" rows="5" class="mt-1 w-full rounded border border-slate-200 px-3 py-2 font-mono text-xs leading-5" />
                <div class="mt-3 flex items-center justify-between gap-2">
                  <label class="flex items-center gap-2 text-xs">
                    <input v-model="persona.active" type="checkbox" />
                    active
                  </label>
                  <button class="rounded-lg border border-teal-300 px-3 py-2 text-xs font-bold text-teal-700 hover:bg-teal-50" @click="savePersona(persona)">
                    儲存 persona
                  </button>
                </div>
              </div>
            </div>
          </article>
        </section>
      </section>
    </main>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue';
import type { AdminSnapshotResponse, EventTask, ExperimentCondition, Persona } from '~/types';

definePageMeta({
  layout: false,
  name: 'admin',
});

const adminKey = ref('');
const snapshot = ref<AdminSnapshotResponse | null>(null);
const error = ref<string | null>(null);
const taskJson = ref<Record<string, string>>({});
const personaJson = ref<Record<string, string>>({});

onMounted(() => {
  adminKey.value = localStorage.getItem('histosphere_admin_key') || '';
});

const headers = () => ({ 'x-admin-key': adminKey.value });

const loadSnapshot = async () => {
  error.value = null;
  try {
    localStorage.setItem('histosphere_admin_key', adminKey.value);
    const data = await $fetch<AdminSnapshotResponse>('/api/admin/snapshot', { headers: headers() });
    snapshot.value = data;
    taskJson.value = {};
    personaJson.value = {};
    for (const event of data.events) {
      if (event.latest_task) {
        taskJson.value[event.latest_task.id] = JSON.stringify(event.latest_task.evaluation_payload || {}, null, 2);
      }
      for (const persona of event.personas) {
        personaJson.value[persona.id] = JSON.stringify(persona.prompt_profile || {}, null, 2);
      }
    }
  } catch (e: any) {
    error.value = e.data?.detail || '後台資料載入失敗，請確認 admin key。';
  }
};

const saveCondition = async (condition: ExperimentCondition) => {
  await $fetch(`/api/admin/conditions/${condition.id}`, {
    method: 'PATCH',
    headers: headers(),
    body: {
      label: condition.label,
      ebl_enabled: condition.ebl_enabled,
      roleplay_enabled: condition.roleplay_enabled,
      agent_mode: condition.roleplay_enabled ? 'persona' : 'generic',
      response_policy: condition.response_policy,
      description: condition.description,
      active: condition.active,
    },
  });
  await loadSnapshot();
};

const saveTask = async (task: EventTask) => {
  let evaluationPayload = {};
  try {
    evaluationPayload = JSON.parse(taskJson.value[task.id] || '{}');
  } catch {
    error.value = `Task ${task.id} 的 evaluation_payload 不是合法 JSON。`;
    return;
  }
  await $fetch(`/api/admin/tasks/${task.id}`, {
    method: 'PATCH',
    headers: headers(),
    body: {
      title: task.title,
      story_text: task.story_text,
      display_text: task.display_text,
      evaluation_payload: evaluationPayload,
      revision_state: 'teacher_modified',
    },
  });
  await loadSnapshot();
};

const savePersona = async (persona: Persona) => {
  let promptProfile = {};
  try {
    promptProfile = JSON.parse(personaJson.value[persona.id] || '{}');
  } catch {
    error.value = `Persona ${persona.name} 的 prompt_profile 不是合法 JSON。`;
    return;
  }
  await $fetch(`/api/admin/personas/${persona.id}`, {
    method: 'PATCH',
    headers: headers(),
    body: {
      name: persona.name,
      role: persona.role,
      biography: persona.biography,
      prompt_profile: promptProfile,
      active: persona.active,
      revision_state: 'teacher_modified',
    },
  });
  await loadSnapshot();
};
</script>
