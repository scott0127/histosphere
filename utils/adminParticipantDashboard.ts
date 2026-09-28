import type { AdminAuthUserSummary, AdminSnapshotResponse, ExperimentSession, HistoricalEvent, Participant } from '~/types';
import { getParticipantActivities } from '~/utils/participantActivities';
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

export type ParticipantActivitySummary = {
  key: string;
  code: string;
  label: string;
  eventId?: string;
  eventName: string;
  isAssigned: boolean;
  stage: ParticipantStage;
  sessionHistory: ParticipantSessionSummary[];
};

export type ParticipantDashboardRow = {
  participant: Participant;
  authUser: AdminAuthUserSummary | null;
  isBound: boolean;
  assignedConditions: Array<{ code: string; label: string; eventId?: string; eventName?: string }>;
  activities: ParticipantActivitySummary[];
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
  searchQuery = '',
) => {
  const query = searchQuery.trim().toLocaleLowerCase();
  return rows.filter((row) => {
    if (!showArchived && row.participant.status === 'archived') return false;
    if (!query) return true;
    return [
      row.participant.code,
      ...row.assignedConditions.map((condition) => condition.eventName || ''),
      ...row.sessionHistory.flatMap((item) => [item.eventName, item.session.id]),
    ].some((value) => value.toLocaleLowerCase().includes(query));
  });
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

export type ParticipantActivityDraft = { event_id: string; condition_code: string };

export const buildParticipantActivityDraft = (participant: Participant): ParticipantActivityDraft[] => {
  const activities = getParticipantActivities(participant);
  return normalizeConditionCodes(participant.condition_list || []).map((code) => ({
    event_id: activities.find((activity) => activity.condition_code === code)?.event_id || '',
    condition_code: code,
  }));
};

export const validateParticipantActivityDraft = (
  activities: ParticipantActivityDraft[],
  events: Pick<HistoricalEvent, 'id' | 'archived_at'>[],
): string | null => {
  if (activities.length > 4) return '最多可分派四個活動。';
  const codes = new Set<string>();
  const eventIds = new Set<string>();
  for (const [index, activity] of activities.entries()) {
    const prefix = `第 ${index + 1} 個活動`;
    if (!experimentConditionCodes.includes(activity.condition_code as ExperimentConditionCode)) return `${prefix}尚未選擇模式。`;
    if (!activity.event_id) return `${prefix}尚未選擇歷史事件。`;
    if (codes.has(activity.condition_code)) return '每個模式只能分派一次。';
    if (eventIds.has(activity.event_id)) return '每個歷史事件只能分派一次。';
    if (!events.some((event) => event.id === activity.event_id && !event.archived_at)) return `${prefix}的歷史事件已封存或不存在，請重新選擇。`;
    codes.add(activity.condition_code);
    eventIds.add(activity.event_id);
  }
  return null;
};

export const participantActivityAssignmentInput = (
  activities: ParticipantActivityDraft[],
  events: Pick<HistoricalEvent, 'id' | 'archived_at'>[],
) => {
  const error = validateParticipantActivityDraft(activities, events);
  if (error) throw new Error(error);
  const activity_assignments = activities.map((activity) => ({
    event_id: activity.event_id,
    condition_code: activity.condition_code as ExperimentConditionCode,
  }));
  return { activity_assignments, condition_list: activity_assignments.map((activity) => activity.condition_code) };
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
  const sessionsByParticipant = new Map<string, ExperimentSession[]>();
  const legacySessionsByUser = new Map<string, ExperimentSession[]>();

  for (const session of snapshot.sessions) {
    if (session.is_admin_test) continue;
    // Stored participant identity survives account rebinding; only legacy records
    // without that identity may fall back to the current account binding.
    const ownerId = session.participant_id || session.user_id;
    if (!ownerId) continue;
    const target = session.participant_id ? sessionsByParticipant : legacySessionsByUser;
    target.set(ownerId, [...(target.get(ownerId) || []), session]);
  }

  return [...snapshot.participants]
    .sort((a, b) => a.code.localeCompare(b.code))
    .map<ParticipantDashboardRow>((participant) => {
      const assignedCodes = normalizeConditionCodes(participant.condition_list || []);
      const activities = getParticipantActivities(participant);
      const authUser = participant.auth_user_id ? authUsersById.get(participant.auth_user_id) || null : null;
      const participantSessions = [
        ...(sessionsByParticipant.get(participant.id) || []),
        ...(participant.auth_user_id ? legacySessionsByUser.get(participant.auth_user_id) || [] : []),
      ];
      const conditionProgress = assignedCodes.map((code) => {
        const activity = activities.find((item) => item.condition_code === code);
        const session = latestSession(participantSessions.filter((item) =>
          item.status !== 'archived'
          && experimentConditionCodeByKey[item.condition_key_snapshot] === code
          && (!activity || item.event_id === activity.event_id),
        ));
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
      const updatedAt = latestSession(participantSessions)?.updated_at;
      const latestActiveSession = conditionProgress
        .map((progress) => progress.session)
        .filter((session): session is ExperimentSession => Boolean(
          session && session.status !== 'completed' && session.status !== 'archived',
        ))
        .sort((a, b) => Date.parse(b.updated_at) - Date.parse(a.updated_at))[0];
      const sessionHistory = [...participantSessions]
        .sort((a, b) => Date.parse(b.updated_at) - Date.parse(a.updated_at))
        .map((session) => {
          const code = experimentConditionCodeByKey[session.condition_key_snapshot] || '??';
          return {
            session,
            eventName: eventNamesById.get(session.event_id) || '未知事件',
            conditionCode: code,
            conditionLabel: conditionName(code),
          };
        });
      const currentSessions = sessionHistory.filter((item) => item.session.status !== 'archived');
      const assignedConditions = assignedCodes.map((code) => {
        const activity = activities.find((item) => item.condition_code === code);
        return {
          code,
          label: participantConditionLabels[code],
          ...(activity ? { eventId: activity.event_id, eventName: eventNamesById.get(activity.event_id) || '未知事件' } : {}),
        };
      });
      const activityKey = (eventId: string | undefined, code: string) => JSON.stringify([eventId || null, code]);
      const activityGroups: ParticipantActivitySummary[] = assignedConditions.map((condition) => ({
        ...condition,
        key: activityKey(condition.eventId, condition.code),
        eventName: condition.eventName || '待指定歷史事件',
        isAssigned: true,
        stage: 'not_started',
        sessionHistory: [],
      }));
      for (const item of sessionHistory) {
        const key = activityKey(item.session.event_id, item.conditionCode);
        let activity = activityGroups.find((candidate) => candidate.key === key);
        if (!activity) {
          activity = {
            key,
            code: item.conditionCode,
            label: item.conditionLabel,
            eventId: item.session.event_id,
            eventName: item.eventName,
            isAssigned: false,
            stage: 'not_started',
            sessionHistory: [],
          };
          activityGroups.push(activity);
        }
        activity.sessionHistory.push(item);
      }
      for (const activity of activityGroups) {
        activity.sessionHistory.sort((a, b) => Number(a.session.status === 'archived') - Number(b.session.status === 'archived'));
        activity.stage = sessionStage(activity.sessionHistory.find((item) => item.session.status !== 'archived')?.session);
      }

      return {
        participant,
        authUser,
        isBound: Boolean(participant.auth_user_id),
        assignedConditions,
        activities: activityGroups,
        conditionProgress,
        currentStage,
        updatedAt,
        latestActiveSession,
        currentSessions,
        sessionHistory,
      };
    });
};
