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
  - メインモデルが検索要否を 1 回の JSON 呼び出しで判定しクエリを生成
  - 複数の独立した知識が必要なとき複数クエリを並列実行
- システムプロンプトへの現在日時（JST）自動注入
- 推論直列化（前の推論完了まで次を待機）と presence へのモデル名・キュー数・推論速度表示
- SQLite への会話履歴保存とサーバー単位設定管理
- 推論ログの SQLite 記録（タイムスタンプ・トークン数・検索クエリ数・エラーフラグ・GPU 消費電力/エネルギーを推論ごとに保存）
- `/stats` スラッシュコマンド（チャンネルの最新推論ログを全体表示：メッセージ受信時刻・Stage 1/Stage 2 の所要時間とトークン数・検索クエリ数・返信完了時刻・GPU 消費電力 W / kWh）
- `/preset` スラッシュコマンドグループによるプリセットプロンプト管理
  - `add` / `update` / `delete` / `list` / `show` / `use` の 6 サブコマンド
  - `add` / `update` は `prompt` 引数を省略するとモーダル（複数行テキストエリア、最大 4000 文字）で入力
  - `use` でサーバー内に anchor メッセージを送信し、そのメッセージへの reply チェーンにのみプリセットが適用される
  - プリセット削除後も進行中の reply チェーンはそのまま継続（anchor に内容を直接保存しているため）
  - ギルドごとに独立して管理。権限制限なし（全員操作可）
- Discord webhook 通知（起動開始・ready・終了・ログ）、複数 URL のカンマ区切り指定に対応
- 起動前 Ollama prewarm（メインモデル）
- GPU 前提の構成（Ollama はホストで起動し、Bot コンテナが `host.docker.internal` 経由で接続）
- graceful shutdown（シグナル受信時に先にオフライン表示へ切り替え）

## 未実装

- 管理者向け slash command によるサーバー設定変更（`/stats` は実装済み。設定の確認・変更コマンドは未実装）
- ストリーミング表示・応答分割送信
- レート制限・再試行ポリシー
- 履歴要約

## Docker での起動

前提:
- Ollama をホスト上で起動しておく必要があります。Bot コンテナは `host.docker.internal:11434` 経由でホストの Ollama に接続します。
- GPU 消費電力を記録する場合は、ホストに NVIDIA Container Toolkit が必要です。未インストールの場合も Bot 本体は起動しますが、`inference_logs` の `gpu_avg_watts` / `gpu_energy_joules` が `NULL` になります。

1. `.env.example` を `.env` としてコピーし、必要な値を設定します。
   - `DISCORD_BOT_TOKEN`: 必須。
   - `OLLAMA_MODEL`: 利用するモデル名（例: `gemma4:26b`、`qwen3.6:27b`）。
   - `OLLAMA_BASE_URL`: Ollama への接続 URL。ホストで Ollama を起動している場合は既定値の `http://host.docker.internal:11434` をそのまま使えます。
   - `SYSTEM_PROMPT`: モデルへ渡す基本システムプロンプト。
   - `VISION_ENABLED=true` にすると vision 対応モデルで画像添付入力が使えます。
   - `WEB_SEARCH_ENABLED=true` にすると Brave Search API による Web 検索補強が有効になります。合わせて `BRAVE_SEARCH_API_KEY` も設定してください。

2. ホスト上で Ollama を起動し、使用するモデルをあらかじめ取得しておきます。
   ```
   ollama pull gemma4:26b
   ```

3. `docker compose up --build -d` を実行します。
4. Ollama prewarm 完了後に Discord 接続します。
   - 進捗確認: `docker compose logs -f discordbot`
5. Webhook 通知を使う場合は `.env` で次を設定します。
   - `DISCORD_WEBHOOK_URL`: 通知先 webhook URL。複数指定はカンマ区切り。
   - `DISCORD_WEBHOOK_NOTIFY_STARTUP` / `DISCORD_WEBHOOK_NOTIFY_SHUTDOWN` / `DISCORD_WEBHOOK_NOTIFY_LOGS`
   - `DISCORD_WEBHOOK_NOTIFY_LOGS_MIN_LEVEL`

`docker-compose.yml` は `discordbot` サービスのみのシンプルな構成です。会話履歴と設定 DB は Docker volume `discordbot-data` に保存されます。

## 技術スタック

| 用途 | 採用技術 |
|---|---|
| 言語 | Python 3.14 |
| Discord 連携 | discord.py |
| LLM 推論 | Ollama（ローカル HTTP API）|
| Web 検索 | Brave Search API |
| 永続化 | SQLite |
| コンテナ | Docker Compose（NVIDIA GPU 対応）|
