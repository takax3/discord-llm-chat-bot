# Specification

## 概要
- 目的: Discord サーバー上で動作する、Ollama ベースのローカル LLM チャットボットを提供する。
- 対象利用者: 自前サーバーまたはローカル PC 上で Discord bot を運用したい個人開発者または小規模チーム。
- 外部依存:
  - Discord Gateway / REST API
  - Ollama HTTP API
  - Ollama 上の利用モデル
  - 任意の永続化先（初期案ではローカルファイルまたは SQLite）

## 前提と非目標
- 初期設計では 1 プロセスの Python サービスとして動作させる。
- LLM 推論は OpenAI API ではなく、ローカルまたは同一ネットワーク上の Ollama に委譲する。
- Bot 自体はテキストチャットを対象とし、音声通話、画像生成、外部ツール実行は初期スコープ外とする。
- マルチノード構成や大規模シャーディングは初期スコープ外とする。
- 本仕様は初期設計版であり、実装前に追加の運用要件が出た場合は本書を更新してからコードへ反映する。

## 機能仕様
### 中核機能
- Discord 上で Bot へのメンションを受け取ったときに会話処理を開始する。
- Bot 自身の返信メッセージへの reply を受け取ったときも会話処理を継続できるようにする。
- 受信メッセージを整形し、Ollama 上の利用モデルへプロンプトとして送る。
- モデル応答を Discord メッセージとして返信し、推論中は待機メッセージを先に返す。
- 同時に複数リクエストが来た場合は bot 内で推論を直列化する。
- Discord の presence に待機キュー数と直近のトークンスピードを表示する。
- 終了処理開始時は Bot の表示を先にオフラインへ切り替える。
- Discord webhook を用いた起動開始通知、ready 通知、終了通知、ログ通知を任意で有効化できる。
- サーバー単位で Bot の有効 / 無効、利用チャンネル、モデル、システムプロンプト、制限値を管理できる構造にする。
- 管理者向け slash command で運用設定を確認 / 変更できるようにする。

### 主な業務フロー
1. アプリ起動時に設定を読み込む。
2. Discord クライアント、Ollama クライアント、永続化層、監視通知を初期化する。
3. 必要に応じて Ollama prewarm を実行する（メインモデル）。
4. Bot が Discord イベントを購読する。
5. Bot が mention されたメッセージ、または Bot の返信に対する reply を会話対象として抽出する。
6. サーバーごとの利用可否と入力制約を検証する。
7. SQLite から会話履歴とサーバー設定を取得し、会話コンテキストを構築する。
8. 推論キューに積み、前のリクエスト完了を待つ（待機中は `Waiting...` を表示）。
9. `WEB_SEARCH_ENABLED=true` の場合、Stage 1 として検索要否を判定する。
   - メインモデルが 1 回の JSON 呼び出しで判定とクエリ生成を実施（「判定中…」を表示）。
   - 複数の独立した知識が必要なときは複数クエリを返し、Brave Search API を並列実行する。
   - 検索する場合は結果を Stage 2 のコンテキストに追加する。
10. Stage 2 としてメインモデルが最終回答を生成し、Discord に返信する。
11. 返信本文と presence を更新する。
12. 終了シグナル受信時に新規受付を止め、未完了タスクを順次停止する。

### 重要な制約
- Discord 側制限に合わせて応答文字数を制御する。
- Ollama 応答遅延や失敗を考慮し、タイムアウトとユーザ向けエラーメッセージを持つ。
- 同時に複数問い合わせが来た場合でも、推論は 1 本ずつ直列で処理する。
- 待機中メッセージと presence 更新が Discord のレート制限へ過度に抵触しないようにする。
- 監視通知の失敗で Bot 本体を停止させない。

## インターフェース
### 受信メッセージ処理
- 目的: Discord からのユーザ入力を受け取り、LLM 応答を返す。
- 入力:
  - Discord イベント
  - メッセージ本文
  - 投稿者 ID
  - サーバー ID / チャンネル ID
- 出力:
  - Discord 返信メッセージ
  - ログイベント
  - 任意の監視通知
- 動作:
  - 正常系:
    - Bot への mention を含むメッセージ、または Bot の返信に対する reply を抽出する。
    - サーバー設定と会話履歴を SQLite から取得する。
    - 通常の mention では、mention を除去した当該メッセージ本文だけを Ollama に渡す。
    - Bot の返信に対する reply では、保存済みの返信チェーンをたどって会話コンテキストを組み立てる。
    - まず待機メッセージを返信し、キュー待ち件数を表示する。
    - Ollama にリクエストし、生成結果を一括返信する。
    - 推論完了時に最新のトークンスピードを presence に反映する。
    - 完了後にユーザ入力とモデル応答を履歴として保存する。
  - バリデーション失敗:
    - 対象外チャンネル、空メッセージ、長すぎる入力は処理せず案内文を返すか黙って無視する。
  - 実行時失敗:
    - Ollama 到達不能、タイムアウト、Discord 返信失敗時はログ出力し、可能なら簡潔な失敗メッセージを返す。
    - 待機メッセージ更新や presence 更新に失敗しても Bot 全体は停止させない。

### `/stats` スラッシュコマンド
- 目的: 実行したチャンネルの最新推論ログを確認する。
- 入力:
  - slash command 実行（チャンネル ID を自動取得）
- 出力:
  - チャンネル全体への応答（全員に表示）
- 動作:
  - 正常系:
    - `inference_logs` テーブルから当該チャンネルの最新ログを 1 件取得する。
    - メッセージ受信時刻を先頭に表示する。
    - Stage 1（検索判定）の所要時間と消費トークン数（prompt + completion）を表示する。
    - 検索が発生した場合は検索クエリ数を表示する。
    - Stage 2（推論）の所要時間と消費トークン数（prompt + completion）を表示する。
    - `reply_sent_at` が記録されている場合は返信完了時刻を末尾に表示する。
  - ログ未存在:
    - 「このチャンネルにはまだ推論ログがありません。」を返す。
- 表示例:
  ```
  **最後の推論ログ（このチャンネル）**
  メッセージ受信: 2026-05-10T12:00:00.000Z
  Stage 1（検索判定）: 0.83 秒 | prompt 512 + completion 48 トークン
  検索クエリ数: 2
  Stage 2（推論）: 12.40 秒 | prompt 1024 + completion 200 トークン
  返信完了: 2026-05-10T12:00:13.500Z
  ```
- 登録方式: `setup_hook()` 内で `app_commands.CommandTree.sync()` を呼び出し、ボット起動時にグローバル登録する。

### 管理用 slash command（未実装）
- 目的: サーバーごとのモデル名、システムプロンプト、利用制限などの運用設定を管理する。
- 入力:
  - slash command 名
  - 実行した管理者の権限情報
  - 対象サーバー ID
  - 更新対象の設定値
- 出力:
  - 更新済み設定
  - ログイベント
- 動作:
  - 正常系:
    - 実行者が管理権限を持つことを検証する。
    - 入力値を検証し、SQLite のサーバー設定へ反映する。
    - 更新結果を管理者へ返す。
  - バリデーション失敗:
    - 権限不足や不正値はエラーメッセージを返し、設定は更新しない。
  - 実行時失敗:
    - 永続化更新失敗時はロールバックまたは前回値を維持する。

### 起動時設定ロード
- 目的: 共通環境設定とサーバー単位設定ストアを初期化する。
- 入力:
  - 環境変数
  - SQLite データベースファイル
- 出力:
  - アプリ設定
  - サーバー設定リポジトリ
- 動作:
  - 正常系:
    - 必須環境変数を読み込む。
    - SQLite スキーマを初期化する。
    - サーバー設定未登録時に既定値を使える状態にする。
  - バリデーション失敗:
    - 不正な URL、タイムアウト、文字数上限は起動失敗または既定値へフォールバックする。
  - 実行時失敗:
    - DB 初期化失敗時は起動を中断する。

## 設定
- `DISCORD_BOT_TOKEN`: Discord bot token。必須。
- `DISCORD_MENTION_RESPONSE`: 本文が空の mention を受けたときの案内文。
- `OLLAMA_BASE_URL`: Ollama API のベース URL。ホストで Ollama を起動している場合の既定値は `http://host.docker.internal:11434`。
- `OLLAMA_MODEL`: 利用する Ollama モデル名。例: `qwen3.6:27b`, `gemma4:26b`。
- `OLLAMA_KEEP_ALIVE`: Ollama 側でモデルを保持する時間。
- `OLLAMA_PREWARM_ENABLED`: 起動前に prewarm を行うかどうか。
- `OLLAMA_PREWARM_PROMPT`: prewarm 用プロンプト。
- `SYSTEM_PROMPT`: 既定のシステムプロンプト。
- `DEFAULT_ALLOWED_CHANNEL_IDS`: サーバー設定未登録時に使う許可チャンネル ID 一覧。
- `MAX_HISTORY_MESSAGES`: 会話コンテキストに含める最大メッセージ数。
- `MAX_RESPONSE_CHARS`: Discord 返信の最大文字数。
- `SHOW_STEPS`: 推論進捗ステップを積み重ねて表示するかどうか。`true` にすると判定・検索・推論の完了を順に表示し、最終応答の前に残す。`false`（既定）では途中ステップを都度置き換え、最終応答のみを残す。
- `STREAMING_UPDATE_INTERVAL_MS`: 段階表示時の更新間隔。
- `OLLAMA_TIMEOUT_SECONDS`: Ollama 応答待機タイムアウト。
- `VISION_ENABLED`: vision 対応モデルで画像添付入力を有効にするか。
- `VISION_IMAGE_ONLY_PROMPT`: 画像のみ添付されて本文がないときに使う既定プロンプト。
- `VISION_MAX_PIXELS`: 画像縮小後の最大画素数。
- `WEB_SEARCH_ENABLED`: Brave Search API による Web 検索補強を有効にするか。
- `BRAVE_SEARCH_API_KEY`: Brave Search API キー。`WEB_SEARCH_ENABLED=true` のとき必須。
- `WEB_SEARCH_MAX_RESULTS`: 検索結果の最大取得件数。
- `WEB_SEARCH_TIMEOUT_SECONDS`: Brave Search API 1 回あたりのタイムアウト秒数。
- `WEB_SEARCH_COUNTRY`: Brave Search の地域設定。
- `WEB_SEARCH_LANGUAGE`: Brave Search の言語設定。
- `LOG_LEVEL`: ログ出力レベル。
- `DISCORD_WEBHOOK_URL`: Discord webhook 通知先 URL。
- `DISCORD_WEBHOOK_NOTIFY_STARTUP`: 起動通知を送るかどうか。
- `DISCORD_WEBHOOK_NOTIFY_SHUTDOWN`: 終了通知を送るかどうか。
- `DISCORD_WEBHOOK_NOTIFY_LOGS`: 通常ログ通知を送るかどうか。
- `DISCORD_WEBHOOK_NOTIFY_LOGS_MIN_LEVEL`: 通常ログ通知の最小ログレベル。
- `DATA_DIR`: 永続化データ保存先。
- `SQLITE_PATH`: SQLite データベースファイルパス。

## 永続化仕様
### SQLite を使う理由
- 会話履歴とサーバー設定を単一ファイルで扱え、ローカル運用と相性がよい。
- 起動時にスキーマ確認しやすく、テストでも再現しやすい。

### 想定テーブル
- `guild_settings`
  - `guild_id`
  - `is_enabled`
  - `allowed_channel_ids`
  - `ollama_model`
  - `system_prompt`
  - `max_history_messages`
  - `max_response_chars`
  - `updated_at`
- `conversation_messages`
  - `id`
  - `discord_message_id`
  - `reply_to_message_id`
  - `guild_id`
  - `channel_id`
  - `user_id`
  - `role`
  - `content`
  - `created_at`
- `runtime_events`
  - `id`
  - `guild_id`
  - `event_type`
  - `payload`
  - `created_at`
- `inference_logs`
  - `id`
  - `guild_id`
  - `channel_id`
  - `user_id`
  - `message_received_at`（UTC ISO 8601 Z サフィックス）
  - `decision_started_at` / `decision_ended_at`（Stage 1 の開始・終了）
  - `search_started_at` / `search_ended_at`（Brave Search の開始・終了）
  - `inference_started_at` / `inference_ended_at`（Stage 2 の開始・終了）
  - `reply_sent_at`（返答送信完了時刻）
  - `decision_prompt_tokens` / `decision_completion_tokens`（Stage 1 のトークン数）
  - `inference_prompt_tokens` / `inference_completion_tokens`（Stage 2 のトークン数）
  - `search_query_count`（発行した検索クエリ数）
  - `is_error`（OllamaClientError 発生フラグ）
  - `gpu_avg_watts`（推論ターン中の GPU 平均消費電力 W、NVIDIA GPU 非搭載時は NULL）
  - `gpu_energy_joules`（推論ターン中の GPU 推定消費エネルギー J、NVIDIA GPU 非搭載時は NULL）

## ログと監視
- INFO:
  - 起動開始
  - prewarm 開始 / 完了
  - Discord 接続完了
  - 受信イベント受付
  - Ollama 推論開始 / 完了
  - presence 更新
  - 応答送信完了
  - graceful shutdown 開始 / 完了
- WARNING:
  - 設定値のフォールバック
  - 許可外チャンネルからの利用
  - 管理権限不足での管理コマンド拒否
  - Ollama 一時失敗からの劣化継続
- ERROR / EXCEPTION:
  - Discord 接続失敗
  - Ollama 初期接続失敗
  - 永続化層障害
  - 返信不能な処理失敗
- 通知条件:
  - 起動失敗
  - 起動完了
  - graceful shutdown 開始
  - 連続する Ollama 呼び出し失敗
  - 未処理例外

## 起動時動作
- 環境変数を読み込み、型と必須値を検証する。
- SQLite スキーマを初期化する。
- 起動開始通知が有効なら webhook を送る。
- prewarm が有効な場合は、Discord 接続前に 1 回 Ollama を warmup する。
- Discord クライアントを起動し、イベントハンドラを登録する。
- ready 到達後に ready 通知が有効なら webhook を送る。
- 起動失敗条件:
  - `DISCORD_BOT_TOKEN` 未設定
  - prewarm 実行時の Ollama 接続不可
  - prewarm 実行時の指定モデル未取得
  - SQLite 初期化失敗

## 終了時動作
- 終了シグナルまたは例外停止要求を受けたら、新規イベント受付を止める。
- graceful shutdown 開始時に Bot の表示をオフラインへ切り替える。
- 処理中リクエストをキャンセルまたは待機する。
- Discord クライアントを切断する。
- Ollama クライアントのセッションを閉じる。
- 段階表示中の更新タスクを停止する。
- SQLite 接続を close する。
- 監視通知が必要なら最後に送る。

## 想定モジュール分割
- `main.py`: 起動、依存組み立て、シグナル処理。
- `config.py`: 環境変数読み込みと設定検証。
- `constants.py`: 既定値と制限値。
- `messages.py`: ユーザ向け / ログ向け文言。
- `integrations/discord_client.py`: Discord 連携。
- `integrations/ollama_client.py`: Ollama 連携。
- `webhook_logging.py`: Discord webhook 通知と logging handler。
- `services/chat_service.py`: 会話処理のユースケース。
- `services/context_builder.py`: 会話履歴整形。
- `services/inference_queue.py`: 推論直列化とキュー状態管理。
- `services/presence_service.py`: presence 表示組み立て。
- `services/gpu_power_sampler.py`: NVML 経由の GPU 消費電力サンプリング。NVIDIA 環境以外では無効化。
- `services/admin_command_service.py`: slash command のユースケース。
- `storage/settings_repository.py`: サーバー設定保存。
- `storage/conversation_repository.py`: 会話履歴保存。
- `storage/inference_log_repository.py`: 推論ログ保存。
- `storage/database.py`: SQLite 接続とスキーマ管理。
- `domain/inference_log.py`: 推論ログのデータクラス。
