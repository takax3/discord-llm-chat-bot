# Ollama Gemma 4 26B RTX 3090 Settings

このメモは、`RTX 3090 24GB` 上で `Gemma 4 26B` を Discord bot 用途で安定運用するための設定例です。

## 対象

- GPU: `RTX 3090 24GB`
- 用途: Discord 上の日本語チャットボット
- 実行基盤: `Ollama + Docker Compose`
- 想定モデル: `gemma4:26b`

## Compose 側の推奨設定

`.env` / `.env.example` では次の値を基準にします。

```env
OLLAMA_MODEL=gemma4:26b
OLLAMA_KEEP_ALIVE=24h
OLLAMA_NUM_PARALLEL=2
OLLAMA_CONTEXT_LENGTH=32768
OLLAMA_FLASH_ATTENTION=1
OLLAMA_GPU_LAYERS=100
OLLAMA_TIMEOUT_SECONDS=180
```

## 設定意図

- `OLLAMA_CONTEXT_LENGTH=32768`
  - 32K コンテキストで、reply チェーンを使う会話でも余裕を持たせます。
- `OLLAMA_FLASH_ATTENTION=1`
  - VRAM 効率と速度の改善を狙います。
- `OLLAMA_GPU_LAYERS=100`
  - 全レイヤーを GPU に寄せる前提です。
- `OLLAMA_NUM_PARALLEL=2`
  - Ollama 自体の並列設定です。
  - この bot はアプリ側で推論を直列化しているため、大きく上げる必要はありません。
- `OLLAMA_KEEP_ALIVE=24h`
  - モデルを VRAM に保持しやすくし、再ロード待ちを減らします。
- `OLLAMA_TIMEOUT_SECONDS=180`
  - 26B クラスの初回応答や重い質問に備えて長めにしています。

## モデル設定の考え方

量子化設定は `docker-compose.yml` ではなく `Modelfile` 側で管理します。

Gemma 4 26B を RTX 3090 で使うなら、まずは次のような方針が現実的です。

- 量子化: `Q4_K_M` 相当を優先候補にする
- コンテキスト: まずは `32K` 運用から始める
- 多並列: 速度より安定性優先で低めに保つ

## 運用メモ

- モデル切り替え後は `ollama-init` が正しい `OLLAMA_MODEL` を pull しているか確認します。
- 起動後は `docker compose exec ollama ollama ps` で GPU 利用状況を確認します。
- 応答速度が厳しい場合は、次の順で見直すのがおすすめです。
  1. `OLLAMA_CONTEXT_LENGTH` を下げる
  2. `OLLAMA_NUM_PARALLEL` を下げる
  3. より軽い量子化や小さいモデルを検討する

## 確認コマンド

```powershell
docker compose exec ollama ollama list
docker compose exec ollama ollama ps
docker compose exec ollama nvidia-smi
docker compose logs -f ollama-init
```
