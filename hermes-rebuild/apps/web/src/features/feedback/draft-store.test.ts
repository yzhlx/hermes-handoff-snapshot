import { afterEach, describe, expect, it } from 'vitest';
import { clearFeedbackDrafts, feedbackDraftFor } from './draft-store';

afterEach(clearFeedbackDrafts);

describe('feedback draft ownership', () => {
  it('keeps unsent content and operation ids for the same account and session', () => {
    const beforeAuthExpiry = feedbackDraftFor('QA_TEST_user', 'session-1');
    beforeAuthExpiry.summary = 'QA_TEST_实际完成了两道题';
    beforeAuthExpiry.reflectionOperation = { fingerprint: 'summary:v1', id: 'operation-1' };

    const afterSignIn = feedbackDraftFor('QA_TEST_user', 'session-1');
    expect(afterSignIn).toBe(beforeAuthExpiry);
    expect(afterSignIn.summary).toBe('QA_TEST_实际完成了两道题');
    expect(afterSignIn.reflectionOperation?.id).toBe('operation-1');
  });

  it('does not carry private feedback drafts into a different account', () => {
    const privateDraft = feedbackDraftFor('QA_TEST_user_a', 'session-1');
    privateDraft.problemStatement = 'QA_TEST_私人题目';

    const nextAccount = feedbackDraftFor('QA_TEST_user_b', 'session-1');
    expect(nextAccount).not.toBe(privateDraft);
    expect(nextAccount.problemStatement).toBe('');
  });

  it('clears feedback on explicit logout', () => {
    feedbackDraftFor('QA_TEST_user', 'session-1').stuckNote = 'QA_TEST_卡点';
    clearFeedbackDrafts();
    expect(feedbackDraftFor('QA_TEST_user', 'session-1').stuckNote).toBe('');
  });
});
