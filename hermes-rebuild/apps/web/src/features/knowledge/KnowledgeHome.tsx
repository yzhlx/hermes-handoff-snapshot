import { useQuery } from '@tanstack/react-query';
import { request } from '../../shared/api/client';
import type { SubjectsResponse } from '../../shared/api/types';
import { Feedback } from '../../shared/ui/Feedback';
import { SubjectActionCard, SubjectCard, groupSubjects } from './SubjectCards';

/**
 * 学科空间：学科与分组全部来自 GET /subjects 的 id / name / group_label。
 * 分组顺序 = 接口返回的首次出现顺序；新增学科或新增分组时这里不需要改动。
 */
export function KnowledgeHome({ onOpenSubject, onStartFree, compact = false }: {
  onOpenSubject: (subjectId: string) => void;
  onStartFree: () => void;
  compact?: boolean;
}) {
  const subjects = useQuery({
    queryKey: ['subjects'],
    queryFn: ({ signal }) => request<SubjectsResponse>('/subjects', { signal }),
  });
  const groups = groupSubjects(subjects.data?.data.items ?? []);
  const titleId = compact ? 'subject-entries-compact' : 'subject-entries';

  return <section className={compact ? 'subject-home subject-home-compact' : 'subject-home'} aria-labelledby={titleId}>
    <header className="page-hero subject-hero subject-hero--split"><div><span className="eyebrow">SUBJECTS</span><h2 id={titleId}>学科空间</h2></div>{subjects.isFetching && <span className="muted" role="status">正在同步学科…</span>}</header>
    {subjects.isPending ? <p className="muted" role="status">正在读取学科入口…</p> : subjects.isError ? <div><Feedback error={subjects.error} /><button className="secondary" onClick={() => void subjects.refetch()}>重新读取学科</button></div> : <>
      {groups.map((group) => <div className="subject-group" key={group.key}>
        <h3>{group.label}</h3><div className="subject-grid">
          {group.items.map((subject) => <SubjectCard key={subject.id} subject={subject} onOpen={onOpenSubject} />)}
        </div>
      </div>)}
      <div className="subject-grid">
        <SubjectActionCard label="自由学习" hint="不指定学科，直接开始 →" onOpen={onStartFree} />
      </div>
    </>}
  </section>;
}
