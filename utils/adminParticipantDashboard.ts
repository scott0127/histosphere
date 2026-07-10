import type { AdminAuthUserSummary, AdminSnapshotResponse, ExperimentSession, Participant } from '~/types';
import {
  experimentConditionCodeByKey,
  experimentConditionCodes,
  experimentConditionLabels,
} from '~/utils/experimentConditions';

export type ParticipantStage = 'not_started' | 'task' | 'chat' | 'completed';

export type ParticipantConditionProgress = {
  code: string;
  label: string;
  stage: ParticipantStage;
  sessionId?: string;
  updatedAt?: string;
};

export type ParticipantDashboardRow = {
  participant: Participant;
  authUser: AdminAuthUserSummary | null;
  isBound: boolean;
  assignedConditions: Array<{ code: string; label: string }>;
  conditionProgress: ParticipantConditionProgress[];
  currentStage: ParticipantStage;
  updatedAt?: string;
};

export const participantConditionLabels: Record<string, string> = experimentConditionLabels;

export const participantStageLabels: Record<ParticipantStage, string> = {
  not_started: '未開始',
  task: 'Task',
  chat: 'Chat',
  completed: '完成',
};

const normalizeConditionCodes = (codes: string[]) => {
  const unique = new Set(codes.filter((code) => participantConditionLabels[code]));
  return experimentConditionCodes.filter((code) => unique.has(code));
};

export const conditionDisplayLabel = (code: string) => {
  return `${code} ${participantConditionLabels[code] || 'Unknown'}`;
};

export const sessionStage = (session?: ExperimentSession | null): ParticipantStage => {
  if (!session) return 'not_started';
  if (session.status === 'completed' || session.status === 'archived') return 'completed';
  if (session.status === 'conversation_started') return 'chat';
  return 'task';
};

const latestSession = (sessions: ExperimentSession[]) => {
  return [...sessions].sort((a, b) => Date.parse(b.updated_at) - Date.parse(a.updated_at))[0] || null;
};

export const buildParticipantDashboardRows = (
  snapshot: AdminSnapshotResponse,
  authUsers: AdminAuthUserSummary[],
) => {
  const authUsersById = new Map(authUsers.map((user) => [user.id, user]));
  const sessionsByUserAndCode = new Map<string, ExperimentSession[]>();

  for (const session of snapshot.sessions) {
    if (!session.user_id) continue;
    const code = experimentConditionCodeByKey[session.condition_key_snapshot];
    if (!code) continue;
    const key = `${session.user_id}:${code}`;
    sessionsByUserAndCode.set(key, [...(sessionsByUserAndCode.get(key) || []), session]);
  }

  return [...snapshot.participants]
    .sort((a, b) => a.code.localeCompare(b.code))
    .map<ParticipantDashboardRow>((participant) => {
      const assignedCodes = normalizeConditionCodes(participant.condition_list || []);
      const authUser = participant.auth_user_id ? authUsersById.get(participant.auth_user_id) || null : null;
      const conditionProgress = assignedCodes.map((code) => {
        const session = participant.auth_user_id
          ? latestSession(sessionsByUserAndCode.get(`${participant.auth_user_id}:${code}`) || [])
          : null;
        return {
          code,
          label: participantConditionLabels[code],
          stage: sessionStage(session),
          sessionId: session?.id,
          updatedAt: session?.updated_at,
        };
      });
      const stages = conditionProgress.map((item) => item.stage);
      const currentStage: ParticipantStage = stages.length > 0 && stages.every((stage) => stage === 'completed')
        ? 'completed'
        : stages.includes('chat')
          ? 'chat'
          : stages.includes('task')
            ? 'task'
            : 'not_started';
      const updatedAt = conditionProgress
        .map((progress) => progress.updatedAt)
        .filter((value): value is string => Boolean(value))
        .sort((a, b) => Date.parse(b) - Date.parse(a))[0];

      return {
        participant,
        authUser,
        isBound: Boolean(participant.auth_user_id),
        assignedConditions: assignedCodes.map((code) => ({
          code,
          label: participantConditionLabels[code],
        })),
        conditionProgress,
        currentStage,
        updatedAt,
      };
    });
};
