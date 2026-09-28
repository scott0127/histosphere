import type { ChatMessage, EventTask } from '~/types';

export interface TaskDiscussionProgress {
  status: 'corrected' | 'closed' | 'active';
  label: string;
  messageId?: string;
  linkLabel?: string;
}

export interface TaskDiscussionCompletion extends TaskDiscussionProgress {
  questionId: string;
  questionIndex: number;
}

const isDeliveredMessage = (message: ChatMessage) => {
  if (!message.id || message.id.startsWith('local-')) return false;
  const metadata = message.metadata || {};
  return [message.operation_status, metadata.generation_status, metadata.response_status]
    .every((status) => !status || status === 'completed');
};

// 完成狀態只取自已送達的後端紀錄，不以原始評分或人物台詞推測。
export const getTaskDiscussionCompletions = (
  task: EventTask,
  history: ChatMessage[],
): TaskDiscussionCompletion[] => {
  const questions = task.evaluation_payload.questions || [];
  const learnerByResponse = new Map<string, ChatMessage>();
  for (const message of history) {
    const responseId = message.metadata?.response_message_id;
    if (message.speaker_type === 'learner' && isDeliveredMessage(message) && typeof responseId === 'string') {
      learnerByResponse.set(responseId, message);
    }
  }

  const completions: TaskDiscussionCompletion[] = [];
  const recorded = new Set<string>();
  for (let index = history.length - 1; index >= 0; index -= 1) {
    const message = history[index]!;
    if (message.speaker_type === 'learner' || !isDeliveredMessage(message)) continue;
    const metadata = message.metadata || {};
    if ((metadata.answer_delivery as { state_held?: boolean } | undefined)?.state_held) continue;
    const questionIndex = questions.findIndex((question) => question.id === metadata.target_question_id);
    if (questionIndex < 0) continue;
    const questionId = questions[questionIndex]!.id;
    if (recorded.has(questionId)) continue;
    const status = metadata.completion_status;
    const corrected = status === 'resolved' || status === 'feedback_completed' || status === 'corrected_after_feedback';
    const closed = status === 'unresolved_after_max_support' || status === 'complete';
    if (!corrected && !closed) continue;
    recorded.add(questionId);
    // 只有明確對應此回覆的學生訊息才用作修正連結；舊紀錄回到 AI 的確認。
    const learner = corrected ? learnerByResponse.get(message.id!) : undefined;
    completions.push({
      questionId,
      questionIndex,
      status: corrected ? 'corrected' : 'closed',
      label: corrected ? '已完成修正' : '已結束討論',
      messageId: learner?.id || message.id,
      linkLabel: corrected ? '查看修正對話' : '查看討論結尾',
    });
  }
  return completions;
};
