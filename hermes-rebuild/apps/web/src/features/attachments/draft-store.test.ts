import { afterEach, describe, expect, it } from 'vitest';
import { addAttachmentDraft, attachmentDraftFor, clearAttachmentDrafts, selectAttachmentOwner } from './draft-store';

afterEach(() => clearAttachmentDrafts());

describe('attachment draft ownership', () => {
  it('drops in-memory Files and pending IDs when the account changes', () => {
    const file = new File(['private'], 'QA_TEST_private.png', { type: 'image/png' });
    const first = attachmentDraftFor('QA_TEST_user_a', 'feedback:one');
    const item = addAttachmentDraft(first, file);
    const operationId = item.uploadOperationId;
    selectAttachmentOwner('QA_TEST_user_b');
    expect(attachmentDraftFor('QA_TEST_user_b', 'feedback:one').items).toEqual([]);
    expect(attachmentDraftFor('QA_TEST_user_a', 'feedback:one').items).toEqual([]);
    expect(operationId).not.toBe('');
  });

  it('aborts active uploads and clears pending files on logout', () => {
    const draft = attachmentDraftFor('QA_TEST_user', 'feedback:one');
    const item = addAttachmentDraft(draft, new File(['private'], 'QA_TEST_abort.png', { type: 'image/png' }));
    const controller = new AbortController();
    item.abortController = controller;
    clearAttachmentDrafts();
    expect(controller.signal.aborted).toBe(true);
    expect(attachmentDraftFor('QA_TEST_user', 'feedback:one').items).toEqual([]);
  });
});
