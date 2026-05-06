# Changes

## Unreleased
- Discord + Ollama + Qwen チャットボット向けの初期仕様と設計ドキュメントを追加
- Dockerfile と docker-compose.yml を追加し、Bot と Ollama を Docker で起動できるようにした
- Docker サービス名と Python package 名を `discordbot` に変更した
- Discord 接続と mention 固定応答による最小疎通実装を追加した
- SQLite 初期化と `guild_settings` 読み込みによるサーバー単位設定の土台を追加した
