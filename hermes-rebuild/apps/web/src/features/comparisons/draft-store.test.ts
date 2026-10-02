import { afterEach, describe, expect, it } from 'vitest';
import { clearComparisonDrafts, comparisonDraftFor, comparisonWorkspaceFor, selectComparisonOwner } from './draft-store';

afterEach(clearComparisonDrafts);

const empty = { conditions: '', known_values: '', formulas: '', entry_point: '', diagram: '', boundary: '', assumptions: '', conclusion: '' };

describe('comparison draft ownership', () => {
  it('retains in-memory fields and selection for the same account, then clears them on account switch or explicit logout', () => {
    selectComparisonOwner('QA_TEST_user_a');
    const draft = comparisonDraftFor('QA_TEST_user_a', 'new:QA_TEST_left:QA_TEST_right', empty);
    draft.conditions = 'QA_TEST 本地草稿';
    const workspace = comparisonWorkspaceFor('QA_TEST_user_a');
    workspace.mode = 'edit';
    workspace.leftProblemId = 'QA_TEST_left';
    workspace.rightProblemId = 'QA_TEST_right';

    expect(comparisonDraftFor('QA_TEST_user_a', 'new:QA_TEST_left:QA_TEST_right', empty).conditions).toBe('QA_TEST 本地草稿');
    expect(comparisonWorkspaceFor('QA_TEST_user_a').leftProblemId).toBe('QA_TEST_left');

    selectComparisonOwner('QA_TEST_user_b');
    expect(comparisonDraftFor('QA_TEST_user_b', 'new:QA_TEST_left:QA_TEST_right', empty).conditions).toBe('');
    expect(comparisonWorkspaceFor('QA_TEST_user_b').leftProblemId).toBe('');
    clearComparisonDrafts();
    expect(comparisonDraftFor('QA_TEST_user_b', 'new:QA_TEST_left:QA_TEST_right', empty).conditions).toBe('');
  });
});
