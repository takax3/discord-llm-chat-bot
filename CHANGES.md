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
- graceful shutdown 開始時に Bot の表示を先にオフラインへ切り替えるようにした
- Discord webhook による起動通知、終了通知、ログ通知を任意で有効化できるようにした
- Ollama prewarm を起動処理に追加し、起動開始通知と ready 通知を分けて送るようにした
- Gemma 4 26B と Qwen3.6 の RTX 3090 向け設定ガイドを追加した
- Discord presence に待機キュー数と直近のトークンスピードを表示するようにした
- vision 対応モデルに対して Discord 添付画像 1 枚を推論へ渡せるようにした
- Brave Search API を使った条件付き Web 検索補強を追加した
