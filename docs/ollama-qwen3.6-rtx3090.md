# Ollama Qwen3.6 RTX 3090 Settings

このメモは、`RTX 3090 24GB` 上で `Qwen3.6` を Discord bot 用途で安定運用するための設定例です。

## 対象

- GPU: `RTX 3090 24GB`
- 用途: Discord 上の日本語チャットボット
- 実行基盤: `Ollama + Docker Compose`
- 推奨モデル: `qwen3.6:27b`

## 推奨モデルの考え方

Ollama の公開ライブラリでは、2026-05-07 時点で次の系統が確認できます。

- `qwen3.6:27b`
  - `27.8B`
  - `Q4_K_M`
  - 約 `17GB`
- `qwen3.6` / `qwen3.6:latest`
  - `36B`
  - `Q4_K_M`
  - 約 `24GB`

RTX 3090 では `qwen3.6:latest` も理論上は載りますが、VRAM 余裕がかなり小さいため、チャットボット用途ではまず `qwen3.6:27b` を基準にするのが安全です。

## Compose 側の推奨設定

`.env` / `.env.example` の設定例です。

```env
OLLAMA_MODEL=qwen3.6:27b
OLLAMA_KEEP_ALIVE=24h
OLLAMA_NUM_PARALLEL=2
OLLAMA_CONTEXT_LENGTH=32768
OLLAMA_FLASH_ATTENTION=1
OLLAMA_GPU_LAYERS=100
OLLAMA_PREWARM_ENABLED=true
OLLAMA_PREWARM_PROMPT=こんにちは。準備ができたら一言だけ返答してください。
OLLAMA_TIMEOUT_SECONDS=180
```

## 設定意図

- `OLLAMA_MODEL=qwen3.6:27b`
  - RTX 3090 で速度と安定性のバランスを取りやすいです。
- `OLLAMA_CONTEXT_LENGTH=32768`
  - reply チェーンを含む会話でも扱いやすい、現実的な上限です。
- `OLLAMA_FLASH_ATTENTION=1`
  - 速度と VRAM 効率の改善を狙います。
- `OLLAMA_GPU_LAYERS=100`
  - 全レイヤーを GPU に寄せる前提です。
- `OLLAMA_NUM_PARALLEL=2`
  - bot 側で推論要求を直列化しているため、高くしすぎる必要はありません。
- `OLLAMA_KEEP_ALIVE=24h`
  - モデル再ロードを減らし、体感速度を安定させます。
- `OLLAMA_PREWARM_ENABLED=true`
  - 起動直後の初回応答待ちを避けやすくします。
- `OLLAMA_TIMEOUT_SECONDS=180`
  - 初回ロードや重めの応答を見込んだ余裕値です。

## より軽くしたい場合

応答が重い場合は、次の順で見直すのがおすすめです。

1. `OLLAMA_CONTEXT_LENGTH` を `16384` に下げる
2. `OLLAMA_TIMEOUT_SECONDS` は維持したまま、応答速度を観測する
3. それでも厳しければ、より小さい Qwen 系タグを検討する

## より大きい `qwen3.6:latest` を試す場合

`qwen3.6:latest` は Ollama 上で約 `24GB` と案内されており、RTX 3090 ではかなりタイトです。試すなら次のような注意が必要です。

- 他の GPU 利用プロセスをできるだけ減らす
- `OLLAMA_CONTEXT_LENGTH` はまず `16384` から始める
- 初回ロード時間が長くなりやすいので prewarm を有効にしておく

設定例:

```env
OLLAMA_MODEL=qwen3.6
OLLAMA_KEEP_ALIVE=24h
OLLAMA_NUM_PARALLEL=1
OLLAMA_CONTEXT_LENGTH=16384
OLLAMA_FLASH_ATTENTION=1
OLLAMA_GPU_LAYERS=100
OLLAMA_PREWARM_ENABLED=true
OLLAMA_TIMEOUT_SECONDS=240
```

## モデル設定の考え方

量子化設定は `docker-compose.yml` ではなく、モデルタグまたは `Modelfile` 側で管理します。

今回の前提では、`qwen3.6:27b` も `qwen3.6:latest` も Ollama 側の公開モデル実体として `Q4_K_M` が使われます。別の量子化を使いたい場合は、専用タグまたは独自 `Modelfile` を使う想定です。

## 確認コマンド

```powershell
docker compose exec ollama ollama list
docker compose exec ollama ollama show qwen3.6:27b
docker compose exec ollama ollama ps
docker compose exec ollama nvidia-smi
docker compose logs -f ollama-init
```
