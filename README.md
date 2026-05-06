# Discord LLM Chat Bot

Discord 上で動作する、Ollama + Qwen ベースのローカル LLM チャットボットです。  
Discord との接続、Ollama への推論依頼、会話コンテキスト構築、監視や graceful shutdown を責務分離して実装する前提で設計を進めています。

## 現在の状態
- このリポジトリは最小疎通実装まで完了しています。
- 利用者向けの概要はこの README に記載します。
- 開発者向けの正本仕様は `SPECIFICATION.md` に記載します。
- モジュール分割案は `docs/architecture.md` に記載します。
- 現在は Discord に接続し、Bot への mention に固定文で応答できます。

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
   - `DISCORD_MENTION_RESPONSE` を変えると、mention への固定応答文を変更できます。
2. `docker compose up --build -d` を実行します。
3. 初回は Ollama コンテナ内でモデルを取得します。

```bash
docker compose exec ollama ollama pull qwen3:8b
```

4. ログ確認は `docker compose logs -f discordbot` を使います。

`docker-compose.yml` は `discordbot` と `ollama` の 2 サービス構成です。Bot からは `http://ollama:11434` で Ollama に接続します。会話履歴と設定 DB は Docker volume `discordbot-data` に保存され、Ollama のモデルは `ollama-data` に保存されます。
