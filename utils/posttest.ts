import type { PosttestDraftInput, PosttestResponse } from '~/types';

export const engagementQuestionIds = ['engagement_1', 'engagement_2', 'engagement_3'];
export const hatQuestionIds = ['hat_1', 'hat_2'];

export const isEngagementComplete = (answers: Record<string, number | null>) =>
  engagementQuestionIds.every((id) => Number.isInteger(answers[id]) && Number(answers[id]) >= 1 && Number(answers[id]) <= 5);

export const isHatComplete = (answers: Record<string, string>) =>
  hatQuestionIds.every((id) => typeof answers[id] === 'string' && answers[id].trim().length > 0 && answers[id].length <= 10000);

export const posttestDraftPayload = (
  response: PosttestResponse,
  engagement: Record<string, number | null>,
  hat: Record<string, string>,
): PosttestDraftInput => response.stage === 'engagement'
  ? { revision: response.revision, engagement_answers: Object.fromEntries(engagementQuestionIds
    .filter((id) => engagement[id] != null).map((id) => [id, engagement[id] as number])) }
  : { revision: response.revision, hat_answers: Object.fromEntries(hatQuestionIds.map((id) => [id, hat[id] || ''])) };

// Compare only the active stage's answers, not a changing server revision/timestamp.
export const posttestDraftSignature = (payload: PosttestDraftInput) =>
  JSON.stringify(payload.engagement_answers ?? payload.hat_answers ?? {});
