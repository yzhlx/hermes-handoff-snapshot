import type { AttachmentData } from '../../shared/api/types';

export type AttachmentRole = 'question' | 'attempt' | 'answer' | 'source';
export type AttachmentDraftItem = {
  clientId: string;
  file: File;
  declaredMime: string | null;
  uploadOperationId: string;
  putOperationId: string;
  completeOperationId: string;
  attachment: AttachmentData | null;
  status: 'selected' | 'uploading' | 'uploaded' | 'processing' | 'ready' | 'failed';
  progress: number;
  error: string | null;
  role: AttachmentRole;
  page: number;
  abortController: AbortController | null;
};
export type AttachmentCommand = { fingerprint: string; id: string; ifMatch: string; body: Record<string, unknown> };
export type AttachmentDraft = { items: AttachmentDraftItem[]; problemOperation: { fingerprint: string; id: string } | null; commands: Record<string, AttachmentCommand> };

const drafts = new Map<string, AttachmentDraft>();
let owner: string | null = null;
const uuid = () => crypto.randomUUID();

export function selectAttachmentOwner(userId: string) {
  if (owner === userId) return;
  abortDrafts();
  drafts.clear();
  owner = userId;
}

/** Files and their frozen retry keys stay in memory and are scoped to one account and UI context. */
export function attachmentDraftFor(userId: string, scope: string): AttachmentDraft {
  selectAttachmentOwner(userId);
  let draft = drafts.get(scope);
  if (!draft) { draft = { items: [], problemOperation: null, commands: {} }; drafts.set(scope, draft); }
  return draft;
}

export function addAttachmentDraft(draft: AttachmentDraft, file: File): AttachmentDraftItem {
  const item: AttachmentDraftItem = {
    clientId: uuid(), file, declaredMime: null,
    uploadOperationId: uuid(), putOperationId: uuid(), completeOperationId: uuid(),
    attachment: null, status: 'selected', progress: 0, error: null, role: 'question', page: 1, abortController: null,
  };
  draft.items.push(item);
  return item;
}

export function consumeReadyAttachmentDrafts(draft: AttachmentDraft) {
  draft.items = draft.items.filter((item) => item.status !== 'ready');
}

function abortDrafts() { for (const draft of drafts.values()) for (const item of draft.items) item.abortController?.abort(); }
export function clearAttachmentDrafts() { abortDrafts(); drafts.clear(); owner = null; }
