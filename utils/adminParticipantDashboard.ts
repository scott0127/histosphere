import type { AdminAuthUserSummary, AdminSnapshotResponse, ExperimentSession, Participant } from '~/types';
import {
  experimentConditionCodeByKey,
  experimentConditionCodes,
  experimentConditionLabels,
} from '~/utils/experimentConditions';
import type { ExperimentConditionCode } from '~/utils/experimentConditions';

export type ParticipantStage = 'not_started' | 'task' | 'chat' | 'completed';

export type ParticipantConditionProgress = {
  code: string;
  label: string;
  stage: ParticipantStage;
  sessionId?: string;
  session?: ExperimentSession;
  updatedAt?: string;
  latestActiveSession?: ExperimentSession;
};

export type ParticipantSessionSummary = {
  session: ExperimentSession;
  eventName: string;
  conditionCode: string;
  conditionLabel: string;
};

export type ParticipantDashboardRow = {
  participant: Participant;
  authUser: AdminAuthUserSummary | null;
  isBound: boolean;
  assignedConditions: Array<{ code: string; label: string }>;
  conditionProgress: ParticipantConditionProgress[];
  currentStage: ParticipantStage;
  updatedAt?: string;
  latestActiveSession?: ExperimentSession;
  currentSessions: ParticipantSessionSummary[];
  sessionHistory: ParticipantSessionSummary[];
};

export const filterParticipantDashboardRows = (
  rows: ParticipantDashboardRow[],
  showArchived: boolean,
) => {
  return showArchived
    ? rows
    : rows.filter((row) => row.participant.status !== 'archived');
};

export const participantConditionLabels: Record<ExperimentConditionCode, string> = experimentConditionLabels;

export const participantStageLabels: Record<ParticipantStage, string> = {
  not_started: '未開始',
  task: 'Task',
  chat: 'Chat',
  completed: '完成',
};

const normalizeConditionCodes = (codes: string[]): ExperimentConditionCode[] => {
  const normalized: ExperimentConditionCode[] = [];
  for (const code of codes) {
    if (
      experimentConditionCodes.includes(code as ExperimentConditionCode)
      && !normalized.includes(code as ExperimentConditionCode)
    ) {
      normalized.push(code as ExperimentConditionCode);
    }
  }
  return normalized;
};

export const conditionName = (code: string) => {
  return experimentConditionLabels[code as ExperimentConditionCode] || 'Unknown';
};

export const conditionDisplayLabel = (code: string) => {
  return `${code} ${conditionName(code)}`;
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
  const eventNamesById = new Map(snapshot.events.map((event) => [event.id, event.canonical_name]));
  const sessionsByUserAndCode = new Map<string, ExperimentSession[]>();
  const sessionsByUser = new Map<string, ExperimentSession[]>();

  for (const session of snapshot.sessions) {
    if (!session.user_id) continue;
    sessionsByUser.set(
      session.user_id,
      [...(sessionsByUser.get(session.user_id) || []), session],
    );
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
          session: session || undefined,
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
      const latestActiveSession = conditionProgress
        .map((progress) => progress.session)
        .filter((session): session is ExperimentSession => Boolean(
          session && session.status !== 'completed' && session.status !== 'archived',
        ))
        .sort((a, b) => Date.parse(b.updated_at) - Date.parse(a.updated_at))[0];
      const currentSessions = participant.auth_user_id
        ? [...(sessionsByUser.get(participant.auth_user_id) || [])]
            .filter((session) => session.status !== 'archived')
            .sort((a, b) => Date.parse(b.updated_at) - Date.parse(a.updated_at))
            .map((session) => {
              const code = experimentConditionCodeByKey[session.condition_key_snapshot] || '??';
              return {
                session,
                eventName: eventNamesById.get(session.event_id) || '未知事件',
                conditionCode: code,
                conditionLabel: conditionName(code),
              };
            })
        : [];
      const sessionHistory = participant.auth_user_id
        ? [...(sessionsByUser.get(participant.auth_user_id) || [])]
            .sort((a, b) => Date.parse(b.updated_at) - Date.parse(a.updated_at))
            .map((session) => {
              const code = experimentConditionCodeByKey[session.condition_key_snapshot] || '??';
              return {
                session,
                eventName: eventNamesById.get(session.event_id) || '未知事件',
                conditionCode: code,
                conditionLabel: conditionName(code),
              };
            })
        : [];

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
        latestActiveSession,
        currentSessions,
        sessionHistory,
      };
    });
};
