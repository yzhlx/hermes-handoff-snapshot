import { request } from '../../shared/api/client';
import type { CreateComparisonInput, PatchComparisonInput, ProblemPatchInput } from '../../shared/api/types';

export type ComparisonDraftFields = Pick<CreateComparisonInput,
  'conditions' | 'known_values' | 'formulas' | 'entry_point' | 'diagram' | 'boundary' | 'assumptions' | 'conclusion'>;

export type ComparisonCommand = {
  fingerprint: string;
  operationId: string;
  method: 'POST' | 'PATCH';
  path: string;
  ifMatch?: string;
  body: CreateComparisonInput | PatchComparisonInput | ProblemPatchInput;
};

export type ComparisonWorkspaceDraft = {
  mode: 'list' | 'library' | 'select' | 'edit' | 'detail';
  comparisonId: string | null;
  leftProblemId: string;
  rightProblemId: string;
  leftAttemptId: string | null;
  rightAttemptId: string | null;
};

type Store = {
  owner: string;
  forms: Map<string, ComparisonDraftFields>;
  commands: Map<string, ComparisonCommand>;
  uncertain: Set<string>;
  workspace: ComparisonWorkspaceDraft;
};

let store: Store | null = null;

function ownedStore(userId: string): Store {
  if (!store || store.owner !== userId) {
    store = { owner: userId, forms: new Map(), commands: new Map(), uncertain: new Set(), workspace: { mode: 'list', comparisonId: null, leftProblemId: '', rightProblemId: '', leftAttemptId: null, rightAttemptId: null } };
  }
  return store;
}

export function selectComparisonOwner(userId: string) {
  ownedStore(userId);
}

export function comparisonDraftFor(userId: string, key: string, initial: ComparisonDraftFields): ComparisonDraftFields {
  const current = ownedStore(userId);
  let draft = current.forms.get(key);
  if (!draft) {
    draft = { ...initial };
    current.forms.set(key, draft);
  }
  return draft;
}

export function comparisonCommandFor(userId: string, key: string) {
  return ownedStore(userId).commands.get(key);
}

export function saveComparisonCommand(userId: string, key: string, command: ComparisonCommand) {
  ownedStore(userId).commands.set(key, command);
}

export function clearComparisonCommand(userId: string, key: string) {
  const current = ownedStore(userId);
  current.commands.delete(key);
  current.uncertain.delete(key);
}

export function markComparisonCommandUncertain(userId: string, key: string) {
  ownedStore(userId).uncertain.add(key);
}

export function comparisonCommandIsUncertain(userId: string, key: string) {
  return ownedStore(userId).uncertain.has(key);
}

export function comparisonWorkspaceFor(userId: string) {
  return ownedStore(userId).workspace;
}

export function clearComparisonWorkspace(userId: string) {
  const current = ownedStore(userId);
  current.workspace = { mode: 'list', comparisonId: null, leftProblemId: '', rightProblemId: '', leftAttemptId: null, rightAttemptId: null };
}

export async function runComparisonCommand<T>(userId: string, key: string, command: ComparisonCommand): Promise<T> {
  let frozen = comparisonCommandFor(userId, key);
  if (!frozen || frozen.fingerprint !== command.fingerprint) {
    frozen = command;
    saveComparisonCommand(userId, key, frozen);
  }
  return request<T>(frozen.path, {
    method: frozen.method,
    headers: {
      'Idempotency-Key': frozen.operationId,
      ...(frozen.ifMatch ? { 'If-Match': frozen.ifMatch } : {}),
    },
    body: JSON.stringify(frozen.body),
  });
}

export function clearComparisonDrafts() {
  store = null;
}
