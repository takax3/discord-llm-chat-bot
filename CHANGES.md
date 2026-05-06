# Changes

## Unreleased
- Discord + Ollama + Qwen チャットボット向けの初期仕様と設計ドキュメントを追加
- Dockerfile と docker-compose.yml を追加し、Bot と Ollama を Docker で起動できるようにした
- Docker サービス名と Python package 名を `discordbot` に変更した
- Discord 接続と mention 固定応答による最小疎通実装を追加した
- SQLite 初期化と `guild_settings` 読み込みによるサーバー単位設定の土台を追加した
- メンション本文のみを使う単発 Ollama 応答フローを追加した
- Docker Compose 起動時に `ollama-init` でモデルを自動取得するようにした
- 推論開始時に待機メッセージを返し、完了後に編集するようにした
- `ollama` サービスに `gpus: all` を追加し、GPU 推論前提の Compose 構成にした
- `ollama` サービスを NVIDIA device reservation と healthcheck ベースの GPU 構成へ調整した
- Bot の返信に reply したとき、保存済みの返信チェーンを会話コンテキストとして引き継ぐようにした
