<template>
  <!--
    2x2 實驗活動入口：
    Baseline / 錯誤中學習 / 沉浸式角色扮演 / 兩者結合。
    注意：這裡只切換活動 session 與 chat policy，不複製事件素材。
  -->
  <section class="border-t border-[var(--admin-border)] bg-[var(--admin-page)] p-4">
    <div class="mb-4 flex flex-col gap-1 sm:flex-row sm:items-end sm:justify-between">
      <div>
        <p class="text-xs font-black uppercase tracking-[0.2em] text-[var(--admin-coffee)]">學習活動</p>
        <h3 class="mt-1 font-serif text-2xl font-black text-[var(--admin-text)]">選擇學習活動</h3>
      </div>
      <p class="text-xs font-bold leading-6 text-[var(--admin-coffee)]">
        完成 Error-Elicitation Task 後進入對話
      </p>
    </div>

    <div v-if="sortedConditions.length" class="grid gap-3 md:grid-cols-2">
      <button
        v-for="condition in sortedConditions"
        :key="condition.id"
        type="button"
        :class="activityButtonClass(condition)"
        @mouseenter="animateActivityHover($event, true)"
        @mouseleave="animateActivityHover($event, false)"
        @mousemove="onButtonMouseMove"
        @click="emit('start', condition)"
      >
        <span class="gold-shine" aria-hidden="true"></span>
        <span class="gold-line" aria-hidden="true"></span>
        <span v-if="activityVisual(condition) === 'roleplay'" class="gold-motif gold-napoleon" aria-hidden="true">
          <span class="motif-foil"></span>
          <span class="motif-glass"></span>
        </span>
        <span v-else-if="activityVisual(condition) === 'combo'" class="gold-motif gold-factory" aria-hidden="true">
          <span class="motif-foil"></span>
          <span class="motif-glass"></span>
        </span>
        <span v-else-if="activityVisual(condition) === 'baseline'" class="gold-motif gold-baseline" aria-hidden="true">
          <span class="motif-foil"></span>
          <span class="motif-glass"></span>
        </span>
        <span v-else-if="activityVisual(condition) === 'error'" class="gold-motif gold-error-svg" aria-hidden="true">
          <svg class="error-svg" viewBox="0 0 100 24" preserveAspectRatio="xMidYMid meet">
            <defs>
              <linearGradient id="error-gold" x1="0%" y1="0%" x2="100%" y2="100%">
                <stop offset="0%" stop-color="#111111" />
                <stop offset="50%" stop-color="#d4af37" />
                <stop offset="100%" stop-color="#e0e0e0" />
              </linearGradient>
              <filter id="error-glow" x="-20%" y="-20%" width="140%" height="140%">
                <feGaussianBlur stdDeviation="0.4" result="blur" />
                <feComposite in="SourceGraphic" in2="blur" operator="over" />
              </filter>
            </defs>
            <g fill="url(#error-gold)" filter="url(#error-glow)">
              <path class="svg-morph-e" d="M 3 20 L 5 19 V 5 L 3 4 H 17 L 16 7 H 14 L 14 6 H 8 V 11 H 13 V 13 H 8 V 19 H 15 V 17 H 17 L 16 21 H 3 Z" transform="translate(-2, 0)" />
              <path class="svg-morph-b" d="M 3 21 L 5 20 V 4 L 3 3 H 12 C 17 3, 17 11, 13 11.5 C 18 12, 18 20, 12 21 H 3 Z M 8 5 V 11 H 11 C 13 11, 13 5, 11 5 Z M 8 13 V 19 H 11 C 14 19, 14 13, 11 13 Z" transform="translate(22, 0)" />
              <path class="svg-morph-l" d="M 3 20 L 5 19 V 5 L 3 4 H 11 L 9 5 V 19 H 16 V 16 H 18 L 17 21 H 3 Z" transform="translate(46, 0)" />
              <path class="icon-error" d="M22.12 21.46L2.4 1.73L1.12 3L4 5.87L2.34 8.73c-.13.22-.07.49.12.64L4.57 11c-.04.34-.07.67-.07 1s.03.65.07.97l-2.11 1.66c-.19.15-.25.42-.12.64l2 3.46c.12.22.39.3.61.22l2.49-1.01c.52.4 1.06.74 1.69.99l.37 2.65c.04.24.25.42.5.42h4c.25 0 .46-.18.5-.42l.37-2.65c.51-.21.96-.48 1.39-.79l4.59 4.59zM12 15.5c-1.93 0-3.5-1.57-3.5-3.5c0-.5.12-.92.29-1.33l4.54 4.54c-.41.18-.83.29-1.33.29m-.26-6.97L8.56 5.35c.19-.1.37-.2.57-.28l.37-2.65c.04-.24.25-.42.5-.42h4c.25 0 .46.18.5.42l.37 2.65c.63.25 1.17.59 1.69.98l2.49-1c.22-.09.49 0 .61.22l2 3.46c.12.22.07.49-.12.64L19.43 11c.04.34.07.67.07 1s-.03.65-.07.97l2.11 1.66c.19.15.24.42.12.64l-1.16 2.02l-5.03-5.03c.03-.08.03-.17.03-.26c0-1.93-1.57-3.5-3.5-3.5c-.09 0-.17 0-.26.03" opacity="0" />
              <path class="icon-brain" d="M13 8.58c.78 0 1.44.61 1.44 1.42s-.66 1.44-1.44 1.44s-1.42-.66-1.42-1.44s.61-1.42 1.42-1.42M13 3c3.88 0 7 3.14 7 7c0 2.8-1.63 5.19-4 6.31V21H9v-3H8c-1.11 0-2-.89-2-2v-3H4.5c-.42 0-.66-.5-.42-.81L6 9.66A7.003 7.003 0 0 1 13 3m3 7c0-.16 0-.25-.06-.39l.89-.66c.05-.04.09-.18.05-.28l-.8-1.36c-.05-.09-.19-.14-.28-.09l-.99.42c-.18-.19-.42-.33-.65-.42L14 6.19c-.03-.14-.08-.19-.22-.19h-1.59c-.1 0-.19.05-.19.19l-.14 1.03c-.23.09-.47.23-.66.42l-1.03-.42c-.09-.05-.17 0-.23.09l-.8 1.36c-.05.14-.05.24.05.28l.84.66c0 .14-.03.28-.03.39c0 .13.03.27.03.41l-.84.65c-.1.05-.1.14-.05.24l.8 1.4c.06.1.14.1.23.1l.99-.43c.23.19.42.29.7.38l.14 1.08c0 .09.09.17.19.17h1.59c.14 0 .19-.08.22-.17l.16-1.08c.23-.09.47-.19.65-.37l.99.42c.09 0 .23 0 .28-.1l.8-1.4c.04-.1 0-.19-.05-.24l-.83-.65z" opacity="0" />
              <path class="icon-fix" d="M12 15.5A3.5 3.5 0 0 1 8.5 12A3.5 3.5 0 0 1 12 8.5a3.5 3.5 0 0 1 3.5 3.5a3.5 3.5 0 0 1-3.5 3.5m7.43-2.53c.04-.32.07-.64.07-.97s-.03-.66-.07-1l2.11-1.63c.19-.15.24-.42.12-.64l-2-3.46c-.12-.22-.39-.31-.61-.22l-2.49 1c-.52-.39-1.06-.73-1.69-.98l-.37-2.65A.506.506 0 0 0 14 2h-4c-.25 0-.46.18-.5.42l-.37 2.65c-.63.25-1.17.59-1.69.98l-2.49-1c-.22-.09-.49 0-.61.22l-2 3.46c-.13.22-.07.49.12.64L4.57 11c-.04.34-.07.67-.07 1s.03.65.07.97l-2.11 1.66c-.19.15-.25.42-.12.64l2 3.46c.12.22.39.3.61.22l2.49-1.01c.52.4 1.06.74 1.69.99l.37 2.65c.04.24.25.42.5.42h4c.25 0 .46-.18.5-.42l.37-2.65c.63-.26 1.17-.59 1.69-.99l2.49 1.01c.22.08.49 0 .61-.22l2-3.46c.12-.22.07-.49-.12-.64z M 16 16 l 1.5 1.5 l 3.5 -3.5 l 1.5 1.5 l -5 5 l -3 -3 z" opacity="0" />
            </g>
          </svg>
        </span>

        <div class="relative z-10 flex h-full items-start justify-between gap-4 rounded-[8px] border border-[var(--admin-border-soft)] bg-[rgba(255,253,248,0.86)] p-5">
          <div>
            <p class="text-lg font-black leading-snug text-[var(--admin-text)]">{{ conditionTitle(condition) }}</p>
            <p v-if="mode === 'admin'" class="mt-2 max-w-[18rem] text-xs font-bold leading-5 text-[var(--admin-copy)]">
              {{ conditionHint(condition) }}
            </p>
          </div>
          <span :class="progressBadgeClass(condition.condition_key)">
            {{ progressLabel(condition.condition_key) }}
          </span>
        </div>
      </button>
    </div>

    <div v-else class="rounded-[10px] border border-dashed border-[var(--admin-border)] bg-[var(--admin-surface-muted)] p-6 text-center text-sm font-semibold text-[var(--admin-copy)] shadow-sm">
      目前沒有可開始的活動；可能尚未分派模式，或已完成全部分派順序。
    </div>
  </section>
</template>

<script setup lang="ts">
// ActivityConditionGrid 封裝 2x2 活動按鈕與自訂 hover 動畫。
// 資料與導頁由 page 傳入/接收；這裡只負責排序、標籤、狀態與視覺互動。
import { computed } from 'vue';
import type { ConditionKey, ExperimentCondition, UserProgressStatus } from '~/types';
import { experimentConditionCode, sortExperimentConditions } from '~/utils/experimentConditions';

type LocalConditionProgress = {
  status: 'not_started' | UserProgressStatus;
  sessionId?: string;
  taskId?: string;
  attemptId?: string;
  conversationId?: string;
  updatedAt: string;
};

const props = defineProps<{
  conditions: ExperimentCondition[];
  progressByCondition: Partial<Record<ConditionKey, LocalConditionProgress>>;
  mode: 'admin' | 'learner';
}>();

const emit = defineEmits<{
  (event: 'start', condition: ExperimentCondition): void;
}>();

// 固定活動排序，確保研究流程與 UI 呈現一致，不受後端回傳順序影響。
const sortedConditions = computed(() => {
  return sortExperimentConditions(props.conditions);
});

// 顯示受測者可理解的活動名稱，避免揭露內部實驗設定。
const mode = computed(() => props.mode);

const conditionTitle = (condition: ExperimentCondition) => {
  if (props.mode === 'learner') {
    const code = experimentConditionCode(condition);
    return code ? `${code}模式` : '活動代號未設定';
  }
  if (condition.ebl_enabled && condition.roleplay_enabled) return '沉浸式角色扮演 + 錯誤中學習';
  if (condition.ebl_enabled) return '錯誤中學習';
  if (condition.roleplay_enabled) return '沉浸式角色扮演';
  return 'Baseline';
};

// 給受測者看的短提示，不揭露 prompt policy 細節。
const conditionHint = (condition: ExperimentCondition) => {
  if (condition.ebl_enabled && condition.roleplay_enabled) return '以歷史人物對話，引導修正任務中的理解。';
  if (condition.ebl_enabled) return '以一般 tutor 對話，引導檢查任務中的判斷。';
  if (condition.roleplay_enabled) return '以歷史人物語氣展開事件對話。';
  return '以一般 AI 對話回應事件問題。';
};

// 取得目前 condition 的本機進度。
const progressFor = (conditionKey: ConditionKey) => props.progressByCondition[conditionKey] || null;

// 轉換 condition 進度為短標籤。
const progressLabel = (conditionKey: ConditionKey) => {
  const progress = progressFor(conditionKey);
  if (!progress) return '未開始';
  if (progress.status === 'archived') return '已封存';
  if (progress.status === 'completed') return '已完成';
  if (progress.status === 'chat_started') return '進行中';
  if (progress.status === 'task_submitted') return '已送出';
  if (progress.status === 'task_draft') return '草稿';
  return '進行中';
};

// condition 進度標籤樣式。
const progressBadgeClass = (conditionKey: ConditionKey) => {
  const progress = progressFor(conditionKey);
  const base = 'shrink-0 rounded-full px-3 py-1 text-xs font-black';
  if (!progress) return `${base} bg-[var(--admin-coffee-soft)] text-[var(--admin-coffee)]`;
  if (progress.status === 'completed') return `${base} bg-[#dcebd6] text-[#3f6d4a]`;
  if (progress.status === 'chat_started') return `${base} bg-[#eadfcf] text-[var(--admin-coffee)]`;
  if (progress.status === 'task_submitted') return `${base} bg-[#e4dfd6] text-[var(--admin-coffee)]`;
  if (progress.status === 'task_draft') return `${base} bg-[var(--admin-coffee-soft)] text-[var(--admin-copy)]`;
  if (progress.status === 'archived') return `${base} bg-[var(--admin-surface-sunken)] text-[var(--admin-muted)]`;
  return `${base} bg-[var(--admin-surface-sunken)] text-[var(--admin-copy)]`;
};

// 依 condition 取得按鈕外觀 class。
const activityButtonClass = (condition: ExperimentCondition) => [
  'activity-button group relative overflow-hidden rounded-xl border p-1.5 text-left',
  'transition-[color,background-color,border-color,box-shadow] duration-300',
  'border-[var(--admin-border)] bg-[var(--admin-surface)] shadow-md hover:-translate-y-0.5 hover:border-[var(--admin-line)] hover:shadow-lg',
  `activity-${activityVisual(condition)}`,
];

// 依 condition 決定 hover 時使用的燙金圖像語言。
const activityVisual = (condition: ExperimentCondition) => {
  if (condition.ebl_enabled && condition.roleplay_enabled) return 'combo';
  if (condition.ebl_enabled) return 'error';
  if (condition.roleplay_enabled) return 'roleplay';
  return 'baseline';
};

let gsapLoader: Promise<any> | null = null;

// GSAP 與 MorphSVG 只在 hover 時 lazy-load，避免首頁第一次載入就增加動畫成本。
// 這段包含目前自訂的 baseline/error/role-play 視覺語言，請勿在未確認前刪除。
const loadGsap = async () => {
  if (!gsapLoader) {
    gsapLoader = import('gsap').then(async (m) => {
      const gsapInst = m.default || m.gsap || m;
      const { MorphSVGPlugin } = await import('gsap/MorphSVGPlugin');
      gsapInst.registerPlugin(MorphSVGPlugin);
      if (import.meta.client) {
        // @ts-ignore - MorphSVGPlugin 沒有掛在 window 型別上，但動畫回退時會使用。
        window.MorphSVGPlugin = MorphSVGPlugin;
      }
      return gsapInst;
    });
  }
  const gsapInstance = await gsapLoader;
  return { gsap: gsapInstance };
};

// 活動按鈕 hover 時用燙金浮雕感提示活動類型，不用文字揭露實驗機制。
const animateActivityHover = async (event: MouseEvent, entering: boolean) => {
  if (!import.meta.client) return;
  const button = event.currentTarget as HTMLElement | null;
  if (!button) return;

  const { gsap } = await loadGsap();
  const shine = button.querySelector('.gold-shine');
  const motif = button.querySelector('.gold-motif');
  const line = button.querySelector('.gold-line');

  const svgE = button.querySelector('.svg-morph-e');
  const svgB = button.querySelector('.svg-morph-b');
  const svgL = button.querySelector('.svg-morph-l');

  gsap.killTweensOf([button, shine, motif, line, svgE, svgB, svgL]);

  if (!entering) {
    gsap.to(button, { rotateX: 0, rotateY: 0, duration: 0.6, ease: 'power2.out' });
    if (shine) gsap.to(shine, { xPercent: -130, opacity: 0, duration: 0.24, ease: 'power2.out' });
    if (motif) gsap.to(motif, { opacity: 0, scale: 0.98, rotate: 0, x: 0, y: 0, duration: 0.45, ease: 'power2.out' });
    if (line) gsap.to(line, { scaleX: 0, opacity: 0, duration: 0.2, ease: 'power2.out' });

    [svgE, svgB, svgL].forEach((svgPath) => {
      if (!svgPath) return;
      if (!svgPath.getAttribute('data-original')) svgPath.setAttribute('data-original', svgPath.getAttribute('d')!);
      const originalD = svgPath.getAttribute('data-original')!;
      gsap.to(svgPath, {
        morphSVG: originalD,
        duration: 0.5,
        ease: 'power2.out',
        overwrite: 'auto',
      });
    });
    return;
  }

  const tl = gsap.timeline({ defaults: { ease: 'power3.out' } });
  if (shine) tl.to(shine, { xPercent: 130, opacity: 1, duration: 0.75 }, 0);
  if (line) tl.fromTo(line, { scaleX: 0, opacity: 0 }, { scaleX: 1, opacity: 0.95, duration: 0.5 }, 0.06);

  if (motif) {
    if (!svgE) {
      tl.fromTo(motif, { opacity: 0, scale: 0.98, rotate: -0.5 }, { opacity: 1, scale: 1.015, rotate: 0, duration: 0.8 }, 0);
    } else {
      const iconError = button.querySelector('.icon-error');
      const iconBrain = button.querySelector('.icon-brain');
      const iconFix = button.querySelector('.icon-fix');

      if (!svgE.getAttribute('data-original')) svgE.setAttribute('data-original', svgE.getAttribute('d')!);
      if (svgB && !svgB.getAttribute('data-original')) svgB.setAttribute('data-original', svgB.getAttribute('d')!);
      if (svgL && !svgL.getAttribute('data-original')) svgL.setAttribute('data-original', svgL.getAttribute('d')!);

      tl.fromTo(motif, { opacity: 0, scale: 0.98 }, { opacity: 1, scale: 1.015, duration: 0.8 }, 0);

      const setupMorph = (pathEl: Element | null, targetIcon: Element | null, delay: number) => {
        if (!pathEl || !targetIcon) return;
        gsap.to(pathEl, {
          morphSVG: targetIcon,
          duration: 1.5,
          ease: 'power1.inOut',
          yoyo: true,
          repeat: -1,
          repeatDelay: 2.5,
          delay,
          overwrite: 'auto',
        });
      };

      setupMorph(svgE, iconError, 0.1);
      setupMorph(svgB, iconBrain, 0.15);
      setupMorph(svgL, iconFix, 0.2);
    }
  }
};

// 滑鼠移動時讓按鈕與燙金 motif 產生輕微 3D tilt。
const onButtonMouseMove = async (event: MouseEvent) => {
  if (!import.meta.client) return;
  const button = event.currentTarget as HTMLElement | null;
  if (!button) return;

  const rect = button.getBoundingClientRect();
  const x = event.clientX - rect.left;
  const y = event.clientY - rect.top;
  const centerX = rect.width / 2;
  const centerY = rect.height / 2;
  const moveX = (x - centerX) / centerX;
  const moveY = (y - centerY) / centerY;

  const { gsap } = await loadGsap();

  gsap.to(button, {
    rotateY: moveX * 4,
    rotateX: -moveY * 4,
    transformPerspective: 1000,
    transformOrigin: 'center center',
    duration: 0.4,
    ease: 'power2.out',
    overwrite: 'auto',
  });

  const motif = button.querySelector('.gold-motif');
  if (motif) {
    gsap.to(motif, {
      x: moveX * -12,
      y: moveY * -12,
      duration: 0.4,
      ease: 'power2.out',
      overwrite: 'auto',
    });
  }
};
</script>

<style scoped>
.activity-button {
  min-height: 124px;
  isolation: isolate;
  background-color: var(--admin-surface);
  background-image:
    linear-gradient(135deg, rgba(255, 255, 255, 0.48), transparent 40%),
    radial-gradient(circle at 82% 18%, rgba(168, 141, 123, 0.14), transparent 30%);
}

.activity-button::before {
  position: absolute;
  inset: 0;
  z-index: 0;
  content: "";
  background:
    radial-gradient(circle at 82% 28%, rgba(168, 141, 123, 0.18), transparent 32%),
    linear-gradient(135deg, rgba(255, 253, 248, 0.84), rgba(237, 227, 218, 0.32));
  opacity: 0;
  transition: opacity 180ms ease;
}

.activity-button:hover::before {
  opacity: 1;
}

.activity-button:hover {
  box-shadow:
    5px 6px 0 rgba(47, 41, 36, 0.14),
    inset 0 0 0 1px rgba(123, 93, 75, 0.28),
    inset 0 0 28px rgba(168, 141, 123, 0.12);
}

.activity-button:hover .gold-shine {
  animation: mirror-sweep 0.85s ease-out both;
}

.activity-button:hover .gold-motif {
  opacity: 1;
  transform: scale(1.05);
}

.activity-button:hover .gold-line {
  opacity: 0.95;
  transform: scaleX(1);
}

.gold-shine {
  position: absolute;
  inset: -42% auto -42% -48%;
  z-index: 1;
  width: 34%;
  transform: translateX(-150%) skewX(-20deg);
  opacity: 0;
  background:
    linear-gradient(
      90deg,
      transparent 0%,
      rgba(255, 255, 255, 0.08) 24%,
      rgba(255, 255, 255, 0.68) 42%,
      rgba(255, 238, 176, 0.82) 50%,
      rgba(255, 255, 255, 0.38) 58%,
      rgba(255, 255, 255, 0.08) 72%,
      transparent 100%
    );
  filter: blur(0.4px);
  mix-blend-mode: screen;
}

.gold-shine::after {
  position: absolute;
  inset: 0 42%;
  content: "";
  background: rgba(255, 255, 255, 0.74);
  box-shadow: 0 0 18px rgba(255, 245, 196, 0.65);
}

.gold-motif {
  position: absolute;
  right: 28px;
  bottom: -16px;
  z-index: 1;
  width: 170px;
  height: 110px;
  opacity: 0;
  transform-origin: 70% 70%;
  pointer-events: none;
  transition: opacity 180ms ease, transform 180ms ease;
}

.motif-foil,
.motif-glass {
  position: absolute;
  inset: 0;
  content: "";
  mask-position: center;
  mask-repeat: no-repeat;
  mask-size: contain;
  -webkit-mask-position: center;
  -webkit-mask-repeat: no-repeat;
  -webkit-mask-size: contain;
}

.motif-foil {
  background:
    radial-gradient(circle at 34% 12%, rgba(255, 255, 230, 1), transparent 25%),
    linear-gradient(
      135deg,
      rgba(100, 60, 10, 0.95) 0%,
      rgba(255, 215, 90, 1) 25%,
      rgba(150, 85, 15, 0.95) 48%,
      rgba(255, 240, 150, 1) 62%,
      rgba(120, 65, 15, 0.95) 100%
    );
  filter:
    drop-shadow(0 1px 0 rgba(255, 249, 211, 0.9))
    drop-shadow(0 8px 14px rgba(50, 30, 10, 0.4));
  opacity: 0.95;
}

.motif-glass {
  opacity: 0;
  transform: translateX(-72%) skewX(-18deg);
  background:
    linear-gradient(
      90deg,
      transparent 0%,
      rgba(255, 255, 255, 0.04) 28%,
      rgba(255, 255, 255, 0.9) 45%,
      rgba(255, 242, 178, 0.86) 53%,
      rgba(255, 255, 255, 0.18) 68%,
      transparent 100%
    );
  mix-blend-mode: screen;
  filter: blur(0.35px);
  transition: opacity 180ms ease, transform 760ms cubic-bezier(0.2, 0.8, 0.2, 1);
}

.activity-button:hover .motif-glass {
  opacity: 1;
  transform: translateX(74%) skewX(-18deg);
}

.gold-line {
  position: absolute;
  right: 24px;
  bottom: 18px;
  z-index: 1;
  width: min(46%, 220px);
  height: 2px;
  transform: scaleX(0);
  transform-origin: right center;
  opacity: 0;
  background: linear-gradient(90deg, transparent, #d29b32, #fff0a6);
  box-shadow: 0 0 16px rgba(205, 157, 64, 0.58);
}

@keyframes mirror-sweep {
  0% {
    opacity: 0;
    transform: translateX(-150%) skewX(-20deg);
  }
  20% {
    opacity: 1;
  }
  100% {
    opacity: 0.42;
    transform: translateX(360%) skewX(-20deg);
  }
}

.gold-napoleon {
  left: 0;
  right: 0;
  bottom: 0;
  width: 100%;
  height: 100%;
  transform-origin: center bottom;
}

.gold-napoleon .motif-foil,
.gold-napoleon .motif-glass {
  mask-image: url("/images/activity-motifs/napoleon-epic-mask.png");
  -webkit-mask-image: url("/images/activity-motifs/napoleon-epic-mask.png");
  mask-size: cover;
  -webkit-mask-size: cover;
  mask-position: 85% bottom;
  -webkit-mask-position: 85% bottom;
  mask-repeat: no-repeat;
  -webkit-mask-repeat: no-repeat;
}

.gold-factory {
  left: 0;
  right: 0;
  bottom: 0;
  width: 100%;
  height: 100%;
  transform-origin: center bottom;
}

.gold-factory .motif-foil,
.gold-factory .motif-glass {
  mask-image: url("/images/activity-motifs/industrial-mask.png");
  -webkit-mask-image: url("/images/activity-motifs/industrial-mask.png");
  mask-size: cover;
  -webkit-mask-size: cover;
  mask-position: right bottom;
  -webkit-mask-position: right bottom;
  mask-repeat: no-repeat;
  -webkit-mask-repeat: no-repeat;
}

.gold-baseline {
  left: 0;
  right: 0;
  bottom: 0;
  width: 100%;
  height: 100%;
  transform-origin: center bottom;
}

.gold-baseline .motif-foil,
.gold-baseline .motif-glass {
  mask-image: url("/images/activity-motifs/baseline-mask.png");
  -webkit-mask-image: url("/images/activity-motifs/baseline-mask.png");
  mask-size: cover;
  -webkit-mask-size: cover;
  mask-position: center center;
  -webkit-mask-position: center center;
  mask-repeat: no-repeat;
  -webkit-mask-repeat: no-repeat;
}

.gold-error-svg {
  right: 15px;
  bottom: 0px;
  width: 200px;
  height: 120px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.gold-error-svg .error-svg {
  width: 100%;
  height: 100%;
  overflow: visible;
}

.activity-combo .motif-foil {
  opacity: 0.95;
}
</style>
