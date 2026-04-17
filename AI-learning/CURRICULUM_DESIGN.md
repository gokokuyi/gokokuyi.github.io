# AI活用人材育成 教材設計文書（カリキュラム設計書）

> 本ドキュメントは `src/AI-learning/` 配下の HTML 教材の設計・構成を記述した文書です。
> 教材のメンテナンス・改訂・設計変更の際はこのファイルを起点にしてください。
> 最終更新：2026-04-13
> ※ 教材内に登場する「Axxx Japan」はシナリオ用の架空の会社名です。

---

## 1. 教材の概要

### 目的
OpenAI SDK（Azure OpenAI Service）を使ったLLMアプリケーション開発を
段階的に習得する。最終的に「AI アシスタント（MCP対応版）」を
一から構築できる人材を育成する。

### 対象者
- Python の基本文法を理解している社員
- AI/LLM の基礎知識を習得したい方
- 社内DX推進・AI活用に携わる方（開発経験不問）

### 使用技術・前提環境
- Python 3.10+
- Azure OpenAI Service（または OpenAI API）
- OpenAI SDK（`openai` ライブラリ）
- `mcp` ライブラリ（Module 205 のみ）

---

## 2. カリキュラム全体像

### ストーリー設定
> 【架空のシナリオ】Axxx Japan IT推進部に配属された新入社員「田中」が、
> 社内問い合わせを自動化する AI アシスタントを段階的に構築する研修。

### モジュール一覧

| Module | タイトル | 主要学習内容 | 難易度 | 目安時間 |
|---|---|---|---|---|
| 201 | LLM API の基礎 | Chat/Responses API、verbosity、reasoning、会話履歴 | ★☆☆ | 50分 |
| 202 | CLI チャットボット | 会話履歴の永続化、while ループ、JSONL | ★★☆ | 30分 |
| 203a | Embeddings 入門 | Embeddings API、コサイン類似度 | ★☆☆ | 40分 |
| 203b | RAG チャット | RAGパターン、ベクトル検索、類似文書取得 | ★★★ | 60分 |
| 204 | Function Calling | ツール定義、自律判断、ツールループ | ★★★ | 90分 |
| 205 | MCP ツール開発 | MCPプロトコル、サーバ実装、OpenAI クライアント | ★★★ | 90分 |

### 最終成果物
```
Axxx Japan社内 Q&A ボット（MCP サーバ対応版）
├── CLI から自然言語で質問できる             ← 202
├── Axxx Japan グループの FAQ を RAG で検索       ← 203b
├── 検索が必要かどうかを自律判断する          ← 204
└── OpenAI SDK ベースの MCP クライアントから呼び出せる ← 205
```

---

## 3. 各モジュールの学習構造

各モジュールは以下の 3 ステップで構成されます。

```
Lesson（知識習得）→ Quiz（理解確認）→ Handson（実装練習）
```

### Lesson（lesson.html）
- 概念説明（図・比喩を活用）
- **Handsonの先見**：「このモジュールで何を作るか」を冒頭に提示
- サンプルコードの読み解き（`.sample.py` に対応）
- Why の解説：「なぜそう設計するか」を必ず含める

### Quiz（quiz.html）
- 各モジュール 10 問
- 問題形式：選択式・穴埋め式・記述式・考察問題を混在
- 各問いに「このHandsonのどの箇所に対応するか」を明示
- 「答えを確認」ボタン：1問ずつ答えを表示（個別）
- 「全問の答えを表示」ボタン：一括表示

### Handson（handson.html）
- 実装演習（`# EDIT HERE!` 形式の穴埋めコード）
- 3段階ヒント（① APIの名前 → ② 引数 → ③ サンプルファイルの参照先）
- 完成サンプルコード（「答えを見る」で展開）
- 振り返りチェックリスト
- 「次のモジュールへ」ナビゲーション

---

## 4. ファイル構成

```
src/AI-learning/
├── CURRICULUM_DESIGN.md          ← 本ファイル（設計文書）
├── styles.css                     ← 共通スタイルシート
├── index.html                     ← トップページ（ロードマップ）
│
├── 201_api-basics/
│   ├── lesson.html                ← LLM API の概念
│   ├── quiz.html                  ← 10問クイズ
│   └── handson.html               ← 201_openai-sdk.py ベース
│
├── 202_cli-chat/
│   ├── lesson.html                ← 会話履歴・CLIチャットの概念
│   ├── quiz.html
│   └── handson.html               ← 202_cli-chat.py ベース
│
├── 203a_embeddings/
│   ├── lesson.html                ← Embeddings・コサイン類似度の概念
│   ├── quiz.html
│   └── handson.html               ← 203_introduction_of_embeddings.py ベース
│
├── 203b_rag-chat/
│   ├── lesson.html                ← RAGパターンの概念
│   ├── quiz.html
│   └── handson.html               ← 203_rag-chat.py ベース
│
├── 204_function-calling/
│   ├── lesson.html                ← Function Calling の概念
│   ├── quiz.html
│   └── handson.html               ← 204_function-calling-step0〜3.py ベース
│
└── 205_mcp/
    ├── lesson.html                ← MCP の概念
    ├── quiz.html
    └── handson.html               ← 205_mcp-step1〜3.py + client.py ベース
```

---

## 5. HTML テンプレート仕様

### 共通スタイル（styles.css）
- カラーテーマ：
  - Lesson：青系（`#2c5f8a`）
  - Quiz：オレンジ系（`#e07b39`）
  - Handson：緑系（`#2c8a52`）
- フォント：`'Noto Sans JP', sans-serif`
- コードブロック：ダーク背景（`#1e2a3a`）

### ナビゲーション構造
```
[トップ] > [Module XXX] > [Lesson / Quiz / Handson]
各ページ内に Lesson / Quiz / Handson の切り替えタブ
```

### Quiz の JavaScript 仕様
```javascript
// 1問ずつ答えを表示
function toggleAnswer(num) { ... }

// 全問の答えを表示
function showAllAnswers() { ... }

// 選択肢の選択状態を記録（任意）
function selectOption(questionNum, optionValue) { ... }
```

---

## 6. 使用ダミーデータ（Axxx Japanグループ FAQ）

`src/handson/203_rag-chat/` に格納済み。

| ファイル | 内容 | 使用モジュール |
|---|---|---|
| `jxxx-company-profile.txt` | 会社概要・沿革 | 203b, 204 |
| `jxxx-faq-general.txt` | 全般 FAQ | 203b, 204 |
| `jxxx-systems-faq.txt` | Axxx Japanシステムズ FAQ | 203b, 204 |
| `jxxx-consulting-faq.txt` | Axxx Japanコンサルティング FAQ | 203b, 204 |
| `jxxx-data-faq.txt` | Axxx Japanデータ FAQ | 203b, 204 |
| `jxxx-ai-dept-faq.txt` | AI推進部 FAQ | 205 |

---

## 7. メンテナンスガイド

### 教材内容の更新手順
1. 本ドキュメント（CURRICULUM_DESIGN.md）の該当セクションを更新
2. 対応する `.html` ファイルを編集
3. Quiz の問題・答えを更新する場合は `quiz.html` の `<div class="quiz-item">` ブロックを追加・変更

### 新モジュールの追加手順
1. 本ドキュメントのモジュール一覧・ファイル構成に追記
2. 新しいフォルダを `src/AI-learning/` 配下に作成
3. `lesson.html`, `quiz.html`, `handson.html` を既存ファイルをテンプレートとして作成
4. `index.html` のロードマップに新モジュールを追加

### Quiz の問題追加・変更
各 `quiz.html` の構造：
```html
<div class="quiz-item" id="q{番号}">
  <div class="question">
    <span class="q-number">Q{番号}</span>
    <p class="q-text">{問題文}</p>
    <div class="options">{選択肢（選択式の場合）}</div>
  </div>
  <button onclick="toggleAnswer({番号})" class="btn-answer">答えを確認</button>
  <div class="answer" id="answer-{番号}" style="display:none">
    <p class="correct-label">正解：{答え}</p>
    <p class="explanation">{解説}</p>
  </div>
</div>
```

---

## 8. 改訂履歴

| 日付 | バージョン | 内容 |
|---|---|---|
| 2026-04-13 | 1.0.0 | 初版作成 |
