# Specification

## 概要
- 目的: Discord サーバー上で動作する、Ollama + Qwen ベースのローカル LLM チャットボットを提供する。
- 対象利用者: 自前サーバーまたはローカル PC 上で Discord bot を運用したい個人開発者または小規模チーム。
- 外部依存:
  - Discord Gateway / REST API
  - Ollama HTTP API
  - Qwen 系モデル
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
- 受信メッセージを整形し、Ollama 上の Qwen モデルへプロンプトとして送る。
- モデル応答を Discord メッセージとして段階表示で返す。
- サーバー単位で Bot の有効 / 無効、利用チャンネル、モデル、システムプロンプト、制限値を管理できる構造にする。
- 管理者向け slash command で運用設定を確認 / 変更できるようにする。

### 主な業務フロー
1. アプリ起動時に設定を読み込む。
2. Discord クライアント、Ollama クライアント、永続化層、監視通知を初期化する。
3. Bot が Discord イベントを購読する。
4. Bot が mention されたメッセージのみを会話対象として抽出する。
5. サーバーごとの利用可否と入力制約を検証する。
6. SQLite から会話履歴とサーバー設定を取得し、会話コンテキストを構築する。
7. Qwen へ問い合わせ、応答を段階的に Discord へ反映する。
8. 終了シグナル受信時に新規受付を止め、未完了タスクを順次停止する。

### 重要な制約
- Discord 側制限に合わせて応答文字数を制御する。
- Ollama 応答遅延や失敗を考慮し、タイムアウトとユーザ向けエラーメッセージを持つ。
- 同一チャンネルで同時に複数問い合わせが来た場合、メッセージ更新競合を避ける方針を持つ。
- 段階表示中に Discord 編集制限やレート制限へ抵触しない更新頻度に制御する。
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
    - Bot への mention を含むメッセージのみを抽出する。
    - サーバー設定と会話履歴を SQLite から取得する。
    - 現在の実装では、mention を除去した当該メッセージ本文だけを Ollama に渡す。
    - Ollama に単発リクエストし、生成結果を一括返信する。
    - 完了後にユーザ入力とモデル応答を履歴として保存する。
  - バリデーション失敗:
    - 対象外チャンネル、空メッセージ、長すぎる入力は処理せず案内文を返すか黙って無視する。
  - 実行時失敗:
    - Ollama 到達不能、タイムアウト、Discord 返信失敗時はログ出力し、可能なら簡潔な失敗メッセージを返す。
    - 段階表示中に失敗した場合は最終状態を失敗文面へ更新するか、追補メッセージで失敗を通知する。

### 管理用 slash command
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
- `OLLAMA_BASE_URL`: Ollama API のベース URL。Docker Compose 前提の既定値は `http://ollama:11434`。
- `OLLAMA_MODEL`: 利用する Qwen モデル名。例: `qwen3:8b`。
- `SYSTEM_PROMPT`: 既定のシステムプロンプト。
- `DEFAULT_ALLOWED_CHANNEL_IDS`: サーバー設定未登録時に使う許可チャンネル ID 一覧。
- `MAX_HISTORY_MESSAGES`: 会話コンテキストに含める最大メッセージ数。
- `MAX_RESPONSE_CHARS`: Discord 返信の最大文字数。
- `STREAMING_UPDATE_INTERVAL_MS`: 段階表示時の更新間隔。
- `OLLAMA_TIMEOUT_SECONDS`: Ollama 応答待機タイムアウト。
- `LOG_LEVEL`: ログ出力レベル。
- `NOTIFY_WEBHOOK_URL`: 任意の障害通知先 webhook。
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
  - `guild_id`
  - `channel_id`
  - `user_id`
  - `role`
  - `content`
  - `discord_message_id`
  - `created_at`
- `runtime_events`
  - `id`
  - `guild_id`
  - `event_type`
  - `payload`
  - `created_at`

## ログと監視
- INFO:
  - 起動完了
  - Discord 接続完了
  - 受信イベント受付
  - slash command 実行受付
  - Ollama 推論開始 / 完了
  - 応答段階更新
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
  - 連続する Ollama 呼び出し失敗
  - 未処理例外

## 起動時動作
- 環境変数を読み込み、型と必須値を検証する。
- Ollama 接続先の疎通確認を行う。
- 利用モデルが利用可能か確認する。
- SQLite スキーマを初期化する。
- Discord クライアントを起動し、イベントハンドラを登録する。
- slash command を同期する。
- 起動失敗条件:
  - `DISCORD_BOT_TOKEN` 未設定
  - Ollama 接続不可
  - 指定モデル未取得
  - SQLite 初期化失敗
  - slash command 同期失敗

## 終了時動作
- 終了シグナルまたは例外停止要求を受けたら、新規イベント受付を止める。
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
- `services/chat_service.py`: 会話処理のユースケース。
- `services/context_builder.py`: 会話履歴整形。
- `services/admin_command_service.py`: slash command のユースケース。
- `services/streaming_service.py`: 応答段階表示の制御。
- `storage/settings_repository.py`: サーバー設定保存。
- `storage/history_repository.py`: 会話履歴保存。
- `storage/database.py`: SQLite 接続とスキーマ管理。
- `monitoring/notifier.py`: 障害通知。
