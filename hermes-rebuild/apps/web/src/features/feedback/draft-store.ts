export type PendingOperation = {
  fingerprint: string;
  id: string;
  method?: 'POST' | 'PATCH';
  path?: string;
  ifMatch?: string;
  body?: Record<string, unknown>;
} | null;

export type FeedbackDraft = {
  summary: string;
  recalledText: string;
  referenceChecked: '' | 'yes' | 'no';
  missingParts: string;
  stuckNote: string;
  resumeNote: string;
  problemTitle: string;
  problemStatement: string;
  problemId: string | null;
  attemptText: string;
  attemptStuckNote: string;
  independence: 'independent' | 'hinted' | 'after_answer' | 'unable';
  answerCheck: 'pending' | 'checked';
  result: '' | 'correct' | 'partial' | 'incorrect';
  errorCategories: string[];
  otherErrorNote: string;
  reflectionOperation: PendingOperation;
  stuckOperation: PendingOperation;
  problemOperation: PendingOperation;
  attemptOperation: PendingOperation;
  correctionOperations: Record<string, PendingOperation>;
  problemCorrectionOperations: Record<string, PendingOperation>;
};

const freshDraft = (): FeedbackDraft => ({
  summary: '', recalledText: '', referenceChecked: '', missingParts: '', stuckNote: '', resumeNote: '',
  problemTitle: '', problemStatement: '', problemId: null, attemptText: '', attemptStuckNote: '', independence: 'independent',
  answerCheck: 'pending', result: '', errorCategories: [], otherErrorNote: '',
  reflectionOperation: null, stuckOperation: null, problemOperation: null, attemptOperation: null,
  correctionOperations: {}, problemCorrectionOperations: {},
});

let owner: string | null = null;
const drafts = new Map<string, FeedbackDraft>();

/** Keep unsent form values in memory across a 401/login refresh, scoped to one account. */
export function feedbackDraftFor(userId: string, sessionId: string): FeedbackDraft {
  if (owner !== userId) {
    drafts.clear();
    owner = userId;
  }
  let draft = drafts.get(sessionId);
  if (!draft) {
    draft = freshDraft();
    drafts.set(sessionId, draft);
  }
  return draft;
}

export function clearFeedbackDrafts() {
  drafts.clear();
  owner = null;
}
