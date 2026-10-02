import type { HomeData } from '../shared/api/types';

export function homeFixture(): HomeData {
  const section = <T,>(data: T, status: 'ready' | 'empty' = 'empty') => ({ status, data, source_revision: 'QA_TEST_home', error: null });
  return {
    date: '2026-10-01', timezone: 'Asia/Shanghai', rule_version: 'home-v1',
    sections: {
      quote: section({ daily_quote: { local_date: '2026-10-01', day_timezone: 'Asia/Shanghai', quote: null, reason: 'no_eligible_quotes', preference: null } }),
      subjects: section({ items: [{ id: 'math', name: '数学', group_label: '公共课' }] }, 'ready'),
      continue_learning: section({ current: null, last: null }),
      suggestions: section({ items: [], has_more: false }),
      methods: section({ items: [] }),
      changes: section({ from_date: '2026-09-25', to_date: '2026-10-01', items: [], effective_learning_days: 0, rule_version: 'learning-records-v1', source_revision: 'QA_TEST_home' }),
      review: section({ items: [], has_more: false }),
    },
  };
}
