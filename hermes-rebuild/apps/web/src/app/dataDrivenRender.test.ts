/*
 * 渲染层门禁（数据驱动硬门禁的可执行版本）
 * ------------------------------------------------------------------
 * 这里不做渲染，只对源码做三条静态检查：
 *
 * G1 渲染路径里不能出现「数据身份字面量分支」，也就是
 *    `item.title === '…'` / `item.id === 'active-recall'` 这一类：
 *    左边是接口字段、右边是写死的字符串。
 *    `typeof x.id === 'string'` 这类运行时类型校验不算（右边是类型名）。
 *
 * G2 接口目录里的文案（apps/api/src/hermes_api/catalog.py 的方法标题、
 *    情境标签）不得复制进前端：文案只能来自接口。
 *
 * G3 方法 id / 情境 id 只允许出现在元数据映射模块里；学科分组标签只允许
 *    出现在学科元数据模块里。其他文件必须通过 methodMeta/subjectMeta 取值。
 */
import { describe, expect, it } from 'vitest';

/** 目录内的所有源码文件（排除测试与测试夹具）。Vite 的 glob 在测试里同样是构建期展开。 */
const MODULES = import.meta.glob('/src/**/*.{ts,tsx}', { query: '?raw', import: 'default', eager: true }) as Record<string, string>;

function sourceFiles(): [string, string][] {
  return Object.entries(MODULES)
    .map(([path, source]) => [path.replace(/^\/?src\//, ''), source] as [string, string])
    .filter(([path]) => !/\.test\.tsx?$|[/\\]test[-.]/.test(path))
    .sort(([left], [right]) => left.localeCompare(right));
}

/** 去掉注释后的源码：注释里的示例代码不是渲染路径。 */
function codeOf(source: string): string {
  return source
    .replace(/\/\*[\s\S]*?\*\//g, '')
    .replace(/(^|\s)\/\/[^\n]*/g, '$1');
}

function codeOfFile(path: string): string {
  const entry = sourceFiles().find(([candidate]) => candidate === path);
  if (!entry) throw new Error(`未找到渲染路径文件：${path}`);
  return codeOf(entry[1]);
}

/** G1 覆盖的渲染路径文件（页面 + 数据驱动渲染层 + 元数据模块）。 */
const RENDER_FILES = [
  'app/App.tsx',
  'features/home/HomePage.tsx',
  'features/knowledge/KnowledgeHome.tsx',
  'features/knowledge/SubjectCards.tsx',
  'features/knowledge/subject-meta.ts',
  'features/methods/MethodsBrowser.tsx',
  'features/methods/MethodCards.tsx',
  'features/methods/method-meta.ts',
  'features/records/RecordEntry.tsx',
  'features/records/RecordsOverview.tsx',
  'features/records/record-meta.ts',
  'shared/ui/card-icons.tsx',
  'shared/ui/card-kit.ts',
];

/** 哪些字段算「数据身份」：接口返回的 id、标题、标签或目标文本。 */
const IDENTITY_FIELDS = new Set([
  'id', 'title', 'label', 'name', 'summary', 'goal', 'subject_id', 'subject_name', 'group_label',
  'subjectId', 'methodId', 'method_id', 'knowledgePointId', 'pointId', 'groupId',
]);

const TYPE_NAMES = new Set(['string', 'number', 'boolean', 'object', 'function', 'undefined', 'symbol', 'bigint', 'any', 'unknown']);

const FIELD_SUFFIX = /(?:\.([A-Za-z_$][\w$]*)|\[\s*['"`]([^'"`]+)['"`]\s*\])\s*$/;
const FIELD_PREFIX = /^\s*[A-Za-z_$][\w$]*\s*\??(?:\.([A-Za-z_$][\w$]*)|\[\s*['"`]([^'"`]+)['"`]\s*\])/;
const LITERAL_SUFFIX = /(['"`])([^'"`]*)\1\s*$/;
const LITERAL_PREFIX = /^\s*(['"`])([^'"`]*)\1/;

function identityFieldAtEnd(text: string): string | null {
  const match = text.match(FIELD_SUFFIX);
  const field = match?.[1] ?? match?.[2];
  return field && IDENTITY_FIELDS.has(field) ? field : null;
}

function identityFieldAtStart(text: string): string | null {
  const match = text.match(FIELD_PREFIX);
  const field = match?.[1] ?? match?.[2];
  return field && IDENTITY_FIELDS.has(field) ? field : null;
}

function literalAtEnd(text: string): string | null {
  const match = text.match(LITERAL_SUFFIX);
  return match ? match[2] ?? '' : null;
}

function literalAtStart(text: string): string | null {
  const match = text.match(LITERAL_PREFIX);
  return match ? match[2] ?? '' : null;
}

/** 找到所有「身份字段 与 字符串字面量 比较」的位置。 */
function identityLiteralBranches(source: string): string[] {
  const found: string[] = [];
  for (const match of source.matchAll(/===|!==/g)) {
    const index = match.index ?? 0;
    const left = source.slice(Math.max(0, index - 160), index);
    const right = source.slice(index + match[0].length, index + match[0].length + 160);
    const leftField = identityFieldAtEnd(left);
    const rightField = identityFieldAtStart(right);
    const rightLiteral = literalAtStart(right);
    const leftLiteral = literalAtEnd(left);
    const forward = leftField !== null && rightLiteral !== null && !TYPE_NAMES.has(rightLiteral);
    const reversed = rightField !== null && leftLiteral !== null && !TYPE_NAMES.has(leftLiteral);
    if (forward) found.push(`${leftField} === '${rightLiteral}'`);
    if (reversed) found.push(`'${leftLiteral}' === ${rightField}`);
  }
  return found;
}

/** 服务端目录里已经存在的文案：前端不得复制。 */
const CATALOG_COPY = [
  '主动回忆', '实际执行与反馈', '间隔复习', '双例对比', '费曼式检查',
  '刚听完课，感觉听懂', '一看题不知道下手', '看答案会，自己不会', '两道题很像但做法不同', '公式很多容易混',
  '以前学过现在忘了', '同类问题反复错', '状态差，只想先开始一下', '知道要干什么',
];

/** 服务端目录里的 id：只允许出现在方法元数据映射里。 */
const CATALOG_IDS = ['active-recall', 'practice-feedback', 'spaced-review', 'worked-example-compare', 'feynman-check',
  'just-finished-class', 'no-entry-point', 'answer-looks-clear', 'similar-problems', 'confusable-formulas',
  'forgotten-content', 'repeated-mistake', 'low-energy', 'know-what-to-do'];

const ID_ALLOWED_IN = 'features/methods/method-meta.ts';
const GROUP_LABELS = ['上海大学829', '公共课'];
const GROUP_LABELS_ALLOWED_IN = 'features/knowledge/subject-meta.ts';

/**
 * G2 的显式例外：对比编辑器自己的页面标题与目录里的「双例对比」同名，
 * 而它是对比页的功能名（ComparisonsPage.test.tsx 断言了这个 h1），
 * 不是从方法目录复制来的方法卡文案：方法卡标题仍然只来自 /learning-methods。
 */
const CATALOG_COPY_EXEMPT: Readonly<Record<string, readonly string[]>> = {
  'features/comparisons/ComparisonsPage.tsx': ['双例对比'],
};

describe('data-driven render gate', () => {
  it('G1 has zero identity-literal branches in the render path', () => {
    const report: string[] = [];
    for (const file of RENDER_FILES) {
      for (const branch of identityLiteralBranches(codeOfFile(file))) report.push(`${file}: ${branch}`);
    }
    expect(report).toEqual([]);
  });

  it('G1 also rejects literal dispatch inside switch statements', () => {
    const report: string[] = [];
    for (const file of RENDER_FILES) {
      codeOfFile(file).split('\n').forEach((line, index) => {
        if (/^\s*case\s+['"`]/.test(line)) report.push(`${file}:${index + 1}: ${line.trim()}`);
      });
    }
    expect(report).toEqual([]);
  });

  it('G2 never copies the server catalog text into the frontend', () => {
    const report: string[] = [];
    for (const [path, source] of sourceFiles()) {
      const code = codeOf(source);
      for (const text of CATALOG_COPY) {
        if (CATALOG_COPY_EXEMPT[path]?.includes(text)) continue;
        if (code.includes(text)) report.push(`${path}: ${text}`);
      }
    }
    expect(report).toEqual([]);
  });

  it('G3 keeps catalog ids inside the metadata map only', () => {
    const report: string[] = [];
    for (const [path, source] of sourceFiles()) {
      if (path === ID_ALLOWED_IN) continue;
      const code = codeOf(source);
      for (const id of CATALOG_IDS) if (code.includes(id)) report.push(`${path}: ${id}`);
    }
    expect(report).toEqual([]);
  });

  it('G3 keeps subject group labels inside the subject metadata map only', () => {
    const report: string[] = [];
    for (const [path, source] of sourceFiles()) {
      if (path === GROUP_LABELS_ALLOWED_IN) continue;
      const code = codeOf(source);
      for (const label of GROUP_LABELS) if (code.includes(label)) report.push(`${path}: ${label}`);
    }
    expect(report).toEqual([]);
  });

  it('G1 detects the pattern it is supposed to detect (self-check)', () => {
    expect(identityLiteralBranches("if (item.title === '主动回忆') return null;")).toEqual(["title === '主动回忆'"]);
    expect(identityLiteralBranches("if ('active-recall' === method.id) return null;")).toEqual(["'active-recall' === id"]);
    expect(identityLiteralBranches("if (typeof item.id === 'string') return null;")).toEqual([]);
    expect(identityLiteralBranches("if (page === 'methods') return null;")).toEqual([]);
  });
});
