# Discord LLM Chat Bot

Discord 上で動作する、Ollama + Qwen ベースのローカル LLM チャットボットです。  
Discord との接続、Ollama への推論依頼、会話コンテキスト構築、監視や graceful shutdown を責務分離して実装する前提で設計を進めています。

## 現在の状態
- このリポジトリは最小疎通実装まで完了しています。
- SQLite 初期化とサーバー単位設定の読み込みまで完了しています。
- メンション本文だけを使う単発 Ollama 応答まで完了しています。
- 推論中は先に簡単な待機メッセージを返すようになっています。
- 利用者向けの概要はこの README に記載します。
- 開発者向けの正本仕様は `SPECIFICATION.md` に記載します。
- モジュール分割案は `docs/architecture.md` に記載します。
- 現在は Discord に接続し、Bot への mention 本文だけを Ollama に渡して応答できます。
- Bot の返信に対する reply では、保存済みの返信チェーンをたどって会話コンテキストを引き継げます。
- Ollama 推論中は先に `Thinking...` を返し、完了後にそのメッセージを更新します。
- サーバー設定が未登録のときは環境変数の既定値を使い、登録済みサーバーでは SQLite 設定を参照します。
- 終了処理開始時は Bot の表示を先にオフラインへ切り替えます。
- Discord webhook による起動通知、終了通知、ログ通知を任意で有効化できます。

## 目指す機能
- Discord で Bot が mention されたメッセージを受け取って Qwen モデルへ渡す
- Ollama の応答を Discord へ段階表示で返信する
- SQLite に会話履歴を保存する
- サーバーごとにチャンネル制限、システムプロンプト、応答長などを管理する
- 管理者向け slash command で設定を変更する
- 起動時検証、障害ログ、通知、graceful shutdown を備える

## 想定技術
- Python
- Discord API
- Ollama
- Qwen 系モデル
- 任意のローカル永続化層

## Docker での起動
1. `.env.example` を `.env` としてコピーし、`DISCORD_BOT_TOKEN` など必要な値を設定します。
   - `DISCORD_MENTION_RESPONSE` は本文が空のときの案内文として使われます。
2. `docker compose up --build -d` を実行します。
3. 初回起動時は `ollama-init` サービスが `OLLAMA_MODEL` のモデルを自動取得します。
   - 初回はモデル取得に時間がかかることがあります。
   - 状況確認は `docker compose logs -f ollama-init` を使います。
4. Bot のログ確認は `docker compose logs -f discordbot` を使います。
5. GPU 推論を使う前提で、`ollama` サービスには NVIDIA GPU の予約を明示しています。
   - Docker Desktop / NVIDIA Container Toolkit 側で GPU 利用が有効になっている必要があります。
   - `docker compose exec ollama nvidia-smi` で GPU が見えるか確認できます。
6. Webhook 通知を使う場合は、必要に応じて `.env` に次を設定します。
   - `DISCORD_WEBHOOK_URL`
   - `DISCORD_WEBHOOK_NOTIFY_STARTUP`
   - `DISCORD_WEBHOOK_NOTIFY_SHUTDOWN`
   - `DISCORD_WEBHOOK_NOTIFY_LOGS`
   - `DISCORD_WEBHOOK_NOTIFY_LOGS_MIN_LEVEL`

`docker-compose.yml` は `discordbot`、`ollama`、`ollama-init` の 3 サービス構成です。Bot からは `http://ollama:11434` で Ollama に接続します。会話履歴と設定 DB は Docker volume `discordbot-data` に保存され、Ollama のモデルは `ollama-data` に保存されます。
