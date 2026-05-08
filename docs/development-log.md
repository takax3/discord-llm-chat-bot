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

### 推論フロー（ルーターあり）

`OLLAMA_ROUTER_MODEL ≠ OLLAMA_MODEL` のとき。各ステップの結果を Discord にリアルタイム表示する。

```
[メッセージ受信]
  └─ メンション or Bot へのリプライのみ反応
  └─ InferenceQueue でシリアライズ → "Thinking..." 表示

[Stage 1 - 検索判定]  WEB_SEARCH_ENABLED=true のときのみ実行
  Step 1: ジャンル分類  _classify_genre()  [ルーターモデル]
    → 「プログラミング」「政治・時事」等の短いラベルを生成
    → None（失敗）なら → [Stage 2] へ（search なし）

  Step 2: クエリ意図の要約  _summarize_query()  [ルーターモデル]
    → user_message のみを入力（prior_messages なし・コンテキスト最小化）
    → 「ユーザーが何を知りたいか」を1文で要約
    → Step 3 の明示的検索判定と Step 5 のクエリ生成に渡す

  Step 3: 明示的検索要求の確認  _is_explicit_search_request()  [ルーターモデル]
    → ジャンル・クエリ概要をコンテキストとして渡し、「調べて」等の明示指示を検出
    → true なら Step 4 をスキップして Step 5 へ直行

  Step 4: 最新情報・変動性の確認  _needs_fresh_info()  [ルーターモデル]  ※ Step 3 が false のみ
    → ジャンルと元メッセージから変動性を判定
    → false なら → [Stage 2] へ（search なし）

  Step 5: 検索ワード生成  _generate_query()  [ルーターモデル]
    → Step 2 の要約を活用して日本語スペース区切りキーワードを生成

[検索]  WEB_SEARCH_ENABLED=true かつ Step 5 まで到達したとき
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

**ルーターあり構成のステップ数**

| ルート | ステップ数 |
|---|---|
| Step 1 失敗（ジャンル分類不可） | 1回 → search なし |
| 非明示的 + 変動なし | 4回 → search なし |
| 明示的な検索要求（Step 4 スキップ） | 4回 → search |
| 非明示的 + 変動あり（典型） | 5回 → search |

---

### 推論フロー（ルーターなし）

`OLLAMA_ROUTER_MODEL` 未設定またはメインモデルと同じとき。判定とクエリ生成を 1 回にまとめて速度を優先する。

```
[メッセージ受信]
  └─ メンション or Bot へのリプライのみ反応
  └─ InferenceQueue でシリアライズ → "Thinking..." 表示

[Stage 1 - 検索判定]  WEB_SEARCH_ENABLED=true のときのみ実行
  判定 + クエリ生成を 1 回で実施  decide_combined()  [メインモデル]
    → {"action":"search","search_query":"..."} または {"action":"answer"}

[検索]  WEB_SEARCH_ENABLED=true かつ action == "search" のとき
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

> ルーターあり構成では各判定を単一タスクに絞った多段ステップ呼び出しで、
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
| `OLLAMA_ROUTER_SHOW_STEPS` | 最終返答の先頭にルーター判定ステップを付加するか | `false` |
| `OLLAMA_CONTEXT_LENGTH` | KV キャッシュ削減のため低く設定 | `8192` |
| `OLLAMA_NUM_PARALLEL` | KV キャッシュ二重確保防止 | `1` |
| `WEB_SEARCH_ENABLED` | Brave Search 連携を有効化 | `false`（要 API キー） |
| `VISION_ENABLED` | 画像添付入力を有効化 | `true` |
| `MAX_HISTORY_MESSAGES` | リプライチェーンから遡る最大件数 | `20` |
| `MAX_RESPONSE_CHARS` | Discord 返信の文字数上限 | `1800` |

> `OLLAMA_ROUTER_SHOW_STEPS=false` でも、判定中のリアルタイム表示（Discord メッセージのライブ更新）は常に行われる。
> フラグは最終返答への付加のみを制御する。

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

### gemma3:1b → 試行・限界確認済み

- 純テキストモデル。約 0.8 GB で gemma4:26b と同時常駐が可能
- 1B モデルの限界: JSON 指示追従・複雑な分類タスクの精度が根本的に不安定
- 多段分割（最大 5 ステップ）で対策を試みたが、それでも分類が安定しなかった
- **結論**: 検索判定は 1B モデルでは信頼性の確保が困難。メインモデルへの一本化を推奨

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
  ├─ ルーターあり（別モデル指定時）: 最大 5 回に分けて呼び出す
  │     各ステップの結果を Discord にリアルタイム表示（on_pending / on_result）
  └─ ルーターなし（推奨）: メインモデルが判定とクエリ生成を 1 回で実施

[検索] action == "search" なら BraveSearch 実行

[Stage 2] メイン推論（常に実行）
  メインモデル（gemma4:26b 等）が最終回答を生成
```

> **現在の推奨構成**: `OLLAMA_ROUTER_MODEL` を設定せず、メインモデルが `decide_combined()` で検索判定を行う。
> 1B ルーターモデルは精度が根本的に不安定なため、別途モデルを用意するメリットが小さい。

---

## ルータープロンプトの改善

### 第 1 世代: 判定 1 回（2 ステップ）

- **問題**: `test` と送ると検索してしまう
- **原因**: gemma3:1b が「検索する」条件と「しない」条件を正確に区別できなかった
- **対応**: 判定（1a）とクエリ生成（1b）を分離し、判定タスクを単純化

### 第 2 世代: 多段分割（5 ステップ）

- **問題**: 1 回の呼び出しで「検索要否 + 知識鮮度評価 + クエリ生成」を同時に判断させると 1B モデルでタスク競合が発生
- **対応**: 各呼び出しを単一タスクに絞る

#### ステップ分割の設計方針

| ステップ | タスク | 失敗フォールバック |
|---|---|---|
| Step 1 `_classify_genre()` | ジャンルラベル生成（短い日本語ラベル） | None → answer |
| Step 2 `_summarize_query()` | クエリ意図の1文要約（user_message のみ入力） | None（Step 3/5 でコンテキストなしに切り替え） |
| Step 3 `_is_explicit_search_request()` | 明示的検索要求の有無（true/false） | False（チェーン継続） |
| Step 4 `_needs_fresh_info()` | 変動性・最新情報の必要性（true/false） | True（検索に倒す） |
| Step 5 `_generate_query()` | 検索キーワード生成（スペース区切り） | user_message をそのまま使用 |

#### 設計上の判断

- Step 2 の要約を Step 3（明示的検索判定）と Step 5（クエリ生成）に渡す: ジャンルラベル単体より具体的な意図を伝えられる
- Step 1 のジャンルラベルも Step 3 のコンテキストに付加: 明示的検索判定の精度向上
- Step 2 `_summarize_query()` は prior_messages を渡さず user_message のみを使う: 後続ステップへ渡すコンテキストを最小化
- Step 4 には prior_messages を渡さない: Step 1 のジャンル情報で十分（呼び出しコスト削減）
- ジャンルと意図要約を分離: 「政治・時事」（Step 1）と「今の首相の名前を知りたい」（Step 2）は別タスク
  - 統合させると小モデルが回答本文を生成してしまう（「今の首相は岸田文雄です」等）
- ルーターへの画像は渡さない: gemma3:1b はテキスト専用。画像が必要なケースは `decide_combined()`（メインモデル）が処理する

#### リアルタイム進捗表示

- `on_pending`（ステップ開始前）と `on_result`（ステップ完了後）の 2 コールバックで Discord をライブ更新
- `OLLAMA_ROUTER_SHOW_STEPS=false`（デフォルト）: 推論中は現在ステップのみ表示、最終返答には付加しない
- `OLLAMA_ROUTER_SHOW_STEPS=true`: ステップ結果を蓄積表示し、最終返答の先頭にも付加する

#### 第 2 世代の限界

- 各ステップを単純化しても、1B モデルの精度が根本的に不安定であることが判明
- 例: ジャンル分類で回答本文を生成する、クエリ概要で答えを出力するなど
- 対策（Bad/Good 例示・"Do NOT answer" 明記・分類タスク化）を試みても再現率が安定しなかった
- **結論**: 小規模モデルで検索判定を行うより、メインモデルが `decide_combined()` で 1 回で処理する方が信頼性が高い

### プロンプト設計の整理（現行）

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
- 検索中は Discord のメッセージを `検索中 (検索ワード)` に更新し、完了後は `検索完了` を表示して最終返答に残す
- キュー待機中のプレースホルダを `Thinking...` から `Waiting...` に変更

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
