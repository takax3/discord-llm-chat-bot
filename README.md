# Discord LLM Chat Bot

Discord 上で動作する、Ollama + Qwen ベースのローカル LLM チャットボットです。  
Discord との接続、Ollama への推論依頼、会話コンテキスト構築、監視や graceful shutdown を責務分離して実装する前提で設計を進めています。

## 現在の状態
- このリポジトリは設計開始段階です。
- 利用者向けの概要はこの README に記載します。
- 開発者向けの正本仕様は `SPECIFICATION.md` に記載します。
- モジュール分割案は `docs/architecture.md` に記載します。

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

## セットアップ予定
詳細は実装開始後に更新します。現時点では `SPECIFICATION.md` の内容をもとに要件と設計を詰めている段階です。
