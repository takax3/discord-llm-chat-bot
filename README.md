# Discord LLM Chat Bot

Discord 上で動作する、Ollama ベースのローカル LLM チャットボットです。  
現在は `Qwen3.x` や `Gemma 4` などの Ollama モデルを切り替えて利用でき、Discord との接続、Ollama への推論依頼、会話コンテキスト構築、監視、graceful shutdown を責務分離して実装しています。

## 現在の状態
- 利用者向けの概要はこの README に記載します。
- 開発者向けの正本仕様は `SPECIFICATION.md` に記載します。
- モジュール分割案は `docs/architecture.md` に記載します。
- 現在は Discord に接続し、Bot への mention 本文だけを Ollama に渡して応答できます。
- Bot の返信に対する reply では、保存済みの返信チェーンをたどって会話コンテキストを引き継げます。
- 画像が添付されている場合は、vision 対応モデルに対して現在メッセージの画像 1 枚を推論に含められます。
- 本文なしの画像だけのメッセージでは、画像内容の推定を依頼する既定プロンプトを内部的に補います。
- Ollama 推論中は先に `Thinking... (Queue ahead: N)` を返し、完了後にそのメッセージを更新します。
- 推論リクエストは bot 内で直列化し、前の推論が終わるまで次の推論は待機します。
- サーバー設定が未登録のときは環境変数の既定値を使い、登録済みサーバーでは SQLite 設定を参照します。
- 起動時には SQLite 初期化、Ollama prewarm、Discord 接続を順番に行います。
- Discord の presence には現在の待機キュー数と直近の推論速度を表示します。
- 終了処理開始時は Bot の表示を先にオフラインへ切り替えます。
- Discord webhook による起動開始通知、ready 通知、終了通知、ログ通知を任意で有効化できます。
- Docker Compose では `discordbot`、`ollama`、`ollama-init` の 3 サービスで起動します。

## 主な機能
- mention を起点にした Ollama 応答
- Bot 返信への reply での会話継続
- vision 対応モデルへの画像添付入力
- SQLite への会話履歴保存
- サーバー単位の有効 / 無効、許可チャンネル設定
- 起動前 prewarm
- webhook 通知
- GPU 前提の Docker Compose 構成

## 目指す機能
- Discord で Bot が mention されたメッセージを受け取って Ollama モデルへ渡す
- より洗練されたストリーミング表示や応答分割送信
- サーバーごとにチャンネル制限、システムプロンプト、応答長などを管理する
- 管理者向け slash command で設定を変更する
- 起動時検証、障害ログ、通知、graceful shutdown を備える

## 想定技術
- Python
- Discord API
- Ollama
- Ollama 互換のローカルモデル
- 任意のローカル永続化層

## Docker での起動
1. `.env.example` を `.env` としてコピーし、`DISCORD_BOT_TOKEN` など必要な値を設定します。
   - `DISCORD_MENTION_RESPONSE` は本文が空のときの案内文として使われます。
   - モデル設定は `OLLAMA_MODEL` で切り替えます。
   - 画像入力を使う場合は `VISION_ENABLED=true` のままにし、vision 対応モデルを選びます。
2. `docker compose up --build -d` を実行します。
3. 初回起動時は `ollama-init` サービスが `OLLAMA_MODEL` のモデルを自動取得します。
   - 初回はモデル取得に時間がかかることがあります。
   - 状況確認は `docker compose logs -f ollama-init` を使います。
4. 起動時は `Ollama prewarm` が完了してから Discord に接続します。
   - 状況確認は `docker compose logs -f discordbot` を使います。
5. GPU 推論を使う前提で、`ollama` サービスには NVIDIA GPU の予約を明示しています。
   - Docker Desktop / NVIDIA Container Toolkit 側で GPU 利用が有効になっている必要があります。
   - `docker compose exec ollama nvidia-smi` で GPU が見えるか確認できます。
6. Webhook 通知を使う場合は、必要に応じて `.env` に次を設定します。
   - `DISCORD_WEBHOOK_URL`
   - `DISCORD_WEBHOOK_NOTIFY_STARTUP`
   - `DISCORD_WEBHOOK_NOTIFY_SHUTDOWN`
   - `DISCORD_WEBHOOK_NOTIFY_LOGS`
   - `DISCORD_WEBHOOK_NOTIFY_LOGS_MIN_LEVEL`
7. モデル別の推奨設定例は次を参照してください。
   - `docs/ollama-gemma4-26b-rtx3090.md`
   - `docs/ollama-qwen3.6-rtx3090.md`

`docker-compose.yml` は `discordbot`、`ollama`、`ollama-init` の 3 サービス構成です。Bot からは `http://ollama:11434` で Ollama に接続します。会話履歴と設定 DB は Docker volume `discordbot-data` に保存され、Ollama のモデルは `ollama-data` に保存されます。
