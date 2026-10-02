/* ============================================================================
   今日页 · 动机面板（learning-os-momentum.js）
   由 tools/assets/ 装配，加载在 app.js / 错题模块之后。

   为什么做这个：用户反馈"没有想用的欲望"。原今日页在空数据时给出的是
   4 个 0 + 三张空白卡片 + 一段 AI 空话 —— 它只告诉你"你什么都没做"。
   这里改成用错题服务的**真实数据**给出三样东西：
     · 压力：考研倒计时（还差多少天）
     · 进度：今天该复习几道 / 已复习几道，进度条
     · 一个明确的下一步：一个有且只有一个的主按钮（按状态自适应）

   数据全部来自 /cuoti/api/*（同域同门禁）：
     /exam      倒计时、考试名、可复习天数、未来 7 天负荷
     /stats     错题库总数、今日待复习、今日已复习、归档数、累计遗忘
     /forecast  未来每天到期量（画迷你柱状）
     /cards     最近入库（点一下直接进复盘）
   ========================================================================== */
(function () {
  'use strict';

  var BASE = '/cuoti';
  var cache = { exam: null, stats: null, forecast: null, cards: [] };

  function q(sel, root) { return (root || document).querySelector(sel); }
  function el(tag, text, className) {
    var node = document.createElement(tag);
    if (text !== undefined && text !== null) { node.textContent = String(text); }
    if (className) { node.className = className; }
    return node;
  }
  function clear(node) { while (node && node.firstChild) { node.removeChild(node.firstChild); } }

  function get(path) {
    return fetch(BASE + path, { credentials: 'same-origin' }).then(function (r) {
      if (!r.ok) { throw new Error('HTTP ' + r.status); }
      return r.json();
    });
  }

  function localDay(value) {
    var d = value ? new Date(value) : new Date();
    return d.getFullYear() + '-' + String(d.getMonth() + 1).padStart(2, '0') + '-' + String(d.getDate()).padStart(2, '0');
  }
  function deltaText(iso) {
    if (!iso) { return ''; }
    var seconds = (new Date(iso).getTime() - Date.now()) / 1000;
    if (!isFinite(seconds) || seconds <= 0) { return '现在'; }
    if (seconds < 3600) { return Math.max(1, Math.round(seconds / 60)) + ' 分钟后'; }
    if (seconds < 86400) { return Math.round(seconds / 3600) + ' 小时后'; }
    var days = seconds / 86400;
    if (days < 30) { return Math.round(days) + ' 天后'; }
    return (days / 30.44).toFixed(1) + ' 个月后';
  }
  function shortQuestion(card) {
    var text = (card.question || '').replace(/\s+/g, ' ').trim();
    return text.length > 42 ? text.slice(0, 42) + '…' : (text || '（无题干）');
  }
  function dueLabel(card) {
    if (card.suspended) { return { text: '已归档', alert: false }; }
    var today = localDay(), day = localDay(card.due_at);
    if (day < today) {
      var days = Math.round((new Date(today) - new Date(day)) / 86400000);
      return { text: '逾期 ' + days + ' 天', alert: true };
    }
    if (day === today) { return { text: '今天', alert: false }; }
    var diff = Math.round((new Date(day) - new Date(today)) / 86400000);
    return { text: diff === 1 ? '明天' : diff + ' 天后', alert: false };
  }

  /* ---------------------------------------------------------------- 渲染 */
  function renderHero(panel) {
    var exam = cache.exam || {};
    var stats = cache.stats || {};
    var due = stats.due_now || 0;
    var done = stats.reviewed_today || 0;
    var total = stats.total || 0;
    var suspended = stats.suspended || 0;
    var active = Math.max(0, total - suspended);

    var hero = el('section', undefined, 'mm-hero');

    /* 第一行：压力 —— 倒计时 / 待复习 / 已复习 */
    var head = el('div', undefined, 'mm-head');
    if (exam.enabled) {
      var dday = el('div', undefined, 'mm-dday');
      dday.append(el('span', exam.remaining_days, 'mm-dday-num'));
      var ddayText = el('div', undefined, 'mm-dday-text');
      ddayText.append(el('strong', '天后' + (exam.name || '考试')));
      ddayText.append(el('span', '考试日 ' + (exam.deadline || '—')
        + (exam.study_days ? ' · 可复习 ' + exam.study_days + ' 天' : ''), 'mm-sub'));
      dday.append(ddayText);
      head.append(dday);
    } else {
      head.append(el('div', '未设置考试日期', 'mm-dday-text'));
    }
    var facts = el('div', undefined, 'mm-facts');
    facts.append(metric(String(due), '今天待复习', due > 0));
    facts.append(metric(String(done), '今天已复习', false));
    facts.append(metric(String(active), '在学错题', false));
    head.append(facts);
    hero.append(head);

    /* 第二行：进度条 */
    var todayTotal = due + done;
    var percent = todayTotal > 0 ? Math.round((done / todayTotal) * 100) : 100;
    var progress = el('div', undefined, 'mm-progress');
    var track = el('div', undefined, 'mm-track');
    track.append(el('i'));
    q('i', track).style.width = percent + '%';
    progress.append(track, el('span', '今日复习 ' + done + ' / ' + todayTotal + '　' + percent + '%', 'mm-progress-text'));
    hero.append(progress);

    /* 第三行：唯一的主行动（按状态自适应） */
    var actions = el('div', undefined, 'mm-actions');
    var primary = el('button', undefined, 'mm-cta mm-cta--primary');
    primary.type = 'button';
    var secondary = el('button', undefined, 'mm-cta');
    secondary.type = 'button';

    if (due > 0) {
      primary.textContent = '开始今日复习（' + due + ' 道）';
      primary.addEventListener('click', function () { go('review'); });
      secondary.textContent = '拍照录入错题';
      secondary.addEventListener('click', function () { goUpload(); });
    } else if (total === 0) {
      primary.textContent = '拍一道错题，开始建立复习曲线';
      primary.addEventListener('click', function () { goUpload(); });
      secondary.textContent = '先看看错题专栏';
      secondary.addEventListener('click', function () { go('errors'); });
    } else {
      primary.textContent = '今天没有到期的错题 ✓';
      primary.disabled = true;
      secondary.textContent = '再录一道新错题';
      secondary.addEventListener('click', function () { goUpload(); });
    }
    actions.append(primary, secondary);

    if (due === 0 && done > 0 && stats.next_due_at) {
      actions.append(el('span', '下一批在 ' + deltaText(stats.next_due_at), 'mm-hint'));
    } else if (due === 0 && done === 0 && total > 0) {
      actions.append(el('span', '今天没有排期，可以去复习计划看看未来负荷', 'mm-hint'));
    }
    hero.append(actions);
    panel.append(hero);
  }

  function metric(value, label, highlight) {
    var box = el('div', undefined, 'mm-fact' + (highlight ? ' is-alert' : ''));
    box.append(el('strong', value), el('span', label));
    return box;
  }

  function renderLoad(panel) {
    var series = (cache.forecast && cache.forecast.series) || [];
    if (!series.length) { return; }
    var section = el('section', undefined, 'mm-section');
    var head = el('div', undefined, 'mm-section-head');
    head.append(el('h3', '未来 7 天负荷'));
    var peak = Math.max(0, Math.max.apply(null, series.map(function (p) { return p.count; })));
    head.append(el('span', peak > 0 ? '峰值 ' + peak + ' 道/天' : '近期无到期', 'mm-sub'));
    section.append(head);

    var chart = el('div', undefined, 'mm-chart');
    series.slice(0, 7).forEach(function (point, index) {
      var col = el('div', undefined, 'mm-col' + (index === 0 ? ' is-today' : ''));
      var bar = el('div', undefined, 'mm-bar');
      bar.append(el('i'));
      var height = point.count > 0 && peak > 0 ? Math.max(6, Math.round((point.count / peak) * 46)) : 2;
      q('i', bar).style.height = height + 'px';
      if (point.count > 0) { q('i', bar).classList.add('has-value'); }
      col.append(el('b', point.count > 0 ? point.count : '', 'mm-col-value'), bar,
        el('span', index === 0 ? '今天' : (index === 1 ? '明天' : '+' + index + 'd'), 'mm-col-label'));
      chart.append(col);
    });
    section.append(chart);

    if (cache.exam && cache.exam.load_next_7_days) {
      section.append(el('p', '未来 7 天共 ' + cache.exam.load_next_7_days + ' 道到期，越早清掉越轻松。', 'mm-sub'));
    }
    panel.append(section);
  }

  function renderRecent(panel) {
    var stats = cache.stats || {};
    var section = el('section', undefined, 'mm-section');
    var head = el('div', undefined, 'mm-section-head');
    head.append(el('h3', '最近入库的错题'));
    var more = el('button', '看全部 →', 'mm-link');
    more.type = 'button';
    more.addEventListener('click', function () { go('errors'); });
    head.append(more);
    section.append(head);

    var cards = cache.cards || [];
    if (!cards.length) {
      var empty = el('div', undefined, 'mm-empty');
      empty.append(el('strong', '还没有错题'));
      empty.append(el('p', '上传一份错题 PDF（扫描件或拍照），识别后会自动按遗忘曲线排期。'));
      var cta = el('button', '上传错题 PDF', 'mm-cta mm-cta--primary');
      cta.type = 'button';
      cta.addEventListener('click', function () { goUpload(); });
      empty.append(cta);
      section.append(empty);
      panel.append(section);
      return;
    }

    var list = el('div', undefined, 'mm-list');
    cards.forEach(function (card) {
      var row = el('button', undefined, 'mm-row');
      row.type = 'button';
      var main = el('div', undefined, 'mm-row-main');
      main.append(el('span', shortQuestion(card), 'mm-row-title'));
      var metaParts = [];
      if (card.knowledge_point) { metaParts.push(card.knowledge_point); }
      metaParts.push('已复习 ' + (card.repetitions || 0) + ' 次');
      if (card.lapses) { metaParts.push('错 ' + card.lapses + ' 次'); }
      main.append(el('span', metaParts.join(' · '), 'mm-row-meta'));
      var tag = dueLabel(card);
      row.append(main, el('span', tag.text, 'mm-tag' + (tag.alert ? ' is-alert' : '')));
      row.addEventListener('click', function () {
        if (window.WrongAnswers && window.WrongAnswers.openReview) {
          window.WrongAnswers.openReview(card);
        } else {
          go('review');
        }
      });
      list.append(row);
    });
    section.append(list);

    var foot = el('p', undefined, 'mm-sub');
    var parts = ['错题库 ' + (stats.total || 0) + ' 道'];
    if (stats.suspended) { parts.push('已归档 ' + stats.suspended + ' 道'); }
    if (stats.lapses) { parts.push('累计遗忘 ' + stats.lapses + ' 次'); }
    foot.textContent = parts.join('　·　');
    section.append(foot);
    panel.append(section);
  }

  /* ---------------------------------------------------------------- 交互 */
  function go(page) {
    if (typeof window.showPage === 'function') { window.showPage(page); }
  }
  function goUpload() {
    go('errors');
    setTimeout(function () {
      var drop = document.getElementById('waDrop');
      if (drop) {
        drop.scrollIntoView({ behavior: 'smooth', block: 'center' });
        drop.classList.add('is-flash');
        setTimeout(function () { drop.classList.remove('is-flash'); }, 1400);
      }
    }, 220);
  }

  /* ---------------------------------------------------------------- 挂载 */
  /* 今天没有任何任务时，左列「今天的学习」只是一张空卡片 —— 收掉它，
     让动机面板占满宽度（顶栏状态句已经说明「今天还没有安排」）。 */
  function syncIdleState() {
    var dashboard = q('.today-dashboard');
    if (!dashboard) { return; }
    var events = document.querySelectorAll('#todayTimeline .timeline-event:not(.empty)').length;
    dashboard.classList.toggle('mm-idle', events === 0);
  }

  function render() {
    var workspace = q('[data-view="today"] .today-workspace');
    if (!workspace) { return false; }
    var panel = q('#mmPanel');
    if (!panel) {
      panel = el('div', undefined, 'mm-panel');
      panel.id = 'mmPanel';
      workspace.insertBefore(panel, workspace.firstChild);
    }
    clear(panel);
    renderHero(panel);
    renderLoad(panel);
    renderRecent(panel);
    setTimeout(syncIdleState, 800);      // 等 app.js 自己的 loadToday 填完时间轴
    return true;
  }

  function load() {
    return Promise.all([
      get('/api/exam').catch(function () { return null; }),
      get('/api/stats').catch(function () { return null; }),
      get('/api/forecast?days=7').catch(function () { return null; }),
      get('/api/cards?limit=3').catch(function () { return { cards: [] }; })
    ]).then(function (results) {
      cache.exam = results[0];
      cache.stats = results[1];
      cache.forecast = results[2];
      cache.cards = (results[3] && results[3].cards) || [];
      render();
    });
  }

  function hookRouting() {
    if (typeof window.showPage !== 'function' || window.showPage.__mmHooked) { return; }
    var original = window.showPage;
    var wrapped = function (page) {
      original.apply(this, arguments);
      if (page === 'today') { load(); setTimeout(syncIdleState, 700); }
      // 从错题页复习完回到今日，数字要跟着变
      if (page === 'today' && window.refreshPageStatus) { window.refreshPageStatus(); }
    };
    wrapped.__mmHooked = true;
    window.showPage = wrapped;
  }

  function boot() {
    if (!render()) { setTimeout(boot, 200); return; }
    hookRouting();
    load();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', boot);
  } else {
    boot();
  }
  window.LearningMomentum = { reload: load, syncIdle: syncIdleState };
})();
