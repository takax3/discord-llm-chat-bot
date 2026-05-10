# Ollama Gemma 4 26B RTX 3090 Settings

このメモは、`RTX 3090 24GB` 上で `Gemma 4 26B` をシングルモデル構成で Discord bot 用途に安定運用するための設定例です。

## 対象

- GPU: `RTX 3090 24GB`
- 用途: Discord 上の日本語チャットボット
- 実行基盤: `Ollama（ホスト）+ Docker Compose（Bot のみ）`
- モデル: `gemma4:26b`

## VRAM の内訳（参考）

起動時の実測値（`OLLAMA_CONTEXT_LENGTH=8192, OLLAMA_NUM_PARALLEL=1`）：

| 用途 | 概算 VRAM |
|---|---|
| gemma4:26b Q4_K_M（重み） | 約 16.6 GB（CUDA0）+ 0.7 GB（CPU） |
| KV キャッシュ | 約 1.0 GB |
| compute graph | 約 0.3 GB |
| 合計（GPU） | 約 18.6 GB / 24 GB |

空き VRAM は約 5 GB あるため、必要なら `OLLAMA_CONTEXT_LENGTH` を 16384 程度まで引き上げる余地があります。

## 推奨設定

### Ollama ホスト側（OS 環境変数として設定）

```env
OLLAMA_KEEP_ALIVE=24h
OLLAMA_NUM_PARALLEL=1
OLLAMA_CONTEXT_LENGTH=8192
OLLAMA_FLASH_ATTENTION=1
OLLAMA_GPU_LAYERS=100
```

### Bot の `.env`

```env
OLLAMA_MODEL=gemma4:26b
OLLAMA_TIMEOUT_SECONDS=180
```

## 設定意図

- `OLLAMA_CONTEXT_LENGTH=8192`
  - 32768 から下げることで KV キャッシュを削減します（8K → 1 GB、32K → ~4 GB）。
  - reply チェーンを含む通常会話には 8K で十分なケースがほとんどです。
  - VRAM に余裕があるため 16384 まで引き上げも可能です。
- `OLLAMA_NUM_PARALLEL=1`
  - bot 側で推論を直列化しているため、2 以上にしてもほぼ効果がありません。
  - 1 にすることで KV キャッシュの二重確保を避け、VRAM を節約できます。
- `OLLAMA_FLASH_ATTENTION=1`
  - VRAM 効率と速度の改善を狙います。
- `OLLAMA_GPU_LAYERS=100`
  - 全レイヤーを GPU に寄せる前提です。
- `OLLAMA_KEEP_ALIVE=24h`
  - モデルを VRAM に保持し、リロード待ちを避けます。
- `OLLAMA_TIMEOUT_SECONDS=180`
  - 26B クラスの初回応答や重い質問に備えて長めにしています。

## 注意事項

- **サーマルスロットリング**: 連続推論が 20 分を超えると GPU 温度が上昇し、~105 tok/s から ~58 tok/s 程度まで落ちる場合があります。RTX 3090 の熱設計上の問題です。ケースのエアフローを確保してください。
- `gemma4:e2b` は vision encoder を含むため実際に約 7 GB を消費し、26b との同時常駐ができません。

## 運用メモ

- 初回起動前に `ollama pull gemma4:26b` でモデルを取得しておきます。
- `ollama ps` でモデルが VRAM に乗っているか確認できます。
- VRAM が足りない場合は `OLLAMA_CONTEXT_LENGTH` を下げるか、`OLLAMA_GPU_LAYERS` を減らして CPU にオフロードします。

## 確認コマンド

```powershell
ollama list
ollama ps
nvidia-smi
```
