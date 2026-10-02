export type ReviewCommand = {
  operationId: string;
  action: 'accept' | 'snooze' | 'dismiss';
  version: number;
  body: { operation_id: string; action: 'accept' | 'snooze' | 'dismiss'; snoozed_until?: string | null };
  snoozedUntil?: string;
} | null;

let owner: string | null = null;
const commands = new Map<string, ReviewCommand>();

export function selectReviewOwner(userId: string) {
  if (owner !== userId) {
    commands.clear();
    owner = userId;
  }
}

export function reviewCommandFor(id: string): ReviewCommand {
  return commands.get(id) ?? null;
}

export function setReviewCommand(id: string, command: ReviewCommand) {
  if (command) commands.set(id, command);
  else commands.delete(id);
}

export function clearReviewDrafts() {
  commands.clear();
  owner = null;
}
