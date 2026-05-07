"""アプリ全体で使う既定値と固定値。

`.env` / `.env.example` の並びと対応づけしやすいように、
関心ごとごとにグループ化している。
"""

# アプリ名と基本ログ設定。
APP_NAME = "discordbot"
DEFAULT_LOG_LEVEL = "INFO"

# Discord の基本応答設定。
DEFAULT_MENTION_RESPONSE = "Hello! Discord bot is connected and ready."
DEFAULT_OLLAMA_ERROR_RESPONSE = "Sorry, I couldn't get a response from Ollama right now."
DEFAULT_MAX_RESPONSE_CHARS = 1800

# サーバー単位設定の既定値。
DEFAULT_GUILD_ENABLED = True

# Ollama 起動時の挙動。
DEFAULT_OLLAMA_PREWARM_ENABLED = True
DEFAULT_OLLAMA_PREWARM_PROMPT = "こんにちは。準備ができたら一言だけ返答してください。"

# 画像入力まわりの既定値。
DEFAULT_VISION_ENABLED = True
DEFAULT_VISION_IMAGE_ONLY_PROMPT = "この画像に写っているものを推定して、簡潔に説明してください。"
DEFAULT_VISION_MAX_PIXELS = 2073600

# Web 検索補強の既定値。
DEFAULT_WEB_SEARCH_ENABLED = False
DEFAULT_WEB_SEARCH_MAX_RESULTS = 3
DEFAULT_WEB_SEARCH_TIMEOUT_SECONDS = 10
DEFAULT_WEB_SEARCH_COUNTRY = "JP"
DEFAULT_WEB_SEARCH_LANGUAGE = "jp"

# Discord webhook 通知の既定値。
DEFAULT_WEBHOOK_NOTIFY_STARTUP = True
DEFAULT_WEBHOOK_NOTIFY_SHUTDOWN = True
DEFAULT_WEBHOOK_NOTIFY_LOGS = False
DEFAULT_WEBHOOK_MIN_LEVEL_NAME = "ERROR"
WEBHOOK_TIMEOUT_SECONDS = 10
