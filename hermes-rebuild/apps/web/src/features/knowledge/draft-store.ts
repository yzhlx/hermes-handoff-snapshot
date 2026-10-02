import { request } from '../../shared/api/client';

export type FrozenKnowledgeCommand = {
  id: string;
  method: 'POST' | 'PATCH' | 'PUT';
  path: string;
  ifMatch?: string;
  body: Record<string, unknown>;
};

type Store = {
  owner: string;
  forms: Map<string, Record<string, unknown>>;
  commands: Map<string, FrozenKnowledgeCommand>;
};

let store: Store | null = null;

function ownedStore(userId: string): Store {
  if (store?.owner !== userId) store = { owner: userId, forms: new Map(), commands: new Map() };
  return store;
}

export function knowledgeFormFor(userId: string, key: string, initial: Record<string, unknown> = {}) {
  const current = ownedStore(userId);
  let values = current.forms.get(key);
  if (!values) {
    values = { ...initial };
    current.forms.set(key, values);
  }
  return values;
}

export function knowledgeCommandFor(userId: string, key: string) {
  return ownedStore(userId).commands.get(key);
}

export function saveKnowledgeCommand(userId: string, key: string, command: FrozenKnowledgeCommand) {
  ownedStore(userId).commands.set(key, command);
}

export function clearKnowledgeCommand(userId: string, key: string) {
  ownedStore(userId).commands.delete(key);
}

export async function runKnowledgeCommand<T>(userId: string, key: string, method: FrozenKnowledgeCommand['method'], path: string, body: Record<string, unknown>, ifMatch?: string) {
  const current = knowledgeCommandFor(userId, key);
  const command = current ?? { id: String(body.operation_id), method, path, ifMatch, body: { ...body } };
  if (!current) saveKnowledgeCommand(userId, key, command);
  return request<T>(command.path, {
    method: command.method,
    headers: { 'Idempotency-Key': command.id, ...(command.ifMatch ? { 'If-Match': command.ifMatch } : {}) },
    body: JSON.stringify(command.body),
  });
}

export function clearKnowledgeDrafts() {
  store = null;
}
