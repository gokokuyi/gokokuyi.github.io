// AI Learning Curriculum — Progress Tracker
// Tracks lesson/quiz/handson completion per module using localStorage.

const PROGRESS_KEY   = "ai_curriculum_progress";
const CELEBRATED_KEY = "ai_curriculum_celebrated";
const MODULES    = ["module0","module1","module2","module3","module4","module5","module6"];
const PAGE_TYPES = ["lesson","quiz","handson"];

// ── Storage helpers ─────────────────────────────────────────────────

function getProgress() {
  const raw  = localStorage.getItem(PROGRESS_KEY);
  const data = raw ? JSON.parse(raw) : {};
  MODULES.forEach(m => { if (!data[m]) data[m] = { lesson: false, quiz: false, handson: false }; });
  return data;
}

function setProgress(module, pageType, value) {
  const data = getProgress();
  if (data[module] && pageType in data[module]) {
    data[module][pageType] = value !== false;
    localStorage.setItem(PROGRESS_KEY, JSON.stringify(data));
  }
}

function resetProgress() {
  if (confirm("学習進捗をリセットしますか？")) {
    localStorage.removeItem(PROGRESS_KEY);
    localStorage.removeItem(CELEBRATED_KEY);
    location.reload();
  }
}

// ── Page detection ──────────────────────────────────────────────────

function detectCurrentPage() {
  const path = globalThis.location.pathname.replaceAll("\\", "/");
  let module = null, pageType = null;
  MODULES.forEach(m  => { if (path.includes("/" + m))         module   = m; });
  PAGE_TYPES.forEach(t => { if (path.includes(t + ".html"))   pageType = t; });
  return { module, pageType };
}

function calcStats() {
  const data = getProgress();
  let done = 0;
  const total = MODULES.length * PAGE_TYPES.length;
  MODULES.forEach(m => PAGE_TYPES.forEach(t => { if (data[m][t]) done++; }));
  return { done, total, pct: Math.round((done / total) * 100) };
}

// ── Auto-mark + button restore ──────────────────────────────────────

function autoMarkOnLoad() {
  const cur = detectCurrentPage();
  if (cur.module && cur.pageType && cur.pageType !== "handson") {
    setProgress(cur.module, cur.pageType, true);
    checkAndCelebrate();
  }
  if (cur.pageType === "handson") {
    const data = getProgress();
    if (cur.module && data[cur.module]?.handson) _setHandsonButtonCompleted();
  }
}

function _setHandsonButtonCompleted() {
  const btn = document.getElementById("btn-handson-complete");
  if (btn) {
    btn.textContent = "✅ 完了済み";
    btn.disabled = true;
    btn.classList.add("btn-completed");
  }
}

function markHandsonComplete() {
  const cur = detectCurrentPage();
  if (cur.module) {
    setProgress(cur.module, "handson", true);
    _setHandsonButtonCompleted();
    renderFloatWidget();
    checkAndCelebrate();
  }
}

// ── Index page rendering ────────────────────────────────────────────

function renderProgressBadges() {
  const data = getProgress();
  MODULES.forEach(m => {
    const card = document.getElementById("card-" + m);
    if (!card) return;
    const d = data[m];
    const completed = (d.lesson ? 1 : 0) + (d.quiz ? 1 : 0) + (d.handson ? 1 : 0);
    const badge = card.querySelector(".progress-badge");
    if (!badge) return;
    badge.textContent = completed + " / 3";
    const state = completed === 3 ? "done" : completed > 0 ? "in-progress" : "not-started";
    badge.className = "progress-badge " + state;
  });
}

function renderOverallProgress() {
  const { pct } = calcStats();
  const bar   = document.getElementById("progress-bar-inner");
  const pctEl = document.getElementById("progress-pct");
  if (bar)   bar.style.width   = pct + "%";
  if (pctEl) pctEl.textContent = pct + "%";
}

// ── Floating widget (module subpages) ──────────────────────────────

function renderFloatWidget() {
  const floatEl = document.getElementById("progress-float-widget");
  if (!floatEl) return;

  const { done, total, pct } = calcStats();
  const barEl = document.getElementById("progress-float-bar");
  const pctEl = document.getElementById("progress-float-pct");
  if (barEl) barEl.style.width = pct + "%";
  if (pctEl) pctEl.textContent = done + " / " + total;

  const { module } = detectCurrentPage();
  const modEl = document.getElementById("progress-float-module");
  if (!modEl) return;
  if (module) {
    const d = getProgress()[module];
    modEl.textContent =
      "L\u00a0" + (d.lesson  ? "\u2705" : "\u2b1c") + "\u3000" +
      "Q\u00a0" + (d.quiz    ? "\u2705" : "\u2b1c") + "\u3000" +
      "H\u00a0" + (d.handson ? "\u2705" : "\u2b1c");
    modEl.style.display = "";
  } else {
    modEl.style.display = "none";
  }
}

function injectFloatWidget() {
  if (!detectCurrentPage().module) return;
  const el = document.createElement("div");
  el.id = "progress-float-widget";
  el.innerHTML =
    '<a href="../index.html" class="progress-float-home" title="ホームへ戻る">&#8592; ホーム</a>' +
    '<div class="progress-float-bar-track"><div id="progress-float-bar" class="progress-float-bar"></div></div>' +
    '<span id="progress-float-pct" class="progress-float-pct">0 / 21</span>' +
    '<span id="progress-float-module" class="progress-float-module"></span>';
  document.body.insertBefore(el, document.body.firstChild);
  document.body.style.paddingTop = "34px";
}

// ── Celebration (100% complete) ─────────────────────────────────────

function checkAndCelebrate() {
  const { done, total } = calcStats();
  if (done === total && !localStorage.getItem(CELEBRATED_KEY)) {
    localStorage.setItem(CELEBRATED_KEY, "1");
    setTimeout(showCelebration, 400);
  }
}

function showCelebration() {
  const overlay = document.createElement("div");
  overlay.id = "celebration-overlay";
  overlay.innerHTML =
    '<div id="celebration-card">' +
      '<div class="celebration-fireworks">🎆</div>' +
      '<h1 class="celebration-title">おめでとう！</h1>' +
      '<div class="celebration-badge">✨&nbsp;&nbsp;修了認定&nbsp;&nbsp;✨</div>' +
      '<p class="celebration-headline">' +
        'あなたは今日、<strong>AIアプリを自ら構築できるエンジニア</strong>になりました。' +
      '</p>' +
      '<p class="celebration-message">' +
        '全 7 モジュール・21 ページをすべて修了しました。<br>' +
        'API 連携から始まり、RAG・Function Calling・MCP・<br>' +
        'セキュリティ・評価まで——実践的なスキルを一通り習得した' +
        'あなたは、もう AI アプリ開発の世界に踏み出せます。' +
      '</p>' +
      '<div class="celebration-skills">' +
        '<span class="cel-tag">API 連携</span>' +
        '<span class="cel-tag">プロンプト設計</span>' +
        '<span class="cel-tag">RAG</span>' +
        '<span class="cel-tag">Function Calling</span>' +
        '<span class="cel-tag">MCP</span>' +
        '<span class="cel-tag">セキュリティ</span>' +
        '<span class="cel-tag">評価・品質管理</span>' +
      '</div>' +
      '<button onclick="closeCelebration()" class="celebration-close-btn">🏠&nbsp;ホームへ戻る</button>' +
    '</div>';
  document.body.appendChild(overlay);
  spawnConfetti();
  spawnStars();
  _trackCelebration();
}

function closeCelebration() {
  const overlay = document.getElementById("celebration-overlay");
  if (!overlay) return;
  overlay.style.animation = "overlay-out 0.35s ease forwards";
  setTimeout(() => {
    document.querySelectorAll(".confetti-piece, .star-piece").forEach(el => el.remove());
    overlay.remove();
  }, 350);
}

function spawnConfetti() {
  const colors = [
    "#f94144","#f3722c","#f8961e","#f9c74f","#90be6d",
    "#43aa8b","#577590","#a8dadc","#e63946","#ffd700",
    "#ff6b6b","#4ecdc4","#c77dff","#48cae4",
  ];
  for (let i = 0; i < 140; i++) {
    const p = document.createElement("div");
    p.className = "confetti-piece";
    p.style.left              = Math.random() * 100 + "vw";
    p.style.animationDelay    = (Math.random() * 3) + "s";
    p.style.animationDuration = (2.5 + Math.random() * 2.5) + "s";
    p.style.background        = colors[Math.floor(Math.random() * colors.length)];
    const w = 6 + Math.random() * 9;
    p.style.width        = w + "px";
    p.style.height       = w * (0.4 + Math.random() * 0.8) + "px";
    p.style.borderRadius = Math.random() > 0.5 ? "50%" : "2px";
    document.body.appendChild(p);
  }
}

function spawnStars() {
  const emojis = ["⭐","🌟","✨","💫","🎊","🎉"];
  for (let i = 0; i < 18; i++) {
    const s = document.createElement("div");
    s.className             = "star-piece";
    s.textContent           = emojis[Math.floor(Math.random() * emojis.length)];
    s.style.left            = (5 + Math.random() * 90) + "vw";
    s.style.bottom          = "10vh";
    s.style.animationDelay  = (Math.random() * 2) + "s";
    s.style.animationDuration = (1.8 + Math.random() * 1.5) + "s";
    s.style.fontSize        = (18 + Math.random() * 24) + "px";
    document.body.appendChild(s);
  }
}

// ── GoatCounter analytics ───────────────────────────────────────────

function _loadGoatCounter(callback) {
  if (globalThis.goatcounter?.count) { callback(); return; }
  if (document.querySelector("script[data-goatcounter]")) {
    const poll = setInterval(() => {
      if (globalThis.goatcounter?.count) { clearInterval(poll); callback(); }
    }, 100);
    return;
  }
  const s = document.createElement("script");
  s.setAttribute("data-goatcounter", "https://gokokuyi.goatcounter.com/count");
  s.async = true;
  s.src   = "https://gc.zgo.at/count.js";
  s.onload = callback;
  document.head.appendChild(s);
}

function _trackCelebration() {
  _loadGoatCounter(() => {
    globalThis.goatcounter.count({
      path:  "completion/celebration",
      title: "修了セレブレーション",
      event: true,
    });
  });
}

// ── Boot ────────────────────────────────────────────────────────────

document.addEventListener("DOMContentLoaded", () => {
  autoMarkOnLoad();
  injectFloatWidget();
  renderFloatWidget();
  renderProgressBadges();
  renderOverallProgress();
  checkAndCelebrate();
});
