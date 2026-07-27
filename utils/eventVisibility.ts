export type EventIntroductionMode = 'admin' | 'learner';

/**
 * 事件介紹可能在正式作答前形成提示或額外教學，因此只供 Admin 管理視角查看。
 * Admin testmode 使用 learner mode，會與正式受測者看到相同內容。
 */
export const shouldShowEventIntroduction = (mode: EventIntroductionMode) => {
  return mode === 'admin';
};
