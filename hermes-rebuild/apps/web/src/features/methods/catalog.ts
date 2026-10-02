import type { LearningMethodsResponse, LearningSituationsResponse } from '../../shared/api/types';

export type LearningMethod = LearningMethodsResponse['data']['items'][number];
export type LearningSituation = LearningSituationsResponse['data']['items'][number];
