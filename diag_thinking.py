import asyncio
import openai
from core import config

client = openai.OpenAI(
    api_key=config.DEEPSEEK_API_KEY,
    base_url=config.DEEPSEEK_BASE_URL,
    timeout=60,
)

async def test(label, extra_kwargs):
    print(f"\n=== 测试: {label} ===")
    try:
        resp = await asyncio.to_thread(
            client.chat.completions.create,
            model=config.MODEL_NAME,
            messages=[{"role": "user", "content": "用一句话解释什么是动态规划。"}],
            temperature=0.3,
            max_tokens=500,
            **extra_kwargs,
        )
        choice = resp.choices[0]
        rc = getattr(choice.message, "reasoning_content", None)
        print(f"  finish_reason: {choice.finish_reason}")
        print(f"  content: {(choice.message.content or '')[:200]}")
        print(f"  reasoning_len: {len(rc) if rc else 0}")
    except Exception as e:
        print(f"  失败: {type(e).__name__}: {e}")

async def main():
    await test("基线（无额外参数）", {})
    await test("thinking=disabled", {"extra_body": {"thinking": {"type": "disabled"}}})
    await test("reasoning_effort=low", {"extra_body": {"reasoning_effort": "low"}})
    await test("enable_thinking=False", {"extra_body": {"enable_thinking": False}})

asyncio.run(main())