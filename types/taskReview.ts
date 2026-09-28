import type { ChatMessage, EventTask, ExperimentCondition, ExperimentSession, HistoricalEvent, TaskAttempt, TaskMaterial, TaskQuestion } from '~/types';

export interface TaskReviewQuestion {
  question_id: string;
  reviewed: boolean;
  answer_correct: boolean;
  reasoning_correct: boolean;
  answer_feedback: string;
  reasoning_feedback: string;
  override_reason: string;
}

export interface TaskReviewAttempt extends Omit<TaskAttempt, 'status'> {
  status: 'in_progress' | 'processing' | 'awaiting_review' | 'preparing_chat' | 'ready' | 'submitted' | 'failed';
  ai_judgement_payload: Record<string, unknown>;
  review_payload: {
    question_results?: TaskReviewQuestion[];
    reviewer_id?: string;
    approved_at?: string;
  };
  review_version: number;
  pipeline_error?: { stage?: string; message?: string; detail?: string };
}

export interface AdminMonitorSnapshot {
  participant_code: string;
  session: ExperimentSession;
  event: HistoricalEvent;
  condition?: ExperimentCondition | null;
  task?: EventTask | null;
  attempt?: TaskReviewAttempt | null;
  stage: string;
  conversation?: { id: string } | null;
  messages: ChatMessage[];
  posttest?: { stage?: string; status?: string; completed_at?: string; updated_at?: string } | null;
  updated_at: string;
}

export interface ReviewQuestionRow {
  question: TaskQuestion;
  text: string;
  answer: unknown;
  rationale: string;
  ai: { answer_correct?: boolean; reasoning_correct?: boolean; answer_feedback?: string; reasoning_feedback?: string };
}

export interface ReviewReading {
  introduction: string;
  materials: TaskMaterial[];
  fullText: string;
}
