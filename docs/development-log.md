# 開発ログ

このファイルは、現行仕様の整理と、試した実装・設定変更の経緯をまとめたものです。

---

## 現行仕様まとめ

### スタック構成

| コンポーネント | 実装 |
|---|---|
| Discord クライアント | Discord.py（メンション / Bot へのリプライに反応） |
| LLM バックエンド | Ollama（ローカル HTTP API） |
| データ永続化 | SQLite（会話履歴・ギルド設定） |
| Web 検索 | Brave Search API（オプション） |
| 通知 | Discord Webhook（起動・終了・ログ） |
| コンテナ | Docker Compose |

---

### 完全 2 段推論フロー

```
[メッセージ受信]
  └─ メンション or Bot へのリプライのみ反応
  └─ InferenceQueue でシリアライズ → "Thinking..." 表示

[Stage 1 - 検索判定]  WEB_SEARCH_ENABLED=true のときのみ実行
  ├─ ルーターあり (OLLAMA_ROUTER_MODEL ≠ OLLAMA_MODEL)
  │     1a. 検索要否のみ判定（小モデル 1回目）
  │         → {"action":"search"} または {"action":"answer"}
  │     1b. 検索が必要なら日本語クエリ生成（小モデル 2回目）
  │
  └─ ルーターなし（OLLAMA_ROUTER_MODEL 未設定 or メインと同じ）
        判定とクエリ生成を同時に行う（メインモデル 1回）
        → {"action":"search","search_query":"..."} または {"action":"answer"}

[検索]  action == "search" のとき
  └─ Discord メッセージを "Searching... (検索ワード)" に更新
  └─ Brave Search API を呼び出し（最大 WEB_SEARCH_MAX_RESULTS 件）
       タイトル / URL / スニペット / extra_snippets / 公開日 を取得

[Stage 2 - 最終回答生成]  常に実行
  └─ ContextBuilder でシステムプロンプトを組み立て
       - SYSTEM_PROMPT + 現在日時(JST) + ルール群
       - 検索結果があればユーザーメッセージに付加
  └─ メインモデル (OLLAMA_MODEL) で回答生成
  └─ 検索結果があれば参照 URL を末尾に付加して Discord に返信
```

---

### 検索判定の条件（Stage 1 共通）

**検索する**
- 最新情報・政治・時事・法律・規制など変動が激しい領域
- ニッチ・専門知識（ゲーム・アニメ・マンガ・趣味・特定コミュニティ等）
- 知識が欠如または陳腐化している可能性がある場合
- 不確かな場合は検索を優先（諦めるのではなく調べる）

**検索しない**
- 計算・コード・翻訳・論理推論など外部知識が不要な純粋推論タスク

> ルーターあり構成では判定（1a）とクエリ生成（1b）を分離することで、
> 1B モデルの限界（タスク競合による精度低下）を回避している。

---

### メインモデルのシステムプロンプト構成

```
{SYSTEM_PROMPT}

Current date and time: {YYYY-MM-DD HH:MM JST}

Rules:
- Do not invent facts not supported by the conversation.
- If you do not know something or are uncertain, say so clearly instead of guessing.
- For medical, legal, financial, security, or privacy topics: avoid definitive claims.
- Reply concisely unless the user explicitly asks for detail.
- Reply in Japanese unless the user explicitly asks for another language.
- Keep your response within {MAX_RESPONSE_CHARS} characters.
```

> 検索の判断は Stage 1 が担うため、メインプロンプトに検索指示は含めない（責務分離）。

---

### 主要設定項目

| 環境変数 | 説明 | 現行推奨値 |
|---|---|---|
| `OLLAMA_MODEL` | メイン推論モデル | `gemma4:26b` |
| `OLLAMA_ROUTER_MODEL` | 検索判定ルーターモデル（未設定時はメインと同じ） | `gemma3:1b` |
| `OLLAMA_CONTEXT_LENGTH` | KV キャッシュ削減のため低く設定 | `8192` |
| `OLLAMA_NUM_PARALLEL` | KV キャッシュ二重確保防止 | `1` |
| `WEB_SEARCH_ENABLED` | Brave Search 連携を有効化 | `false`（要 API キー） |
| `VISION_ENABLED` | 画像添付入力を有効化 | `true` |
| `MAX_HISTORY_MESSAGES` | リプライチェーンから遡る最大件数 | `20` |
| `MAX_RESPONSE_CHARS` | Discord 返信の文字数上限 | `1800` |

---

### 会話履歴管理

- Discord のリプライチェーンを遡り、最大 `MAX_HISTORY_MESSAGES` 件を context に含める
- 全メッセージを SQLite に保存（ギルド ID / チャンネル ID / ユーザー ID / role / content）
- チェーンが存在しない（新規メンション）場合は prior_messages なしで推論

---

## ルーターモデルの選定経緯

### gemma4:e2b → 不採用

- **問題**: gemma4:e2b は vision encoder を内包しており、実際の VRAM 消費が約 7 GB（想定 ~1.5 GB の約 5 倍）
- **症状**: gemma4:26b（~18.6 GB）と同時常駐できず、推論のたびにモデルが VRAM から退避・再ロードされる
- **ログの証拠**: `model requires more gpu memory than is currently available, evicting a model to make space`
- **結論**: RTX 3090 24GB では gemma4:26b との同時常駐不可

### gemma3:4b → 不採用

- **試行**: gemma3:1b より精度が高いことを期待して採用
- **問題**: VRAM 溢れ。推定より実際の消費が大きかった
- **結論**: gemma4:26b との同時常駐不可

### gemma3:1b → 現行採用（ルーターあり構成）

- 純テキストモデル。約 0.8 GB で gemma4:26b と同時常駐が可能
- ただし 1B モデルのため JSON 指示追従・クエリ生成の精度に限界あり
- 対策として判定（Stage 1a）とクエリ生成（Stage 1b）を **2回に分けて呼び出す** 構成を採用

---

## 推論アーキテクチャの変遷

### 当初: シングルモデル構成

- メインモデル（gemma4:26b）がすべてを担当
- 検索要否の判定も同じモデルで行っていた

### 中間: ルーター + メイン 2 モデル構成

- gemma4:e2b をルーターとして導入し、検索要否のみ判定させる設計
- → VRAM 問題で断念（e2b が予想外に大きかった）

### 現行: 完全 2 段推論アーキテクチャ

```
[Stage 1] 検索要否判定 + クエリ生成
  ├─ ルーターあり（gemma3:1b）: 判定とクエリ生成を 2 回に分けて呼び出す（精度優先）
  └─ ルーターなし（メインモデル）: 判定とクエリ生成を 1 回で実施（速度優先）

[検索] action == "search" なら BraveSearch 実行

[Stage 2] メイン推論（常に実行）
  gemma4:26b が最終回答を生成
```

---

## ルータープロンプトの改善

### 問題: `test` と送ると検索してしまう

- **原因**: gemma3:1b が「検索する」条件と「しない」条件を正確に区別できなかった
- **対応**: 判定（Stage 1a）とクエリ生成（Stage 1b）を分離し、判定タスクを単純化

### プロンプト設計の整理

- **検索する条件**: 最新情報・政治・時事・法律・変動が激しい領域・知識欠如・陳腐化・ニッチ専門知識（ゲーム・アニメ・マンガ等）
- **検索しない条件**: 計算・コード・翻訳・論理推論など外部知識が不要な純粋推論タスク
- **優先ルール**: 検索条件に一つでも該当すれば search を優先
- **不確かな場合**: 諦めるのではなく検索に倒す

---

## メインモデルプロンプトの改善

- 日時（JST）をシステムプロンプトに毎回注入 → 「現在は 2024 年」という誤認を防止
- ハルシネーション抑制: 知らないことは知らないと言わせる
- 高リスク領域（医療・法律・金融等）での断定を避けさせる
- 検索の判断は Stage 1 が担うため、メインプロンプトには検索指示は含めない（責務分離）

---

## 検索機能の改善

- 検索ワードを英語から **日本語スペース区切り** に変更（小モデルでの英語変換が不安定なため）
- Brave Search の `extra_snippets` と `age`（公開日）を LLM に渡すよう対応
- 検索中は Discord のメッセージを `Searching... (検索ワード)` に更新

---

## VRAM チューニング（RTX 3090 / gemma4:26b 構成）

| 設定 | 変更前 | 変更後 | 理由 |
|---|---|---|---|
| `OLLAMA_CONTEXT_LENGTH` | 32768 | 8192 | KV キャッシュ削減、ルーター同時常駐のため |
| `OLLAMA_NUM_PARALLEL` | 2 | 1 | KV キャッシュの二重確保を避けるため |
| `OLLAMA_ROUTER_MODEL` | なし | `gemma3:1b` | 検索判定を分離するため |

---

## その他の実装

- **複数 Webhook URL 対応**: `DISCORD_WEBHOOK_URL` にカンマ区切りで複数指定可能
- **Webhook embed footer に送信日時表示**
- **ollama-init でルーターモデルも pull**: `OLLAMA_ROUTER_MODEL` が異なる場合のみ
- **ルーターモデルの prewarm 追加**: メインモデルの prewarm 後にルーターも warm up
- **vision 対応**: Discord 添付画像 1 枚を LLM に渡す
