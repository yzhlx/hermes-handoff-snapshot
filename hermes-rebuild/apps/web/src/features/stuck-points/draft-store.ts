// Pending stuck point commands survive a failed request so a retry reuses the
// same operation id (idempotent) and never loses the text the user typed.

export type StuckPointUpdate = {
  operationId: string;
  version: number;
  body: { operation_id: string; text?: string; status?: 'open' | 'resolved'; resolution_note?: string | null };
};

export type StuckPointCreate = {
  operationId: string;
  sessionId: string;
  text: string;
};

let owner: string | null = null;
let pendingCreate: StuckPointCreate | null = null;
const updates = new Map<string, StuckPointUpdate>();

export function selectStuckPointOwner(userId: string) {
  if (owner !== userId) {
    updates.clear();
    pendingCreate = null;
    owner = userId;
  }
}

export function stuckPointCreateFor(): StuckPointCreate | null {
  return pendingCreate;
}

export function setStuckPointCreate(command: StuckPointCreate | null) {
  pendingCreate = command;
}

export function stuckPointUpdateFor(id: string): StuckPointUpdate | null {
  return updates.get(id) ?? null;
}

export function setStuckPointUpdate(id: string, command: StuckPointUpdate | null) {
  if (command) updates.set(id, command);
  else updates.delete(id);
}

export function clearStuckPointDrafts() {
  updates.clear();
  pendingCreate = null;
  owner = null;
}
