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
  webhook_logging.py
  domain/
    guild_settings.py
    conversation_message.py
    search_decision.py
    search_result.py
  integrations/
    discord_client.py
    ollama_client.py
    brave_search_client.py
  services/
    chat_service.py
    context_builder.py
    inference_queue.py
    presence_service.py
    image_preprocessor.py
    search_decision_service.py
  storage/
    database.py
    conversation_repository.py
    settings_repository.py
```

## リクエスト処理フロー
1. Discord integration がメッセージイベントを受信する。
2. mention もしくは Bot 返信への reply でない通常メッセージは無視する。
3. `settings_repository` がサーバー設定と利用制限を確認する。
4. `conversation_repository` と `context_builder` が SQLite 履歴を集めて LLM 入力へ整形する。
5. `chat_service` が待機メッセージ `Waiting... (Queue ahead: N)` を先に返す。
6. `inference_queue` が推論を直列化し、キュー待ち件数を管理する。
7. （Stage 1 / `WEB_SEARCH_ENABLED=true` のとき）検索要否を判定する。
   - ルーターなし（推奨）: `ollama_client` が `decide_combined()` で判定とクエリ生成を 1 回で実施。
   - ルーターあり: `search_decision_service` が最大 5 ステップで判定し、各ステップを Discord にリアルタイム表示。
   - 検索する場合は `brave_search_client` が検索を実行し、結果を Stage 2 コンテキストに追加する。
8. （Stage 2）`ollama_client` が利用モデルへ最終回答を問い合わせる。
9. `presence_service` がキュー数と直近のトークンスピードをもとにステータス文言を組み立てる。
10. 完了後に入出力を SQLite へ保存する。

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
- 最初に `Waiting... (Queue ahead: N)` のプレースホルダメッセージを返す。
- キューが進んだら既存メッセージを編集して `Queue ahead` を更新する。
- ルーターモデルを使う場合、各ステップの進捗を Discord にリアルタイム表示する（`OLLAMA_ROUTER_SHOW_STEPS` により累積 or 現在ステップのみ表示を切り替え）。
- 検索を実行した場合、完了後に `検索完了` を表示に残す。
- 推論完了後に最終応答でメッセージを置き換える。ルーター進捗が残っている場合は先頭に付加する。
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
