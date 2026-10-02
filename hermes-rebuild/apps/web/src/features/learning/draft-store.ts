// Non-secret, in-memory draft ownership survives authentication expiry.
// Reloading the browser clears it; account changes and explicit logout clear it.
type Operation = { payload: string; id: string } | null;
type Draft = {
  owner: string | null;
  goal: string;
  subject: string;
  knowledgePointId: string | null;
  knowledgePointName: string | null;
  timingEnabled: boolean;
  methodId: string | null;
  situationId: string | null;
  previousSessionId: string | null;
  resumeNote: string | null;
  feedbackSessionId: string | null;
  feedbackSubjectId: string | null;
  startOperation: Operation;
  endOperation: Operation;
  lifecycleOperation: Operation;
};
let draft: Draft = {
  owner: null,
  goal: '',
  subject: '',
  knowledgePointId: null,
  knowledgePointName: null,
  timingEnabled: false,
  methodId: null,
  situationId: null,
  previousSessionId: null,
  resumeNote: null,
  feedbackSessionId: null,
  feedbackSubjectId: null,
  startOperation: null,
  endOperation: null,
  lifecycleOperation: null,
};

export function clearLearningDraft() {
  draft = {
    owner: null,
    goal: '',
    subject: '',
    knowledgePointId: null,
    knowledgePointName: null,
    timingEnabled: false,
    methodId: null,
    situationId: null,
    previousSessionId: null,
    resumeNote: null,
    feedbackSessionId: null,
    feedbackSubjectId: null,
    startOperation: null,
    endOperation: null,
    lifecycleOperation: null,
  };
}
export function learningDraftFor(owner: string) {
  if (draft.owner !== owner) { clearLearningDraft(); draft.owner = owner; }
  return draft;
}
