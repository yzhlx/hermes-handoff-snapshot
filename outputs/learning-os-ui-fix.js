/* ============================================================================
   主站界面修复层（learning-os-ui-fix.js）
   由 tools/redesign-ui-js.py 生成。加载在 app.js 之后，只做三件事：

     1. 顶栏标题改成「页名」，并在下面填一行可执行的状态句（替代原来的重复标题）
     2. 把每个空状态升级成「图标 + 标题 + 解释 + 一个按钮」
     3. 把「拍照快速录入」提为主行动按钮

   实现方式是包装 showPage + 观察 DOM，**不修改 app.js 一行**，
   所以要回滚只需删掉 index 里的一个 <script> 标签。
   ========================================================================== */
(function () {
  'use strict';

  var PAGE_NAMES = {
    today: '今日', plan: '周计划', errors: '错题专栏', review: '每日复习',
    chat: 'AI 对话', records: '学习记录', settings: '设置'
  };

  /* 每个空状态容器：给一个标题 + 一个明确的下一步按钮 */
  var EMPTY_ACTIONS = [
    { sel: '#todayTimeline', item: '.timeline-event:not(.empty)', icon: '☀',
      title: '今天还没有安排', quiet: true,
      cta: { label: '新增任务', page: 'plan' } },
    { sel: '#nextTasks', item: '.list-item', icon: '☰',
      title: '还没有候选任务',
      cta: { label: '去周计划安排', page: 'plan' } },
    { sel: '#taskList', item: '.planner-task-item', icon: '□',
      title: '当天还没有任务', quiet: true,
      cta: { label: '填写下面的表单', click: '#taskForm input, #taskForm textarea' } },
    { sel: '#reviewList', item: '.review-card', icon: '✓',
      title: '今天没有到期的错题',
      cta: { label: '去录入一道错题', page: 'errors' } },
    { sel: '#errorList', item: '.error-note-card', icon: '◇',
      title: '错题本还是空的',
      cta: { label: '拍照快速录入', dialog: 'quickErrorDialog' } },
    { sel: '#chatList', item: '.chat-history-item', icon: '✦',
      title: '还没有对话',
      cta: { label: '新建对话', click: '#newChat' } },
    { sel: '#statusSummary', item: '.status-chip, .list-item', icon: '◎',
      title: '还没有记录当前状态',
      cta: { label: '记录当前状态', click: '#statusButton' } },
    { sel: '#subjectStats', item: '.list-item', icon: '▤',
      title: '暂无学科数据', quiet: true,
      cta: { label: '去录入错题', page: 'errors' } },
    { sel: '#chapterStats', item: '.list-item', icon: '▤',
      title: '暂无章节数据', quiet: true,
      cta: { label: '去录入错题', page: 'errors' } },
    { sel: '#typeStats', item: '.list-item', icon: '▤',
      title: '暂无错误类型数据', quiet: true,
      cta: { label: '去录入错题', page: 'errors' } }
  ];

  function q(selector) { return document.querySelector(selector); }
  function count(selector, item) {
    var box = q(selector);
    return box ? box.querySelectorAll(item).length : 0;
  }
  function esc(text) {
    return String(text == null ? '' : text)
      .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

  /* ---------- 状态句：页名下面那行「现在该干什么」 ---------- */
  function statusFor(page) {
    if (page === 'review') {
      var due = count('#reviewList', '.review-card');
      return due
        ? '<span class="ps-strong">' + due + ' 道待复习</span><span>·</span><span>一次只复盘一题</span>'
        : '<span>今天没有到期的错题</span><span>·</span><span>录入新错题后会自动排进复习曲线</span>';
    }
    if (page === 'errors') {
      var notes = count('#errorList', '.error-note-card');
      return notes
        ? '<span class="ps-strong">错题本 ' + notes + ' 条</span><span>·</span><span>先补全证据，再让它进复习</span>'
        : '<span>错题本还是空的</span><span>·</span><span>用右上角「拍照快速录入」收第一道</span>';
    }
    if (page === 'today') {
      var items = count('#todayTimeline', '.timeline-event:not(.empty)');
      return items
        ? '<span class="ps-strong">今天 ' + items + ' 项安排</span><span>·</span><span>先做最重要的一件</span>'
        : '<span>今天还没有安排</span><span>·</span><span>先定下最重要的一步</span>';
    }
    if (page === 'plan') {
      var planned = count('#taskList', '.planner-task-item');
      return planned
        ? '<span class="ps-strong">当天 ' + planned + ' 项</span><span>·</span><span>建议每周不超过 2 项核心任务</span>'
        : '<span>当天还没有任务</span><span>·</span><span>从下面「新增任务」写下一步可完成的事</span>';
    }
    if (page === 'records') {
      var rows = count('#subjectStats', '.list-item') + count('#chapterStats', '.list-item') + count('#typeStats', '.list-item');
      return rows
        ? '<span>按学科 / 章节 / 错误类型统计</span>'
        : '<span>还没有可统计的学习记录</span><span>·</span><span>录入错题并复盘后这里会出现图表</span>';
    }
    if (page === 'chat') { return '<span>对话保存在本机</span><span>·</span><span>可以问「现在该复习什么」</span>'; }
    if (page === 'settings') { return '<span>AI 配置与密钥只保存在本机</span>'; }
    return '';
  }

  function refreshStatus() {
    var page = (document.querySelector('.page.active') || {}).dataset;
    var name = page ? page.view : 'today';
    var title = q('#pageTitle');
    if (title && PAGE_NAMES[name]) { title.textContent = PAGE_NAMES[name]; }
    var status = q('#pageStatus');
    // 错题专栏 / 每日复习 的状态句由错题模块接管（它拿得到真实统计），这里不覆盖
    var waOwns = window.WrongAnswers && (name === 'errors' || name === 'review');
    if (status && !waOwns) { status.innerHTML = statusFor(name); }

    var badge = q('#navReviewBadge');
    if (badge) {
      var due = count('#reviewList', '.review-card');
      badge.hidden = due === 0;
      badge.textContent = due ? String(due) : '';
    }
  }

  /* ---------- 空状态升级：图标 + 标题 + 解释 + 一个按钮 ---------- */
  function wireCta(button, cta) {
    button.addEventListener('click', function () {
      if (cta.page && typeof window.showPage === 'function') { window.showPage(cta.page); return; }
      if (cta.dialog) { var d = document.getElementById(cta.dialog); if (d && d.showModal) { d.showModal(); } return; }
      if (cta.click) { var target = q(cta.click); if (target) { target.click(); } }
    });
  }

  function decorateEmptyStates() {
    EMPTY_ACTIONS.forEach(function (cfg) {
      var container = q(cfg.sel);
      if (!container) { return; }
      if (container.querySelector(cfg.item) || count(cfg.sel, cfg.item) > 0) { return; }   // 有内容就不动
      var empty = container.querySelector('.empty, .timeline-event.empty, .chat-empty-state');
      if (!empty || empty.dataset.upgraded === '1') { return; }

      var sentence = (empty.textContent || '').replace(/\s+/g, ' ').trim();
      // 去掉与标题重复的开头，避免「今天还没有安排 / 今天还没有安排」
      if (sentence.indexOf(cfg.title) === 0) { sentence = sentence.slice(cfg.title.length).replace(/^[\s。·,，]+/, ''); }
      if (!sentence || sentence === cfg.title) { sentence = ''; }

      empty.innerHTML =
        '<div class="empty-icon" aria-hidden="true">' + esc(cfg.icon || '○') + '</div>' +
        '<strong>' + esc(cfg.title) + '</strong>' +
        (sentence ? '<p>' + esc(sentence) + '</p>' : '');
      empty.dataset.upgraded = '1';
      empty.classList.toggle('empty--quiet', !!cfg.quiet);

      var action = cfg.cta;
      if (action && action.label) {
        var button = document.createElement('button');
        button.type = 'button';
        button.className = 'empty-cta' + (cfg.quiet ? ' is-quiet' : '');
        button.textContent = action.label;
        wireCta(button, action);
        empty.appendChild(button);
      }
    });
  }

  /* ---------- 「拍照快速录入」提为主行动 ---------- */
  function promoteCaptureButton() {
    var panel = q('[data-view="errors"] .page-heading');
    if (!panel) { return; }
    var button = panel.querySelector('button');
    if (button && button.className.indexOf('capture-primary') === -1) {
      button.className = 'capture-primary';
      button.setAttribute('title', '拍照或上传图片，自动识别成错题');
    }
  }

  /* ---------- 清掉残留的英文装饰标签（如「TODAY'S MISSION · 等待安排」） ---------- */
  var LABEL_SELECTORS = ['.eyebrow', '.review-due-note', '.chat-status', '.date-chip + *', '.task-meta small'];
  var LATIN_ONLY = /^[A-Z0-9][A-Z0-9'’&·\s.\-]*$/;

  function stripLatinKickers() {
    LABEL_SELECTORS.forEach(function (selector) {
      Array.prototype.forEach.call(document.querySelectorAll(selector), function (node) {
        if (node.dataset.stripped === '1') { return; }
        var text = (node.textContent || '').trim();
        if (!text) { return; }
        node.dataset.stripped = '1';
        // 整条都是英文大写 → 纯装饰，直接隐藏
        if (LATIN_ONLY.test(text)) { node.hidden = true; return; }
        // 「ENGLISH · 中文」→ 只留中文
        var parts = text.split(/\s*[·|]\s*/);
        if (parts.length > 1 && LATIN_ONLY.test(parts[0])) {
          node.textContent = parts.slice(1).join(' · ').trim();
        } else {
          var match = text.match(/^([A-Z0-9][A-Z0-9'’&\s.\-]+?)\s+(?=[\u4e00-\u9fa5])/);
          if (match) { node.textContent = text.slice(match[0].length).trim(); }
        }
      });
    });
  }

  /* ---------- 手机端「更多」抽屉：把 3 个次要页面收进底栏第 5 格 ---------- */
  function buildMoreSheet() {
    if (document.querySelector('.nav-more-sheet')) { return; }
    var PRIMARY = ['today', 'review', 'errors', 'plan'];
    // app.js 会动态往侧栏 append 一个「手写画布」按钮（data-action，不是 data-page），
    // 手机端必须一起收进抽屉，否则底栏会变成两行、第三行溢出屏幕。
    Array.prototype.forEach.call(document.querySelectorAll('.main-nav button'), function (button) {
      if (PRIMARY.indexOf(button.dataset.page) < 0) { button.classList.add('nav-more'); }
    });

    var sheet = document.createElement('div');
    sheet.className = 'nav-more-sheet';
    sheet.setAttribute('role', 'menu');
    Array.prototype.forEach.call(document.querySelectorAll('.main-nav button.nav-more'), function (button) {
      var clone = button.cloneNode(true);
      clone.classList.remove('nav-more');
      clone.addEventListener('click', function () {
        sheet.classList.remove('is-open');
        var sep = document.querySelector('.main-nav .nav-sep');
        if (sep) { sep.classList.remove('on'); }
        button.click();          // 复用原按钮已有的处理逻辑（页面或手写画布动作）
      });
      sheet.appendChild(clone);
    });
    document.body.appendChild(sheet);

    var sep = document.querySelector('.main-nav .nav-sep');
    if (sep && !sep.dataset.wired) {
      sep.dataset.wired = '1';
      sep.setAttribute('role', 'button');
      sep.setAttribute('tabindex', '0');
      sep.addEventListener('click', function (event) {
        event.stopPropagation();
        var open = sheet.classList.toggle('is-open');
        sep.classList.toggle('on', open);
      });
      sep.addEventListener('keydown', function (event) {
        if (event.key === 'Enter' || event.key === ' ') { event.preventDefault(); sep.click(); }
      });
    }
    document.addEventListener('click', function (event) {
      if (!sheet.classList.contains('is-open')) { return; }
      if (sheet.contains(event.target) || event.target.closest('.nav-sep')) { return; }
      sheet.classList.remove('is-open');
      var sep2 = document.querySelector('.main-nav .nav-sep');
      if (sep2) { sep2.classList.remove('on'); }
    });
  }

  /* ---------- 观察 DOM：页面切换与数据回填都会触发 ---------- */
  var pending = null;
  function schedule() {
    if (pending) { clearTimeout(pending); }
    pending = setTimeout(function () {
      pending = null;
      stripLatinKickers();
      decorateEmptyStates();
      promoteCaptureButton();
      buildMoreSheet();
      refreshStatus();
    }, 60);
  }

  function start() {
    var root = q('.content') || document.body;
    new MutationObserver(schedule).observe(root, { childList: true, subtree: true });
    schedule();
    window.addEventListener('load', schedule);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', start);
  } else {
    start();
  }
  window.refreshPageStatus = refreshStatus;    // 便于手工触发与自测
})();
