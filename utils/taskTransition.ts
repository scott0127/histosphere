export type TaskTransitionPhase = {
  label: string;
  detail: string;
};

export const formatTaskTransitionEra = (
  eventName: string,
  startYear?: number | null,
  endYear?: number | null,
) => {
  if (startYear && endYear) {
    return startYear === endYear ? `${startYear} 年` : `${startYear}–${endYear} 年`;
  }
  if (startYear) return `${startYear} 年`;
  if (endYear) return `${endYear} 年前後`;
  return `「${eventName || '這段歷史'}」`;
};

export const taskTransitionPhase = (elapsedSeconds: number): TaskTransitionPhase => {
  if (elapsedSeconds < 4) {
    return {
      label: '正在保存你的作答',
      detail: '答案已送出，系統正在建立本次活動紀錄。',
    };
  }
  if (elapsedSeconds < 12) {
    return {
      label: '正在分析作答與歷史脈絡',
      detail: 'AI 正在整理你剛才的判斷，準備後續討論。',
    };
  }
  if (elapsedSeconds < 30) {
    return {
      label: '正在準備歷史對話',
      detail: '人物、事件脈絡與活動模式正在載入。',
    };
  }
  return {
    label: '模型仍在推論',
    detail: '系統正在等待回應或嘗試備援來源，請保留此頁面。',
  };
};
