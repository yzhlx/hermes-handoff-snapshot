const API = 'http://127.0.0.1:4174/api/v2';
const state = { page: 'today', date: new Date().toISOString().slice(0, 10), activeChat: null, chatSending: false };
const $ = selector => document.querySelector(selector);
const escapeHtml = value => String(value ?? '').replace(/[&<>"]/g, character => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[character]));
const formatStudyDate = value => new Intl.DateTimeFormat('zh-CN', { month:'long', day:'numeric', weekday:'short' }).format(new Date(`${value}T12:00:00`));

async function request(path, options = {}) {
  let response;
  try {
    response = await fetch(`${API}${path}`, { headers: { 'Content-Type': 'application/json' }, ...options });
  } catch {
    const error = new Error('无法连接本地学习服务。请确认学习 OS 正在运行后重试。');
    error.code = 'LOCAL_SERVICE_UNAVAILABLE';
    throw error;
  }
  const payload = await response.json();
  if (!response.ok) {
    const error = new Error(payload.error || '本地服务请求失败');
    error.code = payload.code;
    throw error;
  }
  return payload;
}
function notify(message) { const node = $('#notice'); node.textContent = message; node.hidden = false; setTimeout(() => { node.hidden = true; }, 4200); }
function priorityLabel(value) { return ({high:'高优先级',medium:'中优先级',low:'低优先级'})[value] || value; }
function taskStatusLabel(value) { return ({planned:'待开始',active:'进行中',completed:'已完成'})[value] || value; }
function renderList(node, items, render, empty) { node.innerHTML = items.length ? items.map(render).join('') : `<p class="empty">${empty}</p>`; }
function showPage(page) { state.page = page; document.querySelectorAll('.page').forEach(node => node.classList.toggle('active', node.dataset.view === page)); document.querySelectorAll('[data-page]').forEach(node => node.classList.toggle('active', node.dataset.page === page)); $('#pageTitle').textContent = ({today:'今天的安排',plan:'周计划',errors:'错题专栏',review:'每日复习',chat:'AI 对话',records:'学习记录',settings:'设置'})[page]; loadPage(page); }

function renderTimeline(data) {
  const tasks = data.tasks || [];
  $('#todayTimeline').innerHTML = tasks.length ? tasks.slice(0, 4).map((task, index) => {
    const kind = task.status === 'completed' ? 'completed' : task.id === data.current_task?.id || task.status === 'active' ? 'current' : 'planned';
    const time = task.start_time || '待安排';
    const status = kind === 'completed' ? '已完成' : kind === 'current' ? '当前任务' : '计划中';
    return `<article class="timeline-event ${kind}" data-state="${kind}"${kind === 'current' ? ' aria-current="step"' : ''}><time>${escapeHtml(time)}</time><strong>${escapeHtml(task.title)}</strong><small>${task.estimated_minutes || '--'} 分钟 · ${status}</small></article>`;
  }).join('') : `<article class="timeline-event empty"><strong>今天还没有安排</strong><small>先在周计划中写下最重要的一步。</small></article>`;
}
function renderLearningMarkdown(value) {
  const escaped = escapeHtml(value);
  const withCodeBlocks = escaped.replace(/```(?:[\w-]+)?\n?([\s\S]*?)```/g, (_, code) => `<pre><code>${code.trim()}</code></pre>`);
  const withInlineFormat = withCodeBlocks
    .replace(/`([^`\n]+)`/g, '<code>$1</code>')
    .replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
  return withInlineFormat.split(/\n{2,}/).map(block => {
    if (!block) return '';
    if (block.startsWith('<pre>')) return block;
    const lines = block.split('\n');
    if (lines.every(line => /^\s*[-*]\s+/.test(line))) {
      return `<ul>${lines.map(line => `<li>${line.replace(/^\s*[-*]\s+/, '')}</li>`).join('')}</ul>`;
    }
    return `<p>${lines.join('<br>')}</p>`;
  }).join('');
}
function renderAIInsight(data) {
  const reviewCount = data.review.items.length;
  const current = data.current_task;
  $('#aiInsightTitle').textContent = current ? '从小步回忆开始' : '先给今天一个重心';
  $('#aiInsightText').textContent = current ? `你接下来将进入“${current.title}”。建议先用 10 分钟确认关键概念，再把注意力交给主要任务。` : '今天还没有录入任务。先确定一项可在 45 分钟内完成的核心任务，再为它预留缓冲时间。';
  $('#aiEvidence').innerHTML = [`待复习错题 ${reviewCount} 道`, `今日已完成 ${data.completed_count} 项`, current ? `当前优先级：${priorityLabel(current.priority)}` : '当前状态：等待安排'].map(item => `<li>${escapeHtml(item)}</li>`).join('');
}
function renderTodayUnavailable() {
  $('#todayTimeline').innerHTML = `<article class="timeline-event empty"><strong>今天的节奏暂时不可用</strong><small>请检查本地服务后再试。</small></article>`;
  $('#todayCurrent').innerHTML = `<span class="mission-index" aria-hidden="true">—</span><div class="mission-body"><p class="eyebrow">TODAY'S MISSION · 等待服务</p><h2>今天最重要的一步仍在这里</h2><p class="task-meta">暂时无法读取任务。恢复本地服务后，学习安排会自动显示。</p><div class="mission-footer"><span class="mission-progress">本地数据未改变</span><button class="primary" onclick="showPage('plan')">打开周计划</button></div></div>`;
  $('#nextTasks').innerHTML = `<p class="empty">候选任务会在服务恢复后显示。</p>`;
  $('#statusSummary').innerHTML = `<p class="empty">学习状态暂时不可用。</p>`;
}

async function loadToday() {
  let data;
  try {
    data = await request(`/dashboard?date=${state.date}`);
  } catch (error) {
    renderTodayUnavailable();
    notify('无法读取今日学习数据。请检查本地服务后重试。');
    return;
  }
  const current = data.current_task;
  const tasks = data.tasks || [];
  const plannedMinutes = tasks.reduce((total, task) => total + (Number(task.estimated_minutes) || 0), 0);
  const missionProgress = `${data.completed_count} / ${tasks.length || 0}`;

  $('#timelineDate').textContent = formatStudyDate(state.date);
  $('#topbarDate').textContent = formatStudyDate(state.date);
  renderTimeline(data);
  $('#todayCurrent').innerHTML = current
    ? `<span class="mission-index" aria-hidden="true">01</span><div class="mission-body"><p class="eyebrow">CURRENT TASK · 现在进行</p><h2>${escapeHtml(current.title)}</h2><p class="task-meta">${priorityLabel(current.priority)} · ${current.estimated_minutes || '--'} 分钟 · ${current.start_time || '按优先级安排'}</p><div class="mission-footer"><span class="mission-progress">今日已完成 ${missionProgress}</span><button class="primary" onclick="setTaskStatus('${current.id}','active')">开始学习</button></div></div>`
    : `<span class="mission-index" aria-hidden="true">—</span><div class="mission-body"><p class="eyebrow">TODAY'S MISSION · 等待安排</p><h2>还没有安排任务</h2><p class="task-meta">先为今天新增一个任务，系统会帮你安排当前优先项。</p><div class="mission-footer"><span class="mission-progress">为专注留出余量</span><button class="primary" onclick="showPage('plan')">新增任务</button></div></div>`;
  renderList($('#nextTasks'), data.next_tasks.slice(0, 3), task => `<div class="list-item"><strong>${escapeHtml(task.title)}</strong><small>${priorityLabel(task.priority)} · ${task.estimated_minutes || '--'} 分钟</small></div>`, '今天没有更多候选任务。');
  $('#todayProgress').textContent = missionProgress;
  $('#remainingTime').textContent = data.remaining_count ? `${data.remaining_count} 项` : '已完成';
  $('#reviewProgress').textContent = `${data.review.items.length} / 5`;
  $('#focusTime').textContent = plannedMinutes ? `${plannedMinutes} min` : '--';
  renderAIInsight(data);
  const statuses = await request(`/status?date=${state.date}`);
  const latest = statuses.items[0];
  $('#statusSummary').innerHTML = latest
    ? `<strong>${escapeHtml(latest.advice.message)}</strong><p class="task-meta">心情 ${latest.mood ?? '-'} · 精力 ${latest.energy ?? '-'} · 压力 ${latest.stress ?? '-'}</p>`
    : `<p class="empty">尚未记录状态。记录后会获得非医疗的学习建议。</p>`;
}
async function loadPlan() {
  $('#taskDate').value = state.date;
  const data = await request(`/tasks?date=${state.date}`);
  renderList(
    $('#taskList'),
    data.items,
    task => `<article class="list-item planner-task-item" role="listitem"><div class="planner-task-copy"><strong>${escapeHtml(task.title)}</strong><small>${priorityLabel(task.priority)} · ${task.estimated_minutes || '--'} 分钟</small></div><span class="planner-task-state" data-status="${escapeHtml(task.status)}">${escapeHtml(taskStatusLabel(task.status))}</span></article>`,
    '当天还没有任务。先把最重要的一步安排进来。'
  );
}
async function loadErrors() {
  const data = await request('/error-questions');
  renderList(
    $('#errorList'),
    data.items,
    item => {
      const evidence = [item.problem_text, item.work_text, item.correct_answer, item.explanation].filter(Boolean).length;
      const tags = Array.isArray(item.error_types) && item.error_types.length ? item.error_types.join(' · ') : '尚未分析';
      return `<article class="list-item error-note-card" role="listitem"><div class="error-note-heading"><div><span class="error-note-subject">${escapeHtml(item.subject || '未分类')}</span><strong>${escapeHtml(item.title || '未命名错题')}</strong></div><span class="error-evidence-count">${evidence} 项证据</span></div><p class="error-note-context">${escapeHtml(item.chapter || '未填写章节')} · ${escapeHtml(priorityLabel(item.priority))} · ${escapeHtml(tags)}</p><div class="error-note-action"><button class="quiet-button" type="button" data-analysis-id="${escapeHtml(item.id)}" onclick="analyzeError('${item.id}')">分析学习线索</button><p class="error-analysis-status" data-analysis-status="${escapeHtml(item.id)}" role="status" aria-live="polite"></p></div></article>`;
    },
    '还没有错题。先把一段需要回看的证据收录进来。'
  );
}
async function loadReview() {
  const data = await request(`/daily-review?date=${state.date}`);
  renderList(
    $('#reviewList'),
    data.items,
    (item, index) => `<article class="review-card review-focus-card"><header class="review-card-header"><div><span class="section-kicker">REVIEW ${String(index + 1).padStart(2, '0')} · ${escapeHtml(item.subject)}</span><h3>${escapeHtml(item.title || '未命名错题')}</h3><p>${escapeHtml(item.chapter || '未分类章节')} · 已复习 ${item.review_count || 0} 次</p></div><span class="review-due-note">今日复盘</span></header><section class="review-evidence-block"><h4>题目证据</h4><p>${escapeHtml(item.problem_text || '尚未录入原题文本。可在错题笔记中补充。')}</p></section><div class="review-compare-grid"><section><h4>上次作答</h4><p>${escapeHtml(item.work_text || '尚未记录作答过程。')}</p></section><section><h4>参考答案</h4><p>${escapeHtml(item.correct_answer || '尚未记录参考答案。')}</p></section></div><section class="review-explanation"><h4>解析与下次检查点</h4><p>${escapeHtml(item.explanation || '本次可先复述关键步骤，再选择最接近的复习结果。')}</p></section><footer class="review-actions" aria-label="选择本次复习结果">${[['mastered','已掌握'],['partial','部分掌握'],['cannot','仍不会'],['careless','粗心导致错误'],['skipped','暂时跳过']].map(([key,label]) => `<button type="button" onclick="recordReview('${item.id}','${key}')">${label}</button>`).join('')}</footer></article>`,
    '今天没有到期的高等数学错题。'
  );
}
function scrollChatToLatest() { const messages = $('#messages'); messages.scrollTop = messages.scrollHeight; }
function renderChatMessage(message) {
  const isUser = message.role === 'user';
  const content = isUser ? `<p>${escapeHtml(message.content)}</p>` : `<div class="message-content">${renderLearningMarkdown(message.content)}</div>`;
  return `<article class="message ${isUser ? 'user' : 'assistant'}"><span class="message-role">${isUser ? '你的问题' : 'Hermes 的学习批注'}</span>${content}</article>`;
}
async function loadChats() { const data = await request('/chats'); renderList($('#chatList'), data.items, chat => `<button class="list-item chat-history-item ${chat.id === state.activeChat ? 'active' : ''}" type="button" aria-current="${chat.id === state.activeChat ? 'page' : 'false'}" onclick="openChat('${chat.id}')"><strong>${escapeHtml(chat.title)}</strong><small>${new Date(chat.updated_at).toLocaleString()}</small></button>`, '还没有对话。新建一个学习问题开始。'); if (state.activeChat) await openChat(state.activeChat, false); }
async function openChat(id, refresh = true) { state.activeChat = id; const data = await request(`/chats/${id}/messages`); $('#messages').innerHTML = data.items.length ? data.items.map(renderChatMessage).join('') : '<div class="chat-empty-state"><span class="section-kicker">READY WHEN YOU ARE</span><h3>从一个具体问题开始。</h3><p>写下正在卡住的概念、错题或下一步计划。</p></div>'; $('#chatStatus').textContent = data.items.length ? '对话已就绪' : '等待你的问题'; scrollChatToLatest(); if (refresh) loadChats(); }
function safeStatisticCount(value) { const count = Number(value); return Number.isFinite(count) && count >= 0 ? count : 0; }
async function loadRecords() {
  const data = await request('/statistics');
  for (const [selector, items, empty] of [['#subjectStats',data.by_subject,'暂无学科数据。'],['#chapterStats',data.by_chapter,'暂无章节数据。'],['#typeStats',data.by_error_type,'暂无错误类型数据。']]) {
    renderList(
      $(selector),
      items,
      item => {
        const label = item.subject || item.chapter || item.name || '未分类';
        const count = safeStatisticCount(item.count);
        return `<article class="list-item statistic-row" role="listitem" aria-label="${escapeHtml(label)}，${count} 条记录"><strong>${escapeHtml(label)}</strong><span><b>${count}</b><small>条记录</small></span></article>`;
      },
      empty
    );
  }
}
async function loadSettings() {
  const data = await request('/settings/ai');
  const form = $('#aiSettingsForm');
  form.base_url.value = data.base_url || '';
  form.protocol.value = data.protocol || 'chat_completions';
  form.model.value = data.model || '';
  form.timeout_seconds.value = data.timeout_seconds || 30;
  form.clear_api_key.checked = false;
  $('#aiConfigStatus').textContent = data.is_configured ? `密钥已配置（末四位 ${data.key_suffix || '已隐藏'}）` : '尚未配置 API 密钥';
  $('#connectionTestStatus').textContent = '尚未执行测试。';
}
async function loadPage(page = state.page) { try { if (page === 'today') await loadToday(); if (page === 'plan') await loadPlan(); if (page === 'errors') await loadErrors(); if (page === 'review') await loadReview(); if (page === 'chat') await loadChats(); if (page === 'records') await loadRecords(); if (page === 'settings') await loadSettings(); } catch (error) { notify(error.message); } }
async function setTaskStatus(id, status) { await request(`/tasks/${id}`, { method:'PATCH', body:JSON.stringify({status}) }); loadToday(); }
async function recordReview(id, outcome) { await request(`/error-questions/${id}/reviews`, { method:'POST', body:JSON.stringify({outcome, reviewed_on:state.date}) }); loadReview(); }
async function analyzeError(id) {
  const button = document.querySelector(`[data-analysis-id="${id}"]`);
  const status = document.querySelector(`[data-analysis-status="${id}"]`);
  if (button instanceof HTMLButtonElement) {
    button.disabled = true;
    button.setAttribute('aria-busy', 'true');
    button.textContent = '正在整理…';
  }
  if (status) status.textContent = 'Hermes 正在依据已有证据整理学习线索…';
  try {
    const result = await request(`/error-questions/${id}/analyze`, {method:'POST',body:JSON.stringify({})});
    if (result.information_sufficient) {
      const message = `主要原因：${result.primary_error_type}；建议：${result.improvement_suggestion}`;
      if (status) status.textContent = `已生成建议。${message}`;
      notify(message);
    } else {
      const message = result.questions.join('；') || '信息不足，请补充作答过程。';
      if (status) status.textContent = `需要补充证据：${message}`;
      notify(message);
    }
  } catch (error) {
    if (status) status.textContent = `分析未完成：${error.message}`;
    notify(error.message);
  } finally {
    if (button instanceof HTMLButtonElement) {
      button.disabled = false;
      button.removeAttribute('aria-busy');
      button.textContent = '分析学习线索';
    }
  }
}
window.showPage = showPage; window.setTaskStatus = setTaskStatus; window.recordReview = recordReview; window.openChat = openChat; window.analyzeError = analyzeError;
document.querySelectorAll('[data-page]').forEach(button => button.addEventListener('click', () => showPage(button.dataset.page)));
document.querySelectorAll('[data-goto]').forEach(button => button.addEventListener('click', () => {
  if (button.dataset.goto === 'status') return $('#statusDialog').showModal();
  showPage(button.dataset.goto);
}));
$('#taskDate').addEventListener('change', event => { state.date = event.target.value; loadPlan(); });
$('#taskForm').addEventListener('submit', async event => {
  event.preventDefault();
  const formElement = event.currentTarget;
  if (!(formElement instanceof HTMLFormElement) || formElement.dataset.submitting === 'true') return;
  const submitButton = formElement.querySelector('button[type="submit"]');
  const formStatus = $('#taskFormStatus');
  const payload = Object.fromEntries(new FormData(formElement));
  formElement.dataset.submitting = 'true';
  if (submitButton) {
    submitButton.disabled = true;
    submitButton.setAttribute('aria-busy', 'true');
    submitButton.textContent = '正在保存…';
  }
  formStatus.textContent = '正在保存到本机学习计划…';
  try {
    await request('/tasks', {method:'POST', body:JSON.stringify(payload)});
  } catch (error) {
    formStatus.textContent = '未保存。已填写内容仍保留，可以检查后重试。';
    notify(error.message);
    return;
  } finally {
    delete formElement.dataset.submitting;
    if (submitButton) {
      submitButton.disabled = false;
      submitButton.removeAttribute('aria-busy');
      submitButton.textContent = '加入计划';
    }
  }
  formElement.reset();
  $('#taskDate').value = state.date;
  formStatus.textContent = '任务已保存，正在更新当天安排…';
  try {
    await loadPlan();
  } catch (error) {
    formStatus.textContent = '任务已保存，但当天列表暂时无法刷新。';
    notify('任务已加入计划，但当天列表暂时无法刷新。');
    return;
  }
  formStatus.textContent = '任务已加入当天安排。';
  notify('任务已加入计划。');
});
$('#errorForm').addEventListener('submit', async event => {
  event.preventDefault();
  const formElement = event.currentTarget;
  if (!(formElement instanceof HTMLFormElement) || formElement.dataset.submitting === 'true') return;
  const submitButton = formElement.querySelector('button[type="submit"]');
  const formStatus = $('#errorFormStatus');
  const payload = Object.fromEntries(new FormData(formElement));
  formElement.dataset.submitting = 'true';
  if (submitButton) {
    submitButton.disabled = true;
    submitButton.setAttribute('aria-busy', 'true');
    submitButton.textContent = '正在保存…';
  }
  formStatus.textContent = '正在保存这段学习证据…';
  try {
    await request('/error-questions', {method:'POST',body:JSON.stringify(payload)});
  } catch (error) {
    formStatus.textContent = '未保存。已填写内容仍保留，可以检查后重试。';
    notify(error.message);
    return;
  } finally {
    delete formElement.dataset.submitting;
    if (submitButton) {
      submitButton.disabled = false;
      submitButton.removeAttribute('aria-busy');
      submitButton.textContent = '保存错题';
    }
  }
  formElement.reset();
  formElement.subject.value = '高等数学';
  formStatus.textContent = '已保存，正在更新错题笔记…';
  try {
    await loadErrors();
  } catch (error) {
    formStatus.textContent = '错题已保存，但笔记列表暂时无法刷新。';
    notify('错题已保存，但笔记列表暂时无法刷新。');
    return;
  }
  formStatus.textContent = '错题已保存到本机笔记。';
  notify('错题已保存。');
});
$('#refreshReview').addEventListener('click', loadReview);
$('#newChat').addEventListener('click', async () => { const title = window.prompt('对话标题'); if (!title) return; try { const chat = await request('/chats',{method:'POST',body:JSON.stringify({title})}); await openChat(chat.id); } catch(error) { notify(error.message); } });
$('#chatForm').addEventListener('submit', async event => { event.preventDefault(); if (!state.activeChat) return notify('请先新建对话。'); if (state.chatSending) return; const formElement = event.currentTarget; const content = new FormData(formElement).get('content')?.trim(); if (!content) return; const submitButton = formElement.querySelector('button[type="submit"]'); state.chatSending = true; submitButton.disabled = true; submitButton.setAttribute('aria-busy','true'); submitButton.textContent = '生成中…'; $('#chatStatus').textContent = 'Hermes 正在整理学习建议'; $('#messages').insertAdjacentHTML('beforeend', `<article class="message user pending"><span class="message-role">你的问题</span><p>${escapeHtml(content)}</p></article><article class="message assistant pending" aria-live="polite"><span class="message-role">Hermes 正在整理</span><span class="skeleton skeleton--line"></span><span class="skeleton skeleton--short"></span></article>`); scrollChatToLatest(); try { await request(`/chats/${state.activeChat}/messages`,{method:'POST',body:JSON.stringify({role:'user',content})}); formElement.reset(); await openChat(state.activeChat,false); } catch(error) { await openChat(state.activeChat,false); $('#chatStatus').textContent = '回复未生成；你的问题已保留'; notify(`${error.code ? `${error.code}：` : ''}${error.message}。你的消息已保留，可修正配置后重试。`); } finally { state.chatSending = false; submitButton.disabled = false; submitButton.removeAttribute('aria-busy'); submitButton.textContent = '发送'; } });
$('#statusButton').addEventListener('click', () => $('#statusDialog').showModal());
$('#closeStatusDialog').addEventListener('click', () => $('#statusDialog').close());
$('#statusForm').addEventListener('submit', async event => {
  event.preventDefault();
  const formElement = event.currentTarget;
  if (!(formElement instanceof HTMLFormElement) || formElement.dataset.submitting === 'true') return;
  const form = new FormData(formElement);
  const payload = Object.fromEntries(form);
  const submitButton = formElement.querySelector('button[type="submit"]');
  const formStatus = $('#statusFormStatus');
  ['mood','energy','stress'].forEach(key => { payload[key] = payload[key] ? Number(payload[key]) : null; });
  payload.fatigued = form.get('fatigued') === 'on';
  payload.willing_to_continue = form.get('willing_to_continue') === 'on';
  payload.recorded_on = state.date;
  formElement.dataset.submitting = 'true';
  if (submitButton) {
    submitButton.disabled = true;
    submitButton.setAttribute('aria-busy', 'true');
    submitButton.textContent = '正在保存…';
  }
  formStatus.textContent = '正在保存今天的学习节奏…';
  try {
    await request('/status',{method:'POST',body:JSON.stringify(payload)});
  } catch(error) {
    formStatus.textContent = '未保存。已填写内容仍保留，可以检查后重试。';
    notify(error.message);
    return;
  } finally {
    delete formElement.dataset.submitting;
    if (submitButton) {
      submitButton.disabled = false;
      submitButton.removeAttribute('aria-busy');
      submitButton.textContent = '保存状态';
    }
  }
  $('#statusDialog').close();
  try {
    await loadToday();
  } catch (error) {
    notify('状态已记录，但今日建议暂时无法刷新。');
    return;
  }
  notify('状态已记录。');
});
$('#aiSettingsForm').addEventListener('submit', async event => {
  event.preventDefault();
  const formElement = event.currentTarget;
  if (!(formElement instanceof HTMLFormElement) || formElement.dataset.submitting === 'true') return;
  const payload = Object.fromEntries(new FormData(formElement));
  const submitButton = formElement.querySelector('button[type="submit"]');
  const saveStatus = $('#aiSaveStatus');
  payload.clear_api_key = formElement.clear_api_key.checked;
  if (!payload.api_key) delete payload.api_key;
  formElement.dataset.submitting = 'true';
  if (submitButton) {
    submitButton.disabled = true;
    submitButton.setAttribute('aria-busy', 'true');
    submitButton.textContent = '正在保存…';
  }
  saveStatus.textContent = '正在保存本机 AI 配置…';
  try {
    await request('/settings/ai', {method:'POST',body:JSON.stringify(payload)});
  } catch(error) {
    saveStatus.textContent = '未保存。已填写的非密钥配置仍保留，可以检查后重试。';
    notify(error.message);
    return;
  } finally {
    delete formElement.dataset.submitting;
    if (submitButton) {
      submitButton.disabled = false;
      submitButton.removeAttribute('aria-busy');
      submitButton.textContent = '保存 AI 配置';
    }
  }
  formElement.api_key.value = '';
  saveStatus.textContent = '配置已保存，正在读取当前状态…';
  try {
    await loadSettings();
  } catch (error) {
    saveStatus.textContent = '配置已保存，但当前状态暂时无法刷新。';
    notify('AI 配置已保存，但当前状态暂时无法刷新。');
    return;
  }
  saveStatus.textContent = 'AI 配置已保存。';
  notify('AI 配置已保存。');
});
$('#connectionTest').addEventListener('click', async event => {
  const button = event.currentTarget;
  if (!(button instanceof HTMLButtonElement) || button.disabled) return;
  const status = $('#connectionTestStatus');
  button.disabled = true;
  button.setAttribute('aria-busy', 'true');
  button.textContent = '测试中…';
  status.textContent = '正在使用当前 Provider 测试连接…';
  try {
    await request('/settings/ai/test', {method:'POST',body:JSON.stringify({})});
    status.textContent = '连接测试成功。当前 Provider 可以响应最小请求。';
    notify('AI 连接正常。');
  } catch(error) {
    status.textContent = `连接测试未通过：${error.message}`;
    notify(`${error.code ? `${error.code}：` : ''}${error.message}`);
  } finally {
    button.disabled = false;
    button.removeAttribute('aria-busy');
    button.textContent = '测试 AI 连接';
  }
});
// Graceful exit: a user-discoverable, confirm-gated entry that posts to the loopback
// local API. Closing the browser tab does NOT stop the background service.
$('#exitAppButton').addEventListener('click', () => $('#exitConfirmDialog').showModal());
$('#cancelExit').addEventListener('click', () => $('#exitConfirmDialog').close());
$('#confirmExit').addEventListener('click', async () => {
  const button = $('#confirmExit');
  const status = $('#exitStatus');
  button.disabled = true;
  $('#exitConfirmDialog').close();
  status.hidden = false;
  status.textContent = '正在退出本机服务…';
  try {
    await request('/shutdown', { method: 'POST', body: JSON.stringify({}) });
    status.textContent = '学习 OS 已退出，可以关闭此页面。';
    notify('学习 OS 已退出，可以关闭此页面。');
  } catch (error) {
    status.textContent = `退出未成功：${error.message}`;
    button.disabled = false;
    notify(error.message);
  }
});
$('#aiComposer').addEventListener('submit', event => { event.preventDefault(); const prompt = new FormData(event.currentTarget).get('prompt')?.trim(); showPage('chat'); if (prompt) { $('#chatForm [name="content"]').value = prompt; notify('问题已带入 AI 对话。新建对话后即可发送。'); } });
function dataUrl(file) { return new Promise((resolve, reject) => { const reader = new FileReader(); reader.onload = () => resolve(reader.result); reader.onerror = reject; reader.readAsDataURL(file); }); }
const quickErrorButton = document.createElement('button'); quickErrorButton.className = 'quiet-button'; quickErrorButton.type = 'button'; quickErrorButton.textContent = '拍照快速录入'; quickErrorButton.addEventListener('click', () => $('#quickErrorDialog').showModal()); document.querySelector('[data-view="errors"] .page-heading').append(quickErrorButton);
$('#closeQuickError').addEventListener('click', () => $('#quickErrorDialog').close());
$('#extractErrorImages').addEventListener('click', async () => { const files = [...$('#errorImages').files]; if (!files.length) return; try { $('#quickErrorHint').textContent = '正在识别图片…'; const draft = await request('/quick-entry/error-draft',{method:'POST',body:JSON.stringify({images:await Promise.all(files.map(dataUrl))})}); const form = $('#errorForm'); Object.entries(draft).forEach(([key,value]) => { if (form.elements[key] && value) form.elements[key].value = value; }); $('#quickErrorDialog').close(); showPage('errors'); notify('已识别并填入草稿，请核对后保存错题。'); } catch (error) { $('#quickErrorHint').textContent = error.message; } });
$('#todayLabel').textContent = new Intl.DateTimeFormat('zh-CN',{weekday:'long',month:'long',day:'numeric'}).format(new Date());
const handwritingEntry = document.createElement('button');
handwritingEntry.type = 'button';
handwritingEntry.dataset.action = 'recall';
handwritingEntry.dataset.icon = '✎';
handwritingEntry.setAttribute('aria-label', '手写画布');
handwritingEntry.textContent = '手写画布';
document.querySelector('.main-nav').append(handwritingEntry);
loadToday();
