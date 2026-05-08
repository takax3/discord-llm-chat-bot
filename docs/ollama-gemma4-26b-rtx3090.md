# Ollama Gemma 4 26B RTX 3090 Settings

このメモは、`RTX 3090 24GB` 上で `Gemma 4 26B` をルーター（`gemma3:1b`）付き構成で Discord bot 用途に安定運用するための設定例です。

## 対象

- GPU: `RTX 3090 24GB`
- 用途: Discord 上の日本語チャットボット
- 実行基盤: `Ollama + Docker Compose`
- メインモデル: `gemma4:26b`
- ルーターモデル: `gemma3:1b`

## VRAM の内訳（参考）

| 用途 | モデル | 概算 VRAM |
|---|---|---|
| メイン推論 | gemma4:26b Q4_K_M | 約 17〜18 GB |
| KV キャッシュ（context 8192 × parallel 1） | — | 約 1 GB |
| ルーター推論 | gemma3:1b Q4_K_M | 約 1.7 GB |
| 合計 | | 約 20〜21 GB / 24 GB |

`gemma4:e2b` は vision encoder を含むため実際に約 7 GB を消費し、26b と同時常駐できなかった。
`gemma3:1b` は純テキストモデル（約 1.7 GB）のため両モデルの同時常駐が可能。

## 推奨設定

`.env` / `.env.example` では次の値を基準にします。

```env
OLLAMA_MODEL=gemma4:26b
OLLAMA_ROUTER_MODEL=gemma3:1b
OLLAMA_KEEP_ALIVE=24h
OLLAMA_NUM_PARALLEL=1
OLLAMA_CONTEXT_LENGTH=8192
OLLAMA_FLASH_ATTENTION=1
OLLAMA_GPU_LAYERS=100
OLLAMA_TIMEOUT_SECONDS=180
```

## 設定意図

- `OLLAMA_ROUTER_MODEL=gemma3:1b`
  - 検索要否の判定専用モデルとして純テキストの軽量版を使います。
  - vision encoder を持たないため約 1.7 GB で収まり、26b と同時 VRAM 常駐が可能です。
  - `gemma4:e2b` は vision encoder を含み実測 ~7 GB になるため不適です。
- `OLLAMA_CONTEXT_LENGTH=8192`
  - 32768 から下げることで KV キャッシュを削減します。
  - reply チェーンを含む通常会話には 8K で十分なケースがほとんどです。
- `OLLAMA_NUM_PARALLEL=1`
  - bot 側で推論を直列化しているため、2 以上にしてもほぼ効果がありません。
  - 1 にすることで KV キャッシュの二重確保を避け、約 1〜2 GB 節約できます。
- `OLLAMA_FLASH_ATTENTION=1`
  - VRAM 効率と速度の改善を狙います。
- `OLLAMA_GPU_LAYERS=100`
  - 全レイヤーを GPU に寄せる前提です。
- `OLLAMA_KEEP_ALIVE=24h`
  - 両モデルを VRAM に保持し、ルーター初回ロード待ちを避けます。
- `OLLAMA_TIMEOUT_SECONDS=180`
  - 26B クラスの初回応答や重い質問に備えて長めにしています。

## コンテキスト長を戻したい場合

ルーターを使わない構成に戻す、または VRAM に余裕がある別の GPU に移す場合は、次の値を元に戻せます。

```env
# OLLAMA_ROUTER_MODEL は未設定 or OLLAMA_MODEL と同じ値にするとフォールバック
OLLAMA_NUM_PARALLEL=2
OLLAMA_CONTEXT_LENGTH=32768
```

## 運用メモ

- 初回起動時は `ollama-init` が `OLLAMA_MODEL`（26b）と `OLLAMA_ROUTER_MODEL`（gemma3:1b）を pull します。
- `docker compose exec ollama ollama ps` で両モデルが VRAM に乗っているか確認できます。
- VRAM が足りない場合は `OLLAMA_CONTEXT_LENGTH` を下げるか、`OLLAMA_GPU_LAYERS` を減らして CPU にオフロードします。

## 確認コマンド

```powershell
docker compose exec ollama ollama list
docker compose exec ollama ollama ps
docker compose exec ollama nvidia-smi
docker compose logs -f ollama-init
```
