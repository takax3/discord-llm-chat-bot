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

## 推奨設定（ルーターモデルあり構成）

ルーター（`OLLAMA_ROUTER_MODEL`）を併用する場合は、KV キャッシュを抑えて VRAM に余裕を持たせます。

```env
OLLAMA_MODEL=qwen3.6:27b
OLLAMA_ROUTER_MODEL=qwen3.5:2b
OLLAMA_KEEP_ALIVE=24h
OLLAMA_NUM_PARALLEL=1
OLLAMA_CONTEXT_LENGTH=8192
OLLAMA_FLASH_ATTENTION=1
OLLAMA_GPU_LAYERS=100
OLLAMA_PREWARM_ENABLED=true
OLLAMA_PREWARM_PROMPT=こんにちは。準備ができたら一言だけ返答してください。
OLLAMA_TIMEOUT_SECONDS=180
```

### VRAM の内訳（参考）

| 用途 | 概算 VRAM |
|---|---|
| qwen3.6:27b Q4_K_M | 約 17 GB |
| KV キャッシュ（context 8192 × parallel 1） | 約 0.5 GB |
| ルーター qwen3.5:2b | 約 2.7 GB |
| 合計 | 約 20〜21 GB / 24 GB |

Gemma 4 26B 構成より余裕が大きく、`OLLAMA_CONTEXT_LENGTH=16384` まで上げる余地もあります。

## 設定意図

- `OLLAMA_ROUTER_MODEL=qwen3.5:2b`
  - 検索要否の判定専用モデルです。同じ Qwen ファミリーで揃えることで、ルーティングプロンプトへの追従が安定しやすくなります。未設定時は `OLLAMA_MODEL` にフォールバックします。
- `OLLAMA_CONTEXT_LENGTH=8192`
  - ルーターモデルの常駐 VRAM を確保しつつ、通常会話には十分な長さです。
- `OLLAMA_NUM_PARALLEL=1`
  - bot 側で推論を直列化しているため、高くする必要はありません。
- `OLLAMA_FLASH_ATTENTION=1`
  - 速度と VRAM 効率の改善を狙います。
- `OLLAMA_GPU_LAYERS=100`
  - 全レイヤーを GPU に寄せる前提です。
- `OLLAMA_KEEP_ALIVE=24h`
  - モデル再ロードを減らし、体感速度を安定させます。
- `OLLAMA_PREWARM_ENABLED=true`
  - 起動直後の初回応答待ちを避けやすくします。
- `OLLAMA_TIMEOUT_SECONDS=180`
  - 初回ロードや重めの応答を見込んだ余裕値です。

## ルーターなし・シングルモデル構成

ルーターを使わずメインモデルのみで動かす場合は、コンテキストを広く取れます。

```env
OLLAMA_MODEL=qwen3.6:27b
# OLLAMA_ROUTER_MODEL は未設定（OLLAMA_MODEL にフォールバック）
OLLAMA_NUM_PARALLEL=2
OLLAMA_CONTEXT_LENGTH=32768
OLLAMA_FLASH_ATTENTION=1
OLLAMA_GPU_LAYERS=100
OLLAMA_PREWARM_ENABLED=true
OLLAMA_TIMEOUT_SECONDS=180
```

## より大きい `qwen3.6:latest` を試す場合

`qwen3.6:latest` は約 `24GB` と案内されており、RTX 3090 ではかなりタイトです。ルーターとの同時常駐は困難なため、シングルモデル構成か CPU オフロードを検討してください。

```env
OLLAMA_MODEL=qwen3.6
OLLAMA_KEEP_ALIVE=24h
OLLAMA_NUM_PARALLEL=1
OLLAMA_CONTEXT_LENGTH=8192
OLLAMA_FLASH_ATTENTION=1
OLLAMA_GPU_LAYERS=100
OLLAMA_PREWARM_ENABLED=true
OLLAMA_TIMEOUT_SECONDS=240
```

## モデル設定の考え方

量子化設定は `docker-compose.yml` ではなく、モデルタグまたは `Modelfile` 側で管理します。`qwen3.6:27b` も `qwen3.6:latest` も Ollama 側の公開モデル実体として `Q4_K_M` が使われます。別の量子化を使いたい場合は、専用タグまたは独自 `Modelfile` を使う想定です。

## 確認コマンド

```powershell
docker compose exec ollama ollama list
docker compose exec ollama ollama show qwen3.6:27b
docker compose exec ollama ollama ps
docker compose exec ollama nvidia-smi
docker compose logs -f ollama-init
```
