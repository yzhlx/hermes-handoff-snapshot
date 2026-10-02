import { afterEach, describe, expect, it } from 'vitest';
import { clearKnowledgeDrafts, knowledgeCommandFor, knowledgeFormFor, saveKnowledgeCommand } from './draft-store';

afterEach(clearKnowledgeDrafts);

describe('knowledge draft ownership', () => {
  it('retains form values and frozen commands for the same owner', () => {
    const form = knowledgeFormFor('QA_TEST_user', 'point:1', { name: '' });
    form.name = 'QA_TEST_标题';
    const command = { id: 'QA_TEST_operation', method: 'PATCH' as const, path: '/chapters/1', ifMatch: '"1"', body: { operation_id: 'QA_TEST_operation', name: 'QA_TEST_标题' } };
    saveKnowledgeCommand('QA_TEST_user', 'point:1', command);
    expect(knowledgeFormFor('QA_TEST_user', 'point:1').name).toBe('QA_TEST_标题');
    expect(knowledgeCommandFor('QA_TEST_user', 'point:1')).toBe(command);
  });

  it('clears retained knowledge drafts when owner changes or explicit logout clears them', () => {
    knowledgeFormFor('QA_TEST_user', 'point:1', { name: 'private' });
    expect(knowledgeFormFor('QA_TEST_other', 'point:1', { name: 'other' }).name).toBe('other');
    clearKnowledgeDrafts();
    expect(knowledgeFormFor('QA_TEST_other', 'point:1', { name: '' }).name).toBe('');
  });
});
