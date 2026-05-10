# 開発ログ

このファイルは、現行仕様の整理と、試した実装・設定変更の経緯をまとめたものです。

---

## 現行仕様まとめ

### スタック構成

| コンポーネント | 実装 |
|---|---|
| Discord クライアント | Discord.py（メンション / Bot へのリプライに反応） |
| LLM バックエンド | Ollama（ローカル HTTP API） |
| データ永続化 | SQLite（会話履歴・ギルド設定・推論ログ） |
| Web 検索 | Brave Search API（オプション） |
| 通知 | Discord Webhook（起動・終了・ログ） |
| コンテナ | Docker Compose |

---

### 推論フロー

```
[メッセージ受信]
  └─ メンション or Bot へのリプライのみ反応
  └─ InferenceQueue でシリアライズ → "Waiting... (Queue ahead: N)" 表示

[Stage 1 - 検索判定]  WEB_SEARCH_ENABLED=true のときのみ実行
  └─ Discord メッセージを "判定中…" に更新
  └─ メインモデルが判定とクエリ生成を 1 回で実施  decide()  [メインモデル]
       → {"action":"search","search_queries":["q1","q2",...]} または {"action":"answer"}
       → 複数の独立した知識が必要なとき（複数人物・複数トピック等）は複数クエリを返す

[検索]  action == "search" かつ search_queries が 1 件以上のとき（SHOW_STEPS=true のとき "検索クエリ: q1, q2" を表示済み）
  └─ Discord メッセージを "検索中…" に更新（クエリはステップ表示済みのため不要）
  └─ Brave Search API を asyncio.gather で並列実行（最大 WEB_SEARCH_MAX_RESULTS 件/クエリ）
       タイトル / URL / スニペット / extra_snippets / 公開日 を取得
  └─ 完了後 SHOW_STEPS=true なら "検索完了" をステップに追加、false なら "検索完了" を一時表示

[Stage 2 - 最終回答生成]  常に実行
  └─ ContextBuilder でシステムプロンプトを組み立て
       - SYSTEM_PROMPT + 現在日時(JST) + ルール群
       - 検索結果があればユーザーメッセージに付加（全クエリ結果を結合）
  └─ "推論中…" を表示してからメインモデル (OLLAMA_MODEL) で回答生成
  └─ SHOW_STEPS=true: ステップ一覧（判定結果・検索完了・推論完了）＋ 回答を返信
  └─ SHOW_STEPS=false: 回答のみを返信
  └─ 検索結果があれば参照 URL を末尾に付加
```

---

### 検索判定の条件（Stage 1）

**検索する**
- 最新情報・政治・時事・法律・規制など変動が激しい領域
- ニッチ・専門知識（ゲーム・アニメ・マンガ・趣味・特定コミュニティ等）
- 知識が欠如または陳腐化している可能性がある場合
- 不確かな場合は検索を優先（諦めるのではなく調べる）

**検索しない**
- 計算・コード・翻訳・論理推論など外部知識が不要な純粋推論タスク

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
- Format responses using Discord Markdown only.
  Supported: **bold**, *italic*, __underline__, ~~strikethrough~~, `inline code`, ```code blocks```, > blockquotes, - or * bullet lists, numbered lists, # / ## / ### headings.
  Not supported (do not use): HTML tags, --- horizontal rules, Markdown tables, task lists (- [ ]), setext headings (underline-style), reference-style links, image embeds.
- Use ## or ### headings only for long structured responses. Avoid headings for short or conversational replies.
```

> 検索の判断は Stage 1 が担うため、メインプロンプトに検索指示は含めない（責務分離）。

---

### 主要設定項目

| 環境変数 | 説明 | 現行推奨値 |
|---|---|---|
| `OLLAMA_MODEL` | 検索要否判定・最終回答の両方に使うモデル | `gemma4:26b` |
| `OLLAMA_CONTEXT_LENGTH` | KV キャッシュ削減のため低く設定 | `8192` |
| `OLLAMA_NUM_PARALLEL` | KV キャッシュ二重確保防止 | `1` |
| `WEB_SEARCH_ENABLED` | Brave Search 連携を有効化 | `false`（要 API キー） |
| `SHOW_STEPS` | 推論進捗ステップを積み重ねて表示するかどうか | `false` |
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

### 現行: 完全 2 段推論アーキテクチャ（メインモデル一本化）

```
[Stage 1] メインモデルが判定とクエリ生成を 1 回で実施（JSON 出力）
  → 複数クエリ対応: 独立した知識が必要なときは search_queries に複数列挙

[検索] action == "search" なら Brave Search を並列実行（複数クエリ対応）

[Stage 2] メインモデルが最終回答を生成
  → 2 つの呼び出しは完全に分離（専用 JSON プロンプト vs ユーザー向け SYSTEM_PROMPT）
```

> ルーターモデル（小規模別モデル）は廃止。OLLAMA_MODEL のみを使う単一モデル構成。

---

## 検索判定プロンプトの変遷

### 第 1 世代: 小規模ルーターモデル（廃止）

- gemma3:1b 等の 1B モデルを別途用意し、判定とクエリ生成を委譲
- **問題**: JSON 指示追従・分類タスクの精度が根本的に不安定
- 多段分割（最大 5 ステップ）・"Do NOT answer" 明記・タスク限定化で対策を試みたが再現率が安定しなかった
- **結論**: 1B モデルで検索判定を行うのは信頼性の確保が困難

### 現行: メインモデル 1 回呼び出し（decide()）

- 専用 JSON プロンプトで判定とクエリ生成を 1 回に集約
- 出力: `{"action":"search","search_queries":["q1","q2",...]}` または `{"action":"answer"}`
- 複数クエリ対応: 独立した知識が必要なとき（複数人物・複数トピック等）は複数列挙
- **プロンプト設計**:
  - 検索する条件: 最新情報・政治・時事・法律・変動領域・ニッチ専門知識（ゲーム・アニメ等）・不確かな場合
  - 検索しない条件: 計算・コード・翻訳・論理推論など外部知識不要の純粋推論タスク
  - Stage 1（JSON 出力）と Stage 2（ユーザー向け回答）で完全にプロンプトを分離

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
- **複数クエリ並列実行**: 独立した知識が必要なとき LLM が複数クエリを返し `asyncio.gather` で並列検索
- `SHOW_STEPS=true` のとき: 判定後に `検索クエリ: q1, q2` または `検索不要` → `検索中…` → `検索完了` → `推論完了` をステップとして積み重ね、最終応答の前に表示する
- `SHOW_STEPS=false`（既定）のとき: 途中ステップは都度置き換え、最終応答のみ残す
- `検索中…` にはクエリを含めない（クエリは判定後ステップで表示済み）
- キュー待機中のプレースホルダを `Waiting... (Queue ahead: N)` に変更
- 検索要否判定中は `判定中…` を表示（Stage 1 と Stage 2 の 2 段構成をユーザーが認識できる）
- 推論中は `推論中…` を表示し、完了後は `推論完了` に書き換える（SHOW_STEPS=true 時のみ表示に残る）

---

## VRAM チューニング（RTX 3090 / gemma4:26b 構成）

| 設定 | 変更前 | 変更後 | 理由 |
|---|---|---|---|
| `OLLAMA_CONTEXT_LENGTH` | 32768 | 8192 | KV キャッシュ削減のため |
| `OLLAMA_NUM_PARALLEL` | 2 | 1 | KV キャッシュの二重確保を避けるため |

---

## その他の実装

- **複数 Webhook URL 対応**: `DISCORD_WEBHOOK_URL` にカンマ区切りで複数指定可能
- **Webhook embed footer に送信日時表示**
- **vision 対応**: Discord 添付画像 1 枚を LLM に渡す
- **複数検索クエリ並列実行**: LLM が独立した知識が必要と判断したとき複数クエリを返し `asyncio.gather` で並列検索

---

## 推論ログ記録の追加

推論 1 回ごとに `inference_logs` テーブルへタイムスタンプ・トークン数・検索クエリ数・エラーフラグを記録するようにした。

### タイムスタンプ方針

- `_now_utc()` ヘルパー（`discord_client.py` 内）: `datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")`
- UTC で保存し、SQLite の `julianday` 等がそのまま使える
- 表示時の JST 変換は Python 側で行う

### 記録タイミング

| フィールド | 収集箇所 |
|---|---|
| `message_received_at` | `discord_client` がメッセージイベントを受け取った直後 |
| `decision_started_at` / `decision_ended_at` | `search_decision_service.decide()` の呼び出し前後 |
| `search_started_at` / `search_ended_at` | Brave Search API 並列実行の前後 |
| `inference_started_at` / `inference_ended_at` | Stage 2（最終回答）の Ollama 呼び出し前後 |
| `reply_sent_at` | Discord への返信送信完了後 |

### トークン数の伝播

- `OllamaClient` が Ollama API レスポンスから `prompt_tokens` / `completion_tokens` を取得し `OllamaChatResult` に持たせる
- `SearchDecisionService` が `SearchDecision` にトークン数を付与して返す
- `discord_client` がこれらの値を `InferenceLog` に詰めて `InferenceLogRepository.save()` を呼ぶ

### is_error フラグ

- `OllamaClientError` が発生した場合のみ `is_error=True` で記録する
- エラー時も収集済みのタイムスタンプを保持してログに残す

---

## `/stats` スラッシュコマンドの追加

推論ログを手軽に確認するため、`/stats` スラッシュコマンドを実装した。

### CommandTree を Client に持たせる方式

`discord.py` のスラッシュコマンドは `app_commands.CommandTree` を介して登録する。`Bot` サブクラスではなく素の `Client` を使っているため、`__init__` で `self.tree = app_commands.CommandTree(self)` を手動生成し、`setup_hook()` の中で `await self.tree.sync()` を呼んでグローバル登録する方式を採用した。

コマンド定義は `_register_slash_commands()` に集約し、`__init__` から呼ぶ。これにより新しいスラッシュコマンドを追加する場合も同メソッドに追記するだけで済む。

### 全体表示への変更

当初は `/stats` を `ephemeral=True`（実行者のみ表示）で実装していたが、デバッグ情報をチャンネル参加者と共有できるよう全体表示に変更した。

### 表示項目の追加

`message_received_at`（メッセージ受信時刻）を先頭に、`reply_sent_at`（返信完了時刻）を末尾に追加した。これにより受信から返信完了までの全体所要時間をひと目で把握できる。

### `fetch_last_by_channel` の追加

`inference_log_repository` に `WHERE channel_id = ? ORDER BY id DESC LIMIT 1` で当該チャンネルの最新ログを 1 件取得する `fetch_last_by_channel(channel_id)` を追加した。チャンネル単位の絞り込みにより、同一サーバーの別チャンネルのログが混入しない。

### `_elapsed_seconds` ヘルパー

Stage 1・Stage 2 の所要時間計算（ISO 8601 Z サフィックス文字列 → float 秒）を `_elapsed_seconds(start, end)` として切り出した。`start` または `end` が `None` のときは `None` を返し、呼び出し側で未計測として扱う。

---

## Ollama のホスト運用への切り替え

docker-compose.yml から `ollama` サービス・`ollama-init` サービス・`ollama-data` ボリュームをすべて削除し、Bot コンテナのみの構成に移行した。

### 変更前の構成

- `discordbot` / `ollama` / `ollama-init` の 3 サービス構成
- Bot からは `http://ollama:11434`（Docker 内部 DNS）で Ollama に接続
- docker-compose.yml の `environment` ブロックに `OLLAMA_BASE_URL=http://ollama:11434` をハードコードしていた
- `OLLAMA_KEEP_ALIVE` / `OLLAMA_NUM_PARALLEL` / `OLLAMA_CONTEXT_LENGTH` / `OLLAMA_FLASH_ATTENTION` / `OLLAMA_GPU_LAYERS` を Ollama コンテナへ渡す環境変数として `.env` に管理していた

### 変更後の構成

- `discordbot` サービスのみ
- Ollama はホスト上で直接起動し、Bot コンテナが `host.docker.internal:11434` 経由で接続する
- `OLLAMA_BASE_URL` は `.env` で管理し、既定値を `http://host.docker.internal:11434` に変更
- Ollama コンテナへ渡す専用の環境変数（`OLLAMA_NUM_PARALLEL` 等）は Ollama のホスト設定で直接管理するため `.env` から削除
- `discordbot` サービスに `deploy.resources.reservations.devices`（NVIDIA GPU）を追加し、`pynvml` 経由の GPU 消費電力計測を有効化（NVIDIA Container Toolkit が必要）

### 判断の背景

Ollama をコンテナで管理すると、モデルストレージの volume 管理・Ollama サーバーのチューニング設定（`OLLAMA_CONTEXT_LENGTH` 等）の docker-compose 管理・`ollama-init` によるモデル pull の手順が必要になり、構成が複雑になる。ホスト上の Ollama に接続する構成は Ollama の管理を OS 側に任せられるため、docker-compose がシンプルになる。GPU 消費電力の計測（`pynvml` / NVML）は引き続き `discordbot` コンテナ内から行うため、GPU device reservation は Ollama 分ではなく Bot コンテナ側に設定している。

---

## Discord Markdown 最適化

LLM がHTML タグや Markdown テーブルなど Discord でレンダリングされない構文を出力することがあった。この問題へのアプローチとして、後処理（出力後の文字列変換）とシステムプロンプト追記の 2 案を検討した。

### 後処理を採用しなかった理由

- 変換ルールが複雑になる（HTML タグの除去・テーブルの箇条書き変換等）と、LLM の意図した構造が壊れるリスクがある。
- 変換漏れや誤変換のデバッグコストが高い。
- 根本原因（LLM の出力傾向）を直さないため、別の非対応構文が出現するたびに都度対処が必要になる。

### システムプロンプト追記を採用した理由

- 使える構文と使えない構文を明示するだけで、十分な能力のモデルであれば遵守できる。
- 変換ロジックを持たないためコードが増えない。
- ルールの追加・修正が `context_builder.py` の 1 箇所で完結する。

### 追記したルール

`_build_system_prompt()` の Rules ブロックに以下を追加した。

```
- Format responses using Discord Markdown only.
  Supported: **bold**, *italic*, __underline__, ~~strikethrough~~, `inline code`, ```code blocks```, > blockquotes, - or * bullet lists, numbered lists, # / ## / ### headings.
  Not supported (do not use): HTML tags, --- horizontal rules, Markdown tables, task lists (- [ ]), setext headings (underline-style), reference-style links, image embeds.
- Use ## or ### headings only for long structured responses. Avoid headings for short or conversational replies.
```

見出しルールを分けたのは、短い会話でも見出しを使うと不自然に装飾過剰になる挙動が確認されたため。

---

## GPU 消費電力リアルタイム計測の追加

推論ターン中（キュー通過後〜返答送信完了まで）の GPU 消費電力を 1 秒おきにサンプリングし、平均電力と推定消費エネルギーを `inference_logs` に記録するようにした。

### 実装方針

- `GpuPowerSampler`（`services/gpu_power_sampler.py`）: `pynvml` 経由で NVML を呼び出す。`pynvml` 未インストール時は `_pynvml = None` として `available=False`。NVIDIA GPU 未検出時は `nvmlInit()` の例外を握りつぶして `available=False`。
- ポーリングは `asyncio.wait_for(asyncio.shield(stop.wait()), timeout=1.0)` で 1 秒おきに実行する非同期タスク（`asyncio.create_task`）。`gpu_power_sampler.available` が `False` のときはタスク自体を起動しない。
- 計測区間: `turn_started = True`（キュー通過）〜 `sent_message.edit(content=reply)` 完了まで。Brave Search の HTTP 待機時間も区間に含まれる（意図的）。
- `gpu_avg_watts = mean(samples)`、`gpu_energy_joules = avg_watts × elapsed_seconds`（`turn_start_time` を `datetime.now(timezone.utc)` で記録）。
- サンプルが 0 件の場合（NVIDIA GPU なし、または全サンプルで取得失敗）は `gpu_avg_watts` / `gpu_energy_joules` ともに `None` とし、`inference_logs` に `NULL` で保存する。

### グレースフル無効化の設計判断

`pynvml` を optional 依存とし、NVIDIA GPU のない環境でも Bot 本体の起動・動作を妨げないことを優先した。`available` プロパティで呼び出し側が GPU の有無を意識せず扱えるように設計している。
