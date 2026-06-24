// 歷史事件在首頁與詳情彈窗中的純呈現工具。
// 這裡只處理 label、時間格式、線稿圖等 UI 轉換，不接觸後端資料流程。
import type { EventWithPersonas } from '~/types';

// 依事件名稱給予簡短歷史檔案分類，作為卡片上的視覺標籤。
export const eventMotif = (event: EventWithPersonas) => {
  const name = event.canonical_name;
  if (name.includes('法國') || name.includes('革命')) return { label: 'Revolution archive' };
  if (name.includes('文藝復興')) return { label: 'Renaissance archive' };
  if (name.includes('登陸') || name.includes('戰')) return { label: 'Wartime archive' };
  if (name.includes('明治') || name.includes('日本')) return { label: 'Modernization archive' };
  return { label: 'Historical archive' };
};

// 依事件名稱對應背景線稿圖片；實際 source 仍以資料庫與後端為準。
export const getEventSketch = (event: EventWithPersonas) => {
  const name = event.canonical_name;
  if (name.includes('法國') || name.includes('革命')) return '/images/history/french_revolution.png';
  if (name.includes('文藝復興')) return '/images/history/renaissance_florence.png';
  if (name.includes('日本') || name.includes('明治')) return '/images/history/ancient_japan.png';
  if (name.includes('金字塔') || name.includes('埃及')) return '/images/history/egyptian_pyramids.png';
  if (name.includes('希臘') || name.includes('巴特農')) return '/images/history/greek_parthenon.png';
  if (name.includes('羅馬') || name.includes('競技場')) return '/images/history/roman_colosseum.png';
  if (name.includes('維京')) return '/images/history/viking_ship.png';
  if (name.includes('萬里長城') || name.includes('秦朝')) return '/images/history/great_wall_china.png';
  return '/images/neoclassical_building.png';
};

// 格式化事件時間，避免每個元件重複處理 start/end/century fallback。
export const formatYears = (event: EventWithPersonas) => {
  if (event.start_year && event.end_year) return `${event.start_year} - ${event.end_year}`;
  if (event.start_year) return `${event.start_year}`;
  if (event.century) return `${event.century} 世紀`;
  return '時間待補';
};
