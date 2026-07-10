import type { ConditionKey, ExperimentCondition } from '~/types';

export type ExperimentConditionCode = '01' | '02' | '03' | '04';

export const experimentConditionCodes: ExperimentConditionCode[] = ['01', '02', '03', '04'];

export const experimentConditionCodeByKey: Record<ConditionKey, ExperimentConditionCode> = {
  no_ebl_no_roleplay: '01',
  ebl_no_roleplay: '02',
  no_ebl_roleplay: '03',
  ebl_roleplay: '04',
};

export const experimentConditionLabels: Record<ExperimentConditionCode, string> = {
  '01': 'Baseline',
  '02': 'AI Error-based learning',
  '03': 'AI Role-play learning',
  '04': 'EBL AI Role-play',
};

export const experimentConditionCode = (
  condition: ExperimentCondition | ConditionKey,
): ExperimentConditionCode | null => {
  const conditionKey = typeof condition === 'string' ? condition : condition.condition_key;
  return experimentConditionCodeByKey[conditionKey] || null;
};

export const sortExperimentConditions = (conditions: ExperimentCondition[]) => {
  return [...conditions].sort((a, b) => {
    const aCode = experimentConditionCode(a);
    const bCode = experimentConditionCode(b);
    return (aCode || '99').localeCompare(bCode || '99');
  });
};
