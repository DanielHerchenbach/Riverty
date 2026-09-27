"""Return Azure Document Intelligence's visual reading order."""

import asyncio
from pathlib import Path

from azure.ai.documentintelligence.aio import DocumentIntelligenceClient
from azure.ai.documentintelligence.models import AnalyzeDocumentRequest, AnalyzeResult
from azure.core.credentials import AzureKeyCredential


ENDPOINT = "https://extracttoc.cognitiveservices.azure.com/"
KEY = "Bnb39addOQ2pUlrOehrSjURlxqgnxz84z1vytr30BEKtiZ4oILruJQQJ99CIACPV0roXJ3w3AAALACOGJeuh"
PDF_PATH = Path("test.pdf")
PAGES = "1-2" # Set to None to analyze the complete document.

def _line_role(result: AnalyzeResult, page_number: int, line) -> str:
    line_start = line.spans[0].offset if line.spans else None
    line_end = line_start + line.spans[0].length if line.spans else None
    if line_start is None or not result.paragraphs:
        return ""
    for paragraph in result.paragraphs:
        if not paragraph.spans:
            continue
        start = paragraph.spans[0].offset
        end = start + paragraph.spans[0].length
        if line_start < end and line_end > start:
            if any(region.page_number == page_number for region in paragraph.bounding_regions or []):
                return getattr(paragraph, "role", "") or ""
    return ""


async def analyze_layout(pages: str | None = PAGES) -> tuple[str, str]:
    async with DocumentIntelligenceClient(ENDPOINT, AzureKeyCredential(KEY)) as client:
        with PDF_PATH.open("rb") as document:
            poller = await client.begin_analyze_document(
                "prebuilt-layout",
                AnalyzeDocumentRequest(bytes_source=document.read()),
                pages=pages,
            )
        result: AnalyzeResult = await poller.result()

    verbose_lines: list[str] = []
    cleaned_lines: list[str] = []
    for page in result.pages:
        for index, line in enumerate(page.lines or [], start=1):
            role = _line_role(result, page.page_number, line)
            role_name = getattr(role, "value", role)
            role_name = str(role_name).rsplit(".", 1)[-1].replace("_", "").casefold()
            marker = f" [{role}]" if role else ""
            verbose_lines.append(
                f"{page.page_number:02d}.{index:03d} {line.content}{marker}"
            )
            if role_name not in {"pagenumber", "pageheader", "pagefooter"}:
                cleaned_lines.append(line.content)

    return "\n".join(verbose_lines), "\n".join(cleaned_lines)


if __name__ == "__main__":
    a = asyncio.run(analyze_layout())
    print(a[0])
    print("################################################################")
    print(a[1])
