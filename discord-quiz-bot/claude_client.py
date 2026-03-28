import os
import anthropic

_client: anthropic.Anthropic | None = None

SONNET = "claude-sonnet-4-6"
HAIKU  = "claude-haiku-4-5-20251001"

# 모델 용도 분리
# SONNET : 퀴즈 생성, 채점, Q&A 답변 (정확도 중요)
# HAIKU  : slug 생성, 요약 (단순 작업, 비용 절감)


def get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        _client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    return _client


def call_claude(prompt: str, model: str = SONNET, max_tokens: int = 2048) -> str:
    msg = get_client().messages.create(
        model=model,
        max_tokens=max_tokens,
        messages=[{"role": "user", "content": prompt}],
    )
    return msg.content[0].text.strip()
