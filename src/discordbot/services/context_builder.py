from __future__ import annotations

from discordbot.domain.conversation_message import ConversationMessage


class ContextBuilder:
    def __init__(self, *, system_prompt: str, max_response_chars: int) -> None:
        self._system_prompt = system_prompt
        self._max_response_chars = max_response_chars

    def build_messages(
        self,
        *,
        prior_messages: list[ConversationMessage],
        user_message: str,
    ) -> list[dict[str, str]]:
        messages: list[dict[str, str]] = [
            {
                "role": "system",
                "content": self._build_system_prompt(),
            },
        ]
        for message in prior_messages:
            messages.append(
                {
                    "role": message.role,
                    "content": message.content,
                }
            )
        messages.append({"role": "user", "content": user_message})
        return messages

    def _build_system_prompt(self) -> str:
        response_style_instruction = (
            "If you do not know something, say clearly that you do not know instead of guessing. "
            "Do not invent facts that are not supported by the conversation context. "
            "If you are uncertain, say that it is a guess or needs confirmation. "
            "For medical, legal, financial, security, or privacy-sensitive topics, avoid definitive claims and present general information with appropriate caution. "
            "Reply concisely unless the user explicitly asks for a detailed explanation. "
            "Reply in Japanese unless the user explicitly asks for another language."
        )
        response_limit_instruction = (
            f"Keep your final response within {self._max_response_chars} characters."
        )
        return (
            f"{self._system_prompt}\n\n"
            f"{response_style_instruction}\n"
            f"{response_limit_instruction}"
        )
