/* ============================================================
   生成AI時代は、なんでもHTML！ — デジタルブック共通JS
   ============================================================ */

'use strict';

/* ----------------------------------------------------------
   iframeサンプルの折りたたみトグル
   ---------------------------------------------------------- */
function toggleSample(btn) {
  var embed = btn.closest('.sample-embed');
  if (!embed) return;
  var body = embed.querySelector('.sample-embed-body');
  if (!body) return;

  var isOpen = body.classList.contains('open');
  if (isOpen) {
    body.classList.remove('open');
    btn.textContent = '▶ 開いて確認';
  } else {
    body.classList.add('open');
    btn.textContent = '▲ 閉じる';
    // 初回展開時に src を data-src から設定（遅延ロード）
    var iframe = body.querySelector('iframe[data-src]');
    if (iframe) {
      iframe.src = iframe.getAttribute('data-src');
      iframe.removeAttribute('data-src');
    }
  }
}

/* ----------------------------------------------------------
   モバイルのサイドバートグル
   ---------------------------------------------------------- */
function toggleSidebar() {
  var sidebar = document.querySelector('.toc-sidebar');
  if (!sidebar) return;
  sidebar.classList.toggle('open');

  // オーバーレイを作成/削除
  var overlay = document.getElementById('sidebar-overlay');
  if (sidebar.classList.contains('open')) {
    if (!overlay) {
      overlay = document.createElement('div');
      overlay.id = 'sidebar-overlay';
      overlay.style.cssText = [
        'position:fixed', 'inset:0', 'background:rgba(0,0,0,0.4)',
        'z-index:850', 'cursor:pointer'
      ].join(';');
      overlay.addEventListener('click', toggleSidebar);
      document.body.appendChild(overlay);
    }
  } else {
    if (overlay) overlay.remove();
  }
}

/* ----------------------------------------------------------
   現在ページをTOCサイドバーでハイライト
   ---------------------------------------------------------- */
document.addEventListener('DOMContentLoaded', function () {
  var current = location.pathname.split('/').pop() || 'index.html';
  document.querySelectorAll('.toc-sidebar a').forEach(function (a) {
    var href = a.getAttribute('href');
    if (href && href.split('/').pop() === current) {
      a.classList.add('active');
      // サイドバー内でスクロール表示
      a.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
    }
  });

  // モバイルでサイドバー内リンクを踏んだら閉じる
  document.querySelectorAll('.toc-sidebar a').forEach(function (a) {
    a.addEventListener('click', function () {
      var sidebar = document.querySelector('.toc-sidebar');
      if (sidebar && sidebar.classList.contains('open')) {
        toggleSidebar();
      }
    });
  });

  // すべての sample-embed のデフォルトボタンテキストを統一
  document.querySelectorAll('.sample-embed-toggle').forEach(function (btn) {
    if (!btn.textContent.trim()) btn.textContent = '▶ 開いて確認';
  });
});

/* ----------------------------------------------------------
   キーボードナビゲーション（← →矢印キー）
   ---------------------------------------------------------- */
document.addEventListener('keydown', function (e) {
  if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') return;
  if (e.ctrlKey || e.metaKey || e.altKey) return;
  if (e.key === 'ArrowLeft') {
    var prev = document.querySelector('.nav-prev:not(.disabled)');
    if (prev) prev.click();
  } else if (e.key === 'ArrowRight') {
    var next = document.querySelector('.nav-next:not(.disabled)');
    if (next) next.click();
  }
});
