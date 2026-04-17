/**
 * download.js
 *
 * 1. .btn-download リンクをクリックで強制ダウンロード（fetch + Blob）
 *    ブラウザが .py を text/plain として表示してしまう問題を防ぎます。
 *
 * 2. 各ダウンロードボタンの直後に「👁」プレビューボタンを自動挿入
 *    クリックすると viewer.html でシンタックスハイライト表示されます。
 *
 * 注意: fetch は HTTP / HTTPS でのみ動作します。
 *       file:// で直接開いている場合はフォールバックとして新しいタブが開きます。
 *       ローカルテスト時は `python -m http.server 8080` でサーブしてください。
 */
(function () {
  'use strict';

  /** fetch + Blob(octet-stream) で強制ダウンロード */
  function forcedDownload(url, filename) {
    fetch(url)
      .then(function (res) {
        if (!res.ok) { throw new Error('HTTP ' + res.status); }
        return res.blob();
      })
      .then(function (blob) {
        var octetBlob = new Blob([blob], { type: 'application/octet-stream' });
        var blobUrl = URL.createObjectURL(octetBlob);
        var a = document.createElement('a');
        a.href = blobUrl;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        setTimeout(function () { URL.revokeObjectURL(blobUrl); }, 200);
      })
      .catch(function () {
        window.open(url, '_blank');
      });
  }

  document.addEventListener('DOMContentLoaded', function () {
    document.querySelectorAll('a.btn-download').forEach(function (anchor) {

      // ── 1. ダウンロードのクリックハンドラ ──────────────────────────
      anchor.addEventListener('click', function (e) {
        e.preventDefault();
        var url = anchor.href;
        var filename = anchor.getAttribute('download') || url.split('/').pop();
        forcedDownload(url, filename);
      });

      // ── 2. 「👁」プレビューボタンをダウンロードボタンの直後に挿入 ──
      var viewBtn = document.createElement('a');
      viewBtn.href = '../viewer.html?file=' + encodeURIComponent(anchor.href);
      viewBtn.target = '_blank';
      viewBtn.rel = 'noopener noreferrer';
      viewBtn.className = 'btn-view';
      viewBtn.textContent = '👁';
      viewBtn.title = 'コードをプレビュー';
      anchor.insertAdjacentElement('afterend', viewBtn);
    });
  });
}());
