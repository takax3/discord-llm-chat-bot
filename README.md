# Discord LLM Chat Bot

Discord 上で動作する、Ollama ベースのローカル LLM チャットボットです。  
`Qwen3.x` や `Gemma 4` などの Ollama モデルを切り替えて利用でき、会話コンテキスト管理・監視・graceful shutdown を備えます。

- 開発者向けの正本仕様は `SPECIFICATION.md` を参照してください。
- モジュール設計の概要は `docs/architecture.md` を参照してください。

## 機能

- mention を起点にした Ollama 応答
- Bot 返信への reply での会話継続（保存済みチェーンを会話コンテキストとして引き継ぎ）
- vision 対応モデルへの画像添付入力（本文なし画像は既定プロンプトで補完）
- 条件付き Web 検索による回答補強（Brave Search API、回答末尾に参考 URL 最大 3 件表示）
  - メインモデルが検索要否を判定しクエリを生成（`decide_combined`、推奨）
  - 別途ルーターモデルを指定した場合は多段ステップで判定し、各ステップを Discord にリアルタイム表示
- システムプロンプトへの現在日時（JST）自動注入
- 推論直列化（前の推論完了まで次を待機）と presence へのキュー数・推論速度表示
- SQLite への会話履歴保存とサーバー単位設定管理
- Discord webhook 通知（起動開始・ready・終了・ログ）、複数 URL のカンマ区切り指定に対応
- 起動前 Ollama prewarm（メインモデルとルーターモデルの両方）
- GPU 前提の Docker Compose 構成（NVIDIA device reservation）
- graceful shutdown（シグナル受信時に先にオフライン表示へ切り替え）

## 未実装

- 管理者向け slash command によるサーバー設定変更
- ストリーミング表示・応答分割送信
- レート制限・再試行ポリシー
- 履歴要約

## Docker での起動

1. `.env.example` を `.env` としてコピーし、必要な値を設定します。
   - `DISCORD_BOT_TOKEN`: 必須。
   - `OLLAMA_MODEL`: 利用するモデル名（例: `gemma4:26b`、`qwen3.6:27b`）。
   - `SYSTEM_PROMPT`: モデルへ渡す基本システムプロンプト。
   - `VISION_ENABLED=true` にすると vision 対応モデルで画像添付入力が使えます。
   - `WEB_SEARCH_ENABLED=true` にすると Brave Search API による Web 検索補強が有効になります。合わせて `BRAVE_SEARCH_API_KEY` も設定してください。
   - `OLLAMA_ROUTER_MODEL` を設定しない場合（推奨）、メインモデルが検索判定も行います。別の小規模モデルを指定すると多段ルーターとして動作しますが、1B モデルは精度が不安定なため非推奨です。
2. `docker compose up --build -d` を実行します。
3. 初回起動時は `ollama-init` サービスが `OLLAMA_MODEL` のモデルを自動取得します（時間がかかる場合があります）。
   - 進捗確認: `docker compose logs -f ollama-init`
4. Ollama prewarm 完了後に Discord 接続します。
   - 進捗確認: `docker compose logs -f discordbot`
5. GPU 推論前提のため、`ollama` サービスには NVIDIA GPU の予約を明示しています。Docker Desktop / NVIDIA Container Toolkit で GPU 利用が有効になっている必要があります。
   - 確認コマンド: `docker compose exec ollama nvidia-smi`
6. Webhook 通知を使う場合は `.env` で次を設定します。
   - `DISCORD_WEBHOOK_URL`: 通知先 webhook URL。複数指定はカンマ区切り。
   - `DISCORD_WEBHOOK_NOTIFY_STARTUP` / `DISCORD_WEBHOOK_NOTIFY_SHUTDOWN` / `DISCORD_WEBHOOK_NOTIFY_LOGS`
   - `DISCORD_WEBHOOK_NOTIFY_LOGS_MIN_LEVEL`
7. モデル別の推奨設定例は次を参照してください。
   - `docs/ollama-gemma4-26b-rtx3090.md`
   - `docs/ollama-qwen3.6-rtx3090.md`

`docker-compose.yml` は `discordbot`・`ollama`・`ollama-init` の 3 サービス構成です。Bot からは `http://ollama:11434` で Ollama に接続します。会話履歴と設定 DB は Docker volume `discordbot-data` に、Ollama のモデルは `ollama-data` に保存されます。

## 技術スタック

| 用途 | 採用技術 |
|---|---|
| 言語 | Python 3.14 |
| Discord 連携 | discord.py |
| LLM 推論 | Ollama（ローカル HTTP API）|
| Web 検索 | Brave Search API |
| 永続化 | SQLite |
| コンテナ | Docker Compose（NVIDIA GPU 対応）|
