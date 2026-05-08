# Claude Code Project Context

## ドキュメント構成

| ファイル | 内容 |
|---|---|
| `README.md` | 機能概要・Docker 起動手順・未実装リスト |
| `SPECIFICATION.md` | 仕様の正本。実装判断はここを基準にする |
| `docs/architecture.md` | モジュール構成・処理フロー・設計方針 |
| `docs/development-log.md` | 試した実装の経緯・現行仕様まとめ・設定チューニング例 |

## 開発コマンド

```bash
# テスト実行
pytest tests/

# コード整形（変更前に実行）
black src/ tests/

# Lint チェック
flake8 src/ tests/
```

Python 3.14 / Poetry 管理。依存追加は `pyproject.toml` に記載。

## 実装済み / 未実装

実装済みの機能は `README.md` の「機能」セクションを参照。

**未実装（`README.md` 「未実装」セクションより）:**
- 管理者向け slash command によるサーバー設定変更
- ストリーミング表示・応答分割送信
- レート制限・再試行ポリシー
- 履歴要約

## コーディング規約

- コメントは「なぜ」が自明でないときだけ書く。「何をしているか」はコード自体に語らせる。
- 関数の docstring は 1 行の契約説明のみ（不要なら省略）。
- 現タスクに不要な抽象化・エラーハンドリング・将来対応は加えない。
- テストが壊れたら原因を特定してから修正する（テストを黙らせない）。

## 重要な設計判断

- **検索要否の判定はメインモデル推奨**（`decide_combined`、1 回呼び出し）。`OLLAMA_ROUTER_MODEL` に別モデルを指定するルーターあり構成も動くが、1B モデルは精度不安定で非推奨。詳細は `docs/development-log.md` を参照。
- **ルーターあり構成の判定フロー**: classify_genre → summarize_query → is_explicit → needs_fresh → generate_query（5ステップ）。各ステップは `on_pending` / `on_result` コールバックで Discord にリアルタイム表示される。
- **推論は必ず直列化**（`inference_queue`）。同時リクエストは順番待ち。
- `ollama_router_model` は未指定またはメインモデルと同じ場合、メインモデルが判定も行う（`config.py` の `load_config` 参照）。

## テスト方針

- 外部依存（Discord / Ollama / Brave Search / SQLite）はモックで置き換える。
- `tests/` 配下のテスト名は `test_<対象モジュール名>.py` 形式。
- 新機能追加時は対応するユニットテストも追加する。
