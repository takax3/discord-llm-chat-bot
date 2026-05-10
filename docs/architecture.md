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
    inference_log.py
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
    gpu_power_sampler.py
  storage/
    database.py
    conversation_repository.py
    settings_repository.py
    inference_log_repository.py
```

## リクエスト処理フロー
1. Discord integration がメッセージイベントを受信する。
2. mention もしくは Bot 返信への reply でない通常メッセージは無視する。
3. `settings_repository` がサーバー設定と利用制限を確認する。
4. `conversation_repository` と `context_builder` が SQLite 履歴を集めて LLM 入力へ整形する。
5. `chat_service` が待機メッセージ `Waiting... (Queue ahead: N)` を先に返す。
6. `inference_queue` が推論を直列化し、キュー待ち件数を管理する。
7. （Stage 1 / `WEB_SEARCH_ENABLED=true` のとき）検索要否を判定する。
   - `search_decision_service.decide()` がメインモデルへ 1 回の JSON 呼び出しで判定とクエリ生成を実施（「判定中…」を表示）。
   - 複数クエリが返された場合は `brave_search_client` を並列実行し、結果を Stage 2 コンテキストに追加する。
8. （Stage 2）`ollama_client` が利用モデルへ最終回答を問い合わせる。
9. `presence_service` がキュー数と直近のトークンスピードをもとにステータス文言を組み立てる。
10. 完了後に入出力を SQLite へ保存する。
11. `inference_log_repository` が推論ログ（タイムスタンプ 8 点・トークン数・検索クエリ数・エラーフラグ・GPU 消費電力/エネルギー）を `inference_logs` テーブルへ保存する。

## スラッシュコマンドフロー

`discord_client.py` が `app_commands.CommandTree` を保持し、`setup_hook()` で `tree.sync()` を呼んでグローバル登録する。コマンド定義は `_register_slash_commands()` にまとめる。

### `/stats`
1. Discord integration が slash command を受信する。
2. `inference_log_repository.fetch_last_by_channel(channel_id)` で当該チャンネルの最新ログを 1 件取得する。
3. ログが存在しない場合は「このチャンネルにはまだ推論ログがありません。」を `ephemeral=True` で返す。
4. ログが存在する場合、`_elapsed_seconds(start, end)` ヘルパーで所要時間を計算し、Stage 1・検索クエリ数・Stage 2 の統計を `ephemeral=True` で返す。

## 管理コマンドフロー（未実装）
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
- 検索要否判定中は `判定中…` を表示し、Stage 1 と Stage 2 の 2 段構成をユーザーに伝える。
- `SHOW_STEPS=false`（既定）: 推論が完了したら最終応答のみを表示する。途中ステップは都度置き換えられる。
- `SHOW_STEPS=true`: ステップを積み重ねて表示する。
  - 判定後: 検索不要なら `検索不要`、検索ありなら `検索クエリ: q1, q2` をステップに追加する。
  - 検索中は `検索中…` を表示（クエリはステップ表示済み）。検索完了後は `検索完了` をステップに追加する。
  - 推論中は `推論中…` を表示し、完了後は `推論完了` をステップに追加する。
  - 最終応答はステップ一覧の後に続けて表示される。
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
