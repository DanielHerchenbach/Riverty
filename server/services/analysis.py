from pathlib import Path

from openai import AsyncOpenAI

from server.layout import analyze_layout
from server.toc import KEY as OPENAI_KEY
from server.toc import SYSTEM_PROMPT_TOC_SIMPLE


async def analyze_to_toc(pdf_path: Path) -> str:
    _, document_text = await analyze_layout(pdf_path=pdf_path)

    async with AsyncOpenAI(api_key=OPENAI_KEY, max_retries=0, timeout=600) as client:
        response = await client.chat.completions.create(
            model="gpt-6-sol",
            reasoning_effort="medium",
            temperature=1,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT_TOC_SIMPLE},
                {"role": "user", "content": document_text.replace("\n", " ")},
            ],
        )

    toc = response.choices[0].message.content
    if toc is None:
        raise RuntimeError("The model returned no table of contents")
    return toc
