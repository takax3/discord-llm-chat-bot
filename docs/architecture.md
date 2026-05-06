# Architecture Draft

## 設計方針
- `SPECIFICATION.md` を実装判断の正本にする。
- Discord / Ollama / 永続化 / 通知を外部依存として分離する。
- 起動時に設定検証と依存疎通確認を済ませ、実行時分岐を減らす。
- graceful shutdown と監視を初期設計に含める。
- 既定挙動は environment で持ち、サーバーごとの差分は SQLite に保存する。

## 想定ディレクトリ構成
```text
src/discordbot/
  main.py
  config.py
  constants.py
  messages.py
  domain/
    chat.py
    events.py
    errors.py
  integrations/
    discord_client.py
    ollama_client.py
  services/
    admin_command_service.py
    chat_service.py
    context_builder.py
    moderation_service.py
    streaming_service.py
  storage/
    database.py
    history_repository.py
    settings_repository.py
  monitoring/
    notifier.py
    logging_setup.py
```

## リクエスト処理フロー
1. Discord integration がメッセージイベントを受信する。
2. mention もしくは Bot 返信への reply でない通常メッセージは無視する。
3. `settings_repository` がサーバー設定と利用制限を確認する。
4. `conversation_repository` と `context_builder` が SQLite 履歴を集めて LLM 入力へ整形する。
5. `chat_service` が待機メッセージを作成する。
6. `inference_queue` が推論を直列化し、キュー待ち件数を管理する。
7. `ollama_client` が利用モデルへ問い合わせる。
8. `presence_service` がキュー数と直近のトークンスピードをもとにステータス文言を組み立てる。
9. 完了後に入出力を SQLite へ保存する。

## 管理コマンドフロー
1. Discord integration が slash command を受信する。
2. `admin_command_service` が実行者権限を確認する。
3. `settings_repository` がサーバー設定を読み書きする。
4. 結果をエフェメラル応答で返す。

## 依存関係の向き
- `main` は全依存を組み立てる。
- `services` は抽象化された client / repository に依存する。
- `integrations` と `storage` は外界との接点を持つ。
- `domain` はできるだけ外部依存を持たない。

## サーバー設定モデル
- 既定値は環境変数からロードする。
- `guild_settings` に存在しないサーバーは既定値で動作する。
- 管理コマンド実行時に必要な設定だけ upsert する。
- 利用候補設定:
  - Bot 有効 / 無効
  - 許可チャンネル一覧
  - 利用モデル
  - システムプロンプト
  - 履歴件数
  - 応答文字数上限

## 応答表示の方針
- 最初に `Thinking... (Queue ahead: N)` のプレースホルダメッセージを返す。
- キューが進んだら既存メッセージを編集して `Queue ahead` を更新する。
- 推論完了後に最終応答でメッセージを置き換える。
- 最終応答だけ履歴保存対象とし、途中断片は保存しない。

## 初期実装で優先するもの
- mention 起点の 1 メッセージ 1 応答フロー
- Bot 返信への reply による会話継続
- Ollama prewarm
- SQLite による履歴保存とサーバー設定保存
- 推論直列化と presence 表示
- webhook 通知と graceful shutdown

## 後続候補
- レート制限
- 再試行ポリシー
- モデレーション強化
- 履歴要約
