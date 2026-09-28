import { onMounted, watch } from 'vue';
import { DEFAULT_USD_TWD_ESTIMATE, validEstimateRate } from '~/utils/adminLlmUsage';

export const useAdminCostEstimate = () => {
  const rate = useState<number | string>('admin-usd-twd-estimate', () => DEFAULT_USD_TWD_ESTIMATE);
  const loaded = useState('admin-usd-twd-loaded', () => false);
  onMounted(() => {
    if (loaded.value) return;
    loaded.value = true;
    try {
      const saved = Number(localStorage.getItem('histosphere:usd-twd-estimate'));
      if (validEstimateRate(saved)) rate.value = saved;
    } catch { /* Storage may be disabled; keep the visible estimate. */ }
  });
  watch(rate, (value) => {
    if (!validEstimateRate(value)) return;
    try { localStorage.setItem('histosphere:usd-twd-estimate', String(value)); } catch { /* Optional preference. */ }
  });
  return { rate };
};
