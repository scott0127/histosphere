import type { ConditionKey, Participant, ParticipantActivityAssignment } from '~/types';
import { experimentConditionCodeByKey, experimentConditionCodes } from '~/utils/experimentConditions';

export const getParticipantActivities = (participant: Participant | null | undefined): ParticipantActivityAssignment[] => {
  const assignments = participant?.metadata?.activity_assignments;
  if (!Array.isArray(assignments)) return [];
  // Reject the whole malformed sequence rather than silently skipping a round.
  if (!assignments.every((item) => item && typeof item.event_id === 'string' && item.event_id.trim()
    && experimentConditionCodes.includes(item.condition_code))) return [];
  return assignments;
};

export const conditionKeyForActivity = (assignment: ParticipantActivityAssignment): ConditionKey => {
  return (Object.keys(experimentConditionCodeByKey) as ConditionKey[])
    .find((key) => experimentConditionCodeByKey[key] === assignment.condition_code)!;
};

type ActivityProgress = { status: string; posttestStage?: string | null };
type ProgressByEvent = Record<string, Partial<Record<ConditionKey, ActivityProgress>>>;

export const currentParticipantActivity = (
  assignments: ParticipantActivityAssignment[],
  progress: ProgressByEvent,
): ParticipantActivityAssignment | null => {
  return assignments.find((assignment) => {
    const item = progress[assignment.event_id]?.[conditionKeyForActivity(assignment)];
    return item?.status !== 'completed' || item.posttestStage !== 'completed';
  }) || null;
};
