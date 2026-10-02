/* ============================================================================
   错题系统原生集成（learning-os-wrong-answers.js）
   由 tools/redesign-wrong-answers.py 生成。

   把主站的「错题专栏」与「每日复习」换成后开发的错题系统：
     POST   /cuoti/api/pdfs                  上传 PDF（扫描件/拍照）
     GET    /cuoti/api/pdfs                  导入队列状态
     GET    /cuoti/api/cards                 错题库
     PATCH  /cuoti/api/cards/{id}            修正
     DELETE /cuoti/api/cards/{id}            删除
     POST   /cuoti/api/cards/{id}/suspend    归档 / 恢复
     GET    /cuoti/api/queue                 今日待复习
     POST   /cuoti/api/cards/{id}/review     四档自评 → 排下次复习
     GET    /cuoti/api/stats                 统计

   同域同门禁，所以直接用相对路径，cookie 自动带上，无跨域问题。
   旧页面的 DOM 不删除、只隐藏（旧 JS 仍会给它填空，删了会 NullReference）。
   ========================================================================== */
(function () {
  'use strict';

  var BASE = '/cuoti';
  var state = {
    cards: [], sources: [], queue: [], index: 0,
    filter: { subject: '', search: '', sort: 'due' },
    rating: 0, busy: false, pollTimer: null, mounted: false
  };

  /* ---------------------------------------------------------------- 基础工具 */
  function h(tag, text, className) {
    var node = document.createElement(tag);
    if (text !== undefined && text !== null) { node.textContent = String(text); }
    if (className) { node.className = className; }
    return node;
  }
  function clear(node) { while (node && node.firstChild) { node.removeChild(node.firstChild); } }

  function esc(text) {
    return String(text == null ? '' : text)
      .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  }
  function qs(selector, root) { return (root || document).querySelector(selector); }

  function toast(message) {
    if (typeof window.notify === 'function') { window.notify(message); return; }
    var box = qs('#notice');
    if (box) { box.textContent = message; box.hidden = false; setTimeout(function () { box.hidden = true; }, 2600); }
  }

  function api(path, options) {
    options = options || {};
    var init = { method: options.method || 'GET', credentials: 'same-origin' };
    if (options.body instanceof FormData) { init.body = options.body; }
    else if (options.body !== undefined) {
      init.headers = { 'Content-Type': 'application/json' };
      init.body = JSON.stringify(options.body);
    }
    return fetch(BASE + path, init).then(function (response) {
      return response.text().then(function (text) {
        var payload = null;
        try { payload = text ? JSON.parse(text) : null; } catch (error) { payload = null; }
        if (!response.ok) {
          var detail = payload && payload.detail ? payload.detail : ('请求失败（HTTP ' + response.status + '）');
          throw new Error(typeof detail === 'string' ? detail : '请求失败');
        }
        return payload;
      });
    }).catch(function (error) {
      if (error instanceof TypeError) { throw new Error('连接不上错题服务，请稍后重试。'); }
      throw error;
    });
  }

  /* 日期与标签：与错题服务自身的口径保持一致 */
  function localDay(value) {
    var d = value ? new Date(value) : new Date();
    return d.getFullYear() + '-' + String(d.getMonth() + 1).padStart(2, '0') + '-' + String(d.getDate()).padStart(2, '0');
  }
  function deltaText(iso) {
    if (!iso) { return '—'; }
    var seconds = (new Date(iso).getTime() - Date.now()) / 1000;
    if (!isFinite(seconds)) { return '—'; }
    if (seconds <= 0) { return '现在'; }
    if (seconds < 3600) { return Math.max(1, Math.round(seconds / 60)) + ' 分钟后'; }
    if (seconds < 86400) { return Math.round(seconds / 3600) + ' 小时后'; }
    var days = seconds / 86400;
    if (days < 90) { return Math.round(days) + ' 天后'; }
    var months = days / 30.44;
    if (months < 12) { return months.toFixed(1) + ' 个月后'; }
    return (months / 12).toFixed(1) + ' 年后';
  }
  function dueTag(card) {
    if (card.suspended) { return { text: '已归档', cls: 'wa-tag' }; }
    var today = localDay(), day = localDay(card.due_at);
    if (day < today) {
      var days = Math.round((new Date(today) - new Date(day)) / 86400000);
      return { text: '逾期 ' + days + ' 天', cls: 'wa-tag wa-tag--alert' };
    }
    if (day === today) { return { text: '今天', cls: 'wa-tag wa-tag--due' }; }
    var diff = Math.round((new Date(day) - new Date(today)) / 86400000);
    return { text: diff === 1 ? '明天' : (diff + ' 天后'), cls: 'wa-tag' };
  }
  function shortTitle(card) {
    var text = (card.question || '').replace(/\s+/g, ' ').trim();
    return text.length > 54 ? text.slice(0, 54) + '…' : (text || '（无题干）');
  }
  function dueSort(a, b) { return new Date(a.due_at || 0) - new Date(b.due_at || 0); }

  /* ---------------------------------------------------------------- 错题专栏 */
  function buildShell() {
    var shell = h('div', undefined, 'wa-shell');

    var upload = h('section', undefined, 'wa-card wa-upload');
    upload.append(h('div', undefined, 'wa-card-title'));
    qs('.wa-card-title', upload).append(h('strong', '上传错题 PDF'), h('span', '扫描件、拍照导出、电子版都行；自动识别成卡片并按遗忘曲线排期', 'wa-sub'));
    var drop = h('div', undefined, 'wa-drop');
    drop.tabIndex = 0;
    drop.innerHTML = '<div class="wa-drop-icon" aria-hidden="true">＋</div>' +
      '<strong>把 PDF 拖到这里</strong><p>或者点击选择文件 · 单个不超过 60MB</p>';
    var input = document.createElement('input');
    input.type = 'file';
    input.accept = 'application/pdf,.pdf';
    input.multiple = true;
    input.className = 'wa-file-input';
    upload.append(drop, input);
    var queue = h('div', undefined, 'wa-queue');
    upload.append(queue);

    var listSection = h('section', undefined, 'wa-card wa-list-card');
    var head = h('div', undefined, 'wa-list-head');
    var headTitle = h('div', undefined, 'wa-card-title');
    headTitle.append(h('strong', '错题库'), h('span', '按下次复习时间排序', 'wa-sub'));
    head.append(headTitle);
    var tools = h('div', undefined, 'wa-list-tools');
    var search = document.createElement('input');
    search.type = 'search';
    search.placeholder = '搜索题干 / 出处 / 知识点';
    search.className = 'wa-search';
    var subjects = h('div', undefined, 'wa-tabs');
    tools.append(search, subjects);
    head.append(tools);
    var listBody = h('div', undefined, 'wa-list-body');
    listSection.append(head, listBody);

    shell.append(upload, listSection);
    return { shell: shell, drop: drop, input: input, queue: queue, listBody: listBody, subjects: subjects, search: search };
  }

  function renderUploadQueue() {
    var box = qs('#waUploadQueue');
    if (!box) { return; }
    clear(box);
    if (!state.sources.length) { return; }
    state.sources.slice(0, 6).forEach(function (source) {
      var row = h('div', undefined, 'wa-queue-item');
      row.append(h('div', undefined, 'wa-queue-icon'));
      qs('.wa-queue-icon', row).textContent = 'PDF';
      var main = h('div', undefined, 'wa-queue-main');
      main.append(h('div', source.filename, 'wa-queue-name'));
      var statusMap = {
        pending: ['排队中', 'wa-tag'], processing: ['识别中', 'wa-tag wa-tag--due'],
        ready: ['已完成', 'wa-tag wa-tag--ok'], failed: ['失败', 'wa-tag wa-tag--alert']
      };
      var info = statusMap[source.status] || [source.status, 'wa-tag'];
      if (source.status === 'ready') {
        main.append(h('p', source.page_count + ' 页 → ' + (source.card_count || 0) + ' 道题已入库', 'wa-queue-meta'));
      } else if (source.status === 'failed') {
        main.append(h('p', source.message || '识别失败', 'wa-queue-meta'));
      } else {
        main.append(h('p', source.message || '正在识别，完成后会自动出现在错题库', 'wa-queue-meta'));
        var bar = h('div', undefined, 'wa-bar');
        bar.append(h('i'));
        qs('i', bar).style.width = source.status === 'processing' ? '55%' : '12%';
        main.append(bar);
      }
      row.append(main, h('span', info[0], info[1]));
      if (source.status === 'failed') {
        var retry = h('button', '重试', 'wa-btn wa-btn--ghost wa-btn--sm');
        retry.type = 'button';
        retry.addEventListener('click', function () {
          api('/api/pdfs/' + source.id + '/reprocess', { method: 'POST' })
            .then(function () { toast('已重新排队识别'); startPolling(); })
            .catch(function (error) { toast(error.message); });
        });
        row.append(retry);
      }
      box.append(row);
    });
  }

  function uploadFiles(files) {
    var pdfs = Array.prototype.filter.call(files, function (file) {
      return /\.pdf$/i.test(file.name);
    });
    if (!pdfs.length) { toast('请选择 .pdf 文件'); return; }
    var box = qs('#waUploadQueue');
    if (box) { clear(box); box.append(h('p', '正在上传 ' + pdfs.length + ' 个文件…', 'wa-queue-meta')); }

    var chain = Promise.resolve();
    pdfs.forEach(function (file) {
      chain = chain.then(function () {
        var form = new FormData();
        form.append('file', file);
        return api('/api/pdfs', { method: 'POST', body: form }).then(function (payload) {
          if (payload && payload.duplicate) { toast(payload.message || '这个 PDF 已经传过了'); }
        }).catch(function (error) { toast(file.name + '：' + error.message); });
      });
    });
    chain.then(function () {
      toast('已提交，识别完成后自动进入错题库');
      startPolling();
      return loadSources();
    });
  }

  function startPolling() {
    if (state.pollTimer) { clearInterval(state.pollTimer); }
    var ticks = 0;
    state.pollTimer = setInterval(function () {
      ticks += 1;
      loadSources().then(function (sources) {
        var pending = sources.some(function (s) { return s.status === 'pending' || s.status === 'processing'; });
        if (!pending || ticks > 90) {
          clearInterval(state.pollTimer);
          state.pollTimer = null;
          if (!pending) { loadCards(); loadStatusLine(); }
        }
      });
    }, 2500);
  }

  function loadSources() {
    return api('/api/pdfs').then(function (payload) {
      state.sources = (payload && payload.sources) || [];
      renderUploadQueue();
      return state.sources;
    }).catch(function () { return []; });
  }

  function renderSubjects() {
    var tabs = qs('#waSubjects');
    if (!tabs) { return; }
    clear(tabs);
    var active = state.cards.filter(function (card) { return !card.suspended; });
    var counts = {};
    active.forEach(function (card) { var key = card.subject || '未分类'; counts[key] = (counts[key] || 0) + 1; });
    var make = function (label, value) {
      var button = h('button', label, 'wa-tab' + (state.filter.subject === value ? ' active' : ''));
      button.type = 'button';
      button.addEventListener('click', function () {
        state.filter.subject = value;
        renderSubjects();
        renderCards();
      });
      return button;
    };
    tabs.append(make('全部 ' + active.length, ''));
    Object.keys(counts).sort().forEach(function (subject) { tabs.append(make(subject + ' ' + counts[subject], subject)); });
  }

  function filteredCards() {
    var cards = state.cards.filter(function (card) { return !card.suspended; });
    if (state.filter.subject) { cards = cards.filter(function (c) { return (c.subject || '未分类') === state.filter.subject; }); }
    if (state.filter.search) {
      var needle = state.filter.search.toLowerCase();
      cards = cards.filter(function (card) {
        return [card.question, card.source_ref, card.knowledge_point, card.solution_idea, card.note]
          .some(function (field) { return (field || '').toLowerCase().indexOf(needle) >= 0; });
      });
    }
    if (state.filter.sort === 'lapses') { cards.sort(function (a, b) { return (b.lapses || 0) - (a.lapses || 0); }); }
    else if (state.filter.sort === 'created') { cards.sort(function (a, b) { return new Date(b.created_at || 0) - new Date(a.created_at || 0); }); }
    else { cards.sort(dueSort); }
    return cards;
  }

  function renderCards() {
    var body = qs('#waListBody');
    if (!body) { return; }
    clear(body);
    var cards = filteredCards();
    if (!cards.length) {
      var empty = h('div', undefined, 'wa-empty');
      empty.append(h('div', undefined, 'wa-empty-icon'));
      qs('.wa-empty-icon', empty).textContent = '◇';
      var filtered = state.filter.subject || state.filter.search;
      if (!state.cards.length) {
        empty.append(h('strong', '错题库还是空的'));
        empty.append(h('p', '上传一份错题 PDF，识别后会自动出现在这里并按遗忘曲线排期。'));
      } else if (filtered) {
        empty.append(h('strong', '没有符合条件的错题'));
        empty.append(h('p', '换个科目或清空搜索试试。'));
      } else {
        empty.append(h('strong', state.cards.length + ' 张错题都已归档'));
        empty.append(h('p', '归档的错题不推送复习。需要复习时恢复归档，或上传新错题即可出现在这里。'));
      }
      var cta = h('button', '上传错题 PDF', 'wa-btn wa-btn--primary');
      cta.type = 'button';
      cta.addEventListener('click', function () {
        var drop = qs('#waDrop');
        if (drop) { drop.scrollIntoView({ behavior: 'smooth', block: 'center' }); drop.classList.add('is-flash'); setTimeout(function () { drop.classList.remove('is-flash'); }, 1200); }
      });
      empty.append(cta);
      body.append(empty);
      return;
    }
    cards.forEach(function (card) {
      var row = h('article', undefined, 'wa-row');
      var main = h('div', undefined, 'wa-row-main');
      main.append(h('div', shortTitle(card), 'wa-row-title'));
      var meta = h('div', undefined, 'wa-row-meta');
      if (card.knowledge_point) { meta.append(h('span', card.knowledge_point, 'wa-tag wa-tag--kp')); }
      if (card.source_ref) { meta.append(h('span', card.source_ref, 'wa-tag')); }
      if (card.lapses) { meta.append(h('span', '错 ' + card.lapses + ' 次', 'wa-tag wa-tag--alert')); }
      meta.append(h('span', '已复习 ' + (card.repetitions || 0) + ' 次', 'wa-tag'));
      main.append(meta);
      var tag = dueTag(card);
      row.append(main, h('span', tag.text, tag.cls));

      var ops = h('div', undefined, 'wa-row-ops');
      var review = h('button', '复盘', 'wa-btn wa-btn--primary wa-btn--sm');
      review.type = 'button';
      review.addEventListener('click', function () { openReview(card); });
      var archive = h('button', '归档', 'wa-btn wa-btn--ghost wa-btn--sm');
      archive.type = 'button';
      archive.addEventListener('click', function () {
        api('/api/cards/' + card.id + '/suspend', { method: 'POST', body: { suspended: true } })
          .then(function () { toast('已归档，不再推送'); return loadCards(); })
          .then(loadStatusLine)
          .catch(function (error) { toast(error.message); });
      });
      var remove = h('button', '删除', 'wa-btn wa-btn--ghost wa-btn--sm');
      remove.type = 'button';
      remove.addEventListener('click', function () {
        if (!window.confirm('删除「' + shortTitle(card) + '」？不可恢复。')) { return; }
        api('/api/cards/' + card.id, { method: 'DELETE' })
          .then(function () { toast('已删除'); return loadCards(); })
          .then(loadStatusLine)
          .catch(function (error) { toast(error.message); });
      });
      ops.append(review, archive, remove);
      row.append(ops);
      body.append(row);
    });
  }

  function loadCards() {
    var body = qs('#waListBody');
    if (body && !state.cards.length) { body.innerHTML = '<div class="wa-skeleton"></div><div class="wa-skeleton"></div><div class="wa-skeleton"></div>'; }
    return api('/api/cards?limit=500').then(function (payload) {
      state.cards = (payload && payload.cards) || [];
      renderSubjects();
      renderCards();
      return state.cards;
    }).catch(function (error) {
      if (body) { clear(body); body.append(h('p', '读取错题库失败：' + error.message, 'wa-queue-meta')); }
      return [];
    });
  }

  /* ---------------------------------------------------------------- 每日复习 */
  function buildReviewShell() {
    var shell = h('div', undefined, 'wa-review-shell');
    var head = h('div', undefined, 'wa-review-head');
    var progress = h('div', undefined, 'wa-progress');
    progress.append(h('span', '—', 'wa-progress-text'), h('div', undefined, 'wa-progress-track'));
    qs('.wa-progress-track', progress).append(h('i'));
    head.append(progress);
    var actions = h('div', undefined, 'wa-review-actions');
    var refresh = h('button', '换一批', 'wa-btn wa-btn--ghost wa-btn--sm');
    refresh.type = 'button';
    refresh.addEventListener('click', function () { loadQueue(); });
    actions.append(refresh);
    head.append(actions);
    var body = h('div', undefined, 'wa-review-body');
    shell.append(head, body);
    return { shell: shell, body: body, progress: progress };
  }

  function renderReviewProgress() {
    var total = state.queue.length;
    var text = qs('.wa-progress-text');
    var fill = qs('.wa-progress-track i');
    if (text) {
      text.textContent = state.custom ? '单卡复盘（来自错题库）'
        : (total ? '第 ' + Math.min(state.index + 1, total) + ' / ' + total + ' 道' : '—');
    }
    if (fill) { fill.style.width = total ? Math.round((state.index / total) * 100) + '%' : '0%'; }
  }

  function currentCard() { return state.custom || state.queue[state.index] || null; }

  function renderReview() {
    var body = qs('#waReviewBody');
    if (!body) { return; }
    clear(body);
    state.rating = 0;
    renderReviewProgress();

    var card = currentCard();
    if (!card) {
      var empty = h('div', undefined, 'wa-empty');
      empty.append(h('div', undefined, 'wa-empty-icon'));
      qs('.wa-empty-icon', empty).textContent = '✓';
      empty.append(h('strong', '今天没有到期的错题'));
      var stats = state.stats || {};
      empty.append(h('p', stats.next_due_at
        ? '下一批在 ' + deltaText(stats.next_due_at) + '，遗忘曲线已经排好了。'
        : '上传错题后会按遗忘曲线自动排期。'));
      var ctaRow = h('div', undefined, 'wa-empty-actions');
      var cta = h('button', '去错题专栏', 'wa-btn wa-btn--primary');
      cta.type = 'button';
      cta.addEventListener('click', function () { if (typeof window.showPage === 'function') { window.showPage('errors'); } });
      var ctaUpload = h('button', '上传新错题', 'wa-btn wa-btn--ghost');
      ctaUpload.type = 'button';
      ctaUpload.addEventListener('click', function () {
        if (typeof window.showPage === 'function') { window.showPage('errors'); }
        setTimeout(function () {
          var drop = qs('#waDrop');
          if (drop) { drop.scrollIntoView({ behavior: 'smooth', block: 'center' }); drop.classList.add('is-flash'); setTimeout(function () { drop.classList.remove('is-flash'); }, 1200); }
        }, 400);
      });
      ctaRow.append(cta, ctaUpload);
      empty.append(ctaRow);
      body.append(empty);
      return;
    }

    var cardBox = h('article', undefined, 'wa-review-card');
    var tags = h('div', undefined, 'wa-row-meta');
    if (card.subject) { tags.append(h('span', card.chapter ? card.subject + ' · ' + card.chapter : card.subject, 'wa-tag wa-tag--kp')); }
    tags.append(h('span', '第 ' + ((card.repetitions || 0) + 1) + ' 次复习', 'wa-tag'));
    if (card.lapses) { tags.append(h('span', '错 ' + card.lapses + ' 次', 'wa-tag wa-tag--alert')); }
    cardBox.append(tags);
    var stem = h('div', undefined, 'wa-stem');
    (card.question || '').split(/\n+/).filter(function (line) { return line.trim(); })
      .forEach(function (line) { stem.append(h('p', line)); });
    cardBox.append(stem);
    if (card.page_image) {
      var figure = h('figure', undefined, 'wa-scan');
      var img = document.createElement('img');
      img.src = card.page_image;
      img.alt = '原扫描页';
      img.loading = 'lazy';
      figure.append(img, h('figcaption', '原扫描页（可对照核对识别结果）'));
      cardBox.append(figure);
    }
    cardBox.append(h('p', '本页不显示答案 —— 主动回忆比重看答案有效得多。', 'wa-hint'));

    var rateRow = h('div', undefined, 'wa-rate-row');
    var labels = { 1: '重来', 2: '困难', 3: '良好', 4: '轻松' };
    var keys = { 1: 'again', 2: 'hard', 3: 'good', 4: 'easy' };
    var capped = card.preview_capped || [];
    [1, 2, 3, 4].forEach(function (value) {
      var button = h('button', undefined, 'wa-rate');
      button.type = 'button';
      button.append(h('b', labels[value]), h('span', (card.preview && card.preview[keys[value]]) || '—'));
      if (capped.indexOf(keys[value]) >= 0) { button.classList.add('is-capped'); }
      button.addEventListener('click', function () {
        state.rating = value;
        Array.prototype.forEach.call(document.querySelectorAll('.wa-rate'), function (node) { node.classList.toggle('on', node === button); });
      });
      rateRow.append(button);
    });
    cardBox.append(rateRow);

    var foot = h('div', undefined, 'wa-review-foot');
    var hint = h('span', '先在心里答一遍，再选自评', 'wa-hint');
    var skip = h('button', '跳过', 'wa-btn wa-btn--ghost');
    skip.type = 'button';
    skip.addEventListener('click', function () { advance(); });
    var save = h('button', '保存并下一道', 'wa-btn wa-btn--primary');
    save.type = 'button';
    save.addEventListener('click', function () {
      if (!state.rating) { toast('先选一个回忆自评（重来 / 困难 / 良好 / 轻松）'); return; }
      if (state.busy) { return; }
      state.busy = true;
      save.disabled = true;
      save.textContent = '正在排期…';
      api('/api/cards/' + card.id + '/review', { method: 'POST', body: { rating: state.rating } })
        .then(function (payload) {
          state.stats = payload.stats || state.stats;
          toast('已排期：' + deltaText(payload.card && payload.card.due_at));
          advance();
        })
        .catch(function (error) { toast(error.message); })
        .then(function () {
          state.busy = false;
          if (save.isConnected) { save.disabled = false; save.textContent = '保存并下一道'; }
        });
    });
    foot.append(hint, skip, save);
    cardBox.append(foot);
    body.append(cardBox);
  }

  function advance() {
    if (state.custom) { state.custom = null; renderReview(); return; }
    state.index += 1;
    if (state.index >= state.queue.length) {
      loadQueue().then(function () { state.index = 0; renderReview(); });
      return;
    }
    renderReview();
  }

  function openReview(card) {
    state.custom = card;
    if (typeof window.showPage === 'function') { window.showPage('review'); }
    renderReview();
  }

  function loadQueue() {
    var body = qs('#waReviewBody');
    if (body && !state.queue.length) { body.innerHTML = '<div class="wa-skeleton wa-skeleton--tall"></div>'; }
    return api('/api/queue?limit=200').then(function (payload) {
      state.queue = (payload && payload.cards) || [];
      state.stats = (payload && payload.stats) || state.stats;
      state.custom = null;
      if (state.index >= state.queue.length) { state.index = 0; }
      renderReview();
      return state.queue;
    }).catch(function (error) {
      if (body) { clear(body); body.append(h('p', '读取复习队列失败：' + error.message, 'wa-queue-meta')); }
      return [];
    });
  }

  /* ---------------------------------------------------------------- 状态句
     错题专栏 / 每日复习 的状态句由本模块接管（它才拿得到真实数据），
     写进顶栏那个统一的 #pageStatus，避免和界面修复层重复显示两行。        */
  function writeStatus(html) {
    var status = qs('#pageStatus');
    if (!status) { return; }
    var active = qs('.page.active');
    var page = active && active.dataset ? active.dataset.view : '';
    if (page === 'errors' || page === 'review') { status.innerHTML = html; }
    window.__waStatusOwned = page === 'errors' || page === 'review';
  }

  function loadStatusLine() {
    return api('/api/stats').then(function (stats) {
      state.stats = stats;
      var total = stats.total || 0;
      var suspendedCount = stats.suspended || 0;
      var active = total - suspendedCount;
      var due = stats.due_now || 0;
      var activePage = qs('.page.active');
      var page = activePage && activePage.dataset ? activePage.dataset.view : '';

      if (page === 'review') {
        writeStatus(due
          ? '<span class="ps-strong">' + due + ' 道待复习</span><span>·</span><span>只看题面先回忆，再选自评</span>'
          : '<span>今天没有到期的错题</span>'
            + (stats.next_due_at ? '<span>·</span><span>下一批在 ' + esc(deltaText(stats.next_due_at)) + '</span>' : ''));
      } else {
        writeStatus('<span class="ps-strong">错题库 ' + active + ' 道</span><span>·</span>'
          + '<span>今日待复习 ' + due + ' 道</span>'
          + (stats.reviewed_today ? '<span>·</span><span>今日已复习 ' + stats.reviewed_today + ' 道</span>' : '')
          + (suspendedCount ? '<span>·</span><span>已归档 ' + suspendedCount + ' 道</span>' : ''));
      }

      var badge = qs('#navReviewBadge');
      if (badge) { badge.hidden = !(due > 0); badge.textContent = due ? String(due) : ''; }
      return stats;
    }).catch(function () { return null; });
  }

  /* ---------------------------------------------------------------- 挂载 */
  function mount() {
    var errorsPage = qs('[data-view="errors"]');
    var reviewPage = qs('[data-view="review"]');
    if (!errorsPage || !reviewPage) { return false; }
    if (state.mounted) { return true; }

    /* --- 错题专栏 --- */
    var shell = buildShell();
    errorsPage.append(shell.shell);
    shell.drop.id = 'waDrop';
    shell.input.id = 'waFileInput';
    shell.queue.id = 'waUploadQueue';
    shell.listBody.id = 'waListBody';
    shell.subjects.id = 'waSubjects';
    shell.search.addEventListener('input', function () {
      state.filter.search = shell.search.value.trim();
      renderCards();
    });
    shell.drop.addEventListener('click', function () { shell.input.click(); });
    shell.drop.addEventListener('keydown', function (event) {
      if (event.key === 'Enter' || event.key === ' ') { event.preventDefault(); shell.input.click(); }
    });
    shell.input.addEventListener('change', function () {
      if (shell.input.files.length) { uploadFiles(shell.input.files); }
      shell.input.value = '';
    });
    ['dragenter', 'dragover'].forEach(function (type) {
      shell.drop.addEventListener(type, function (event) { event.preventDefault(); shell.drop.classList.add('is-over'); });
    });
    ['dragleave', 'drop'].forEach(function (type) {
      shell.drop.addEventListener(type, function (event) { event.preventDefault(); shell.drop.classList.remove('is-over'); });
    });
    shell.drop.addEventListener('drop', function (event) {
      if (event.dataTransfer && event.dataTransfer.files.length) { uploadFiles(event.dataTransfer.files); }
    });

    /* --- 每日复习 --- */
    var review = buildReviewShell();
    review.body.id = 'waReviewBody';
    reviewPage.append(review.shell);

    state.mounted = true;
    return true;
  }

  function boot() {
    if (!mount()) { setTimeout(boot, 200); return; }
    loadStatusLine();
    loadSources();
    loadCards();
  }

  /* 页面切换时按需拉数据（复用主站的 showPage 钩子） */
  function hookRouting() {
    if (typeof window.showPage !== 'function' || window.showPage.__waHooked) { return; }
    var original = window.showPage;
    var wrapped = function (page) {
      original.apply(this, arguments);
      if (page === 'errors') { loadStatusLine(); loadSources(); loadCards(); }
      if (page === 'review') { loadStatusLine(); loadQueue(); }
      if (page === 'today') { window.__waStatusOwned = false; }
      if (window.refreshPageStatus) { window.refreshPageStatus(); }
    };
    wrapped.__waHooked = true;
    window.showPage = wrapped;
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', function () { boot(); hookRouting(); });
  } else {
    boot();
    hookRouting();
  }
  window.WrongAnswers = {
    reload: function () { loadStatusLine(); loadSources(); loadCards(); loadQueue(); },
    openReview: function (card) { openReview(card); },          // 供今日页「最近入库」直接进复盘
    goUpload: function () { if (typeof window.showPage === 'function') { window.showPage('errors'); } }
  };
})();
