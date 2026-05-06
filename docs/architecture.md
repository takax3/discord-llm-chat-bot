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
2. mention が含まれていない通常メッセージは無視する。
3. `moderation_service` がサーバー設定と利用制限を確認する。
4. `context_builder` が SQLite 履歴を集めて LLM 入力へ整形する。
5. `chat_service` がプレースホルダ返信を作成する。
6. `ollama_client` が Qwen モデルへ問い合わせる。
7. `streaming_service` が段階的に返信メッセージを更新する。
8. 完了後に入出力を SQLite へ保存する。

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

## 段階表示の方針
- 最初に「考え中」または空のプレースホルダメッセージを返す。
- 一定間隔または一定文字数ごとに既存メッセージを編集する。
- Discord の編集頻度制限を避けるため、更新間隔に下限を持たせる。
- 最終応答だけ履歴保存対象とし、途中断片は保存しない。

## 初期実装で優先するもの
- mention 起点の 1 メッセージ 1 応答フロー
- Ollama 接続確認
- SQLite による履歴保存とサーバー設定保存
- 段階表示とエラーハンドリング
- slash command による管理操作
- 基本ログ

## 後続候補
- レート制限
- 再試行ポリシー
- モデレーション強化
- 履歴要約
