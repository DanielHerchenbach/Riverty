"""Print Azure Document Intelligence's visual reading order."""

from pathlib import Path

from azure.ai.documentintelligence import DocumentIntelligenceClient
from azure.ai.documentintelligence.models import AnalyzeDocumentRequest, AnalyzeResult
from azure.core.credentials import AzureKeyCredential


ENDPOINT = "https://extracttoc.cognitiveservices.azure.com/"
KEY = "Bnb39addOQ2pUlrOehrSjURlxqgnxz84z1vytr30BEKtiZ4oILruJQQJ99CIACPV0roXJ3w3AAALACOGJeuh"
PDF_PATH = Path("test.pdf")
# Start with four pages for a small, repeatable layout/OCR test.
# Set to None when the endpoint permits analyzing the complete document.
PAGES = "1-4"

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


def analyze_layout() -> None:
    client = DocumentIntelligenceClient(ENDPOINT, AzureKeyCredential(KEY))
    print(f"Analyzing {PDF_PATH} ({PDF_PATH.stat().st_size / 1024:.1f} KiB), pages={PAGES or 'all'}")
    with PDF_PATH.open("rb") as document:
        poller = client.begin_analyze_document(
            "prebuilt-layout",
            AnalyzeDocumentRequest(bytes_source=document.read()),
            pages=PAGES,
        )
    result: AnalyzeResult = poller.result()

    #print(f"SOURCE: {PDF_PATH}")
    #print("READING ORDER: Azure page.lines order; column is inferred from x position")
    #print("=" * 100)
    for page in result.pages:
        midpoint = (page.width or 1) / 2
        #print(f"\n--- PAGE {page.page_number} ({page.width} x {page.height} {page.unit}) ---")
        for index, line in enumerate(page.lines or [], start=1):
            role = _line_role(result, page.page_number, line)
            # Azure returns enum values such as ParagraphRole.PAGE_NUMBER,
            # ParagraphRole.SECTION_HEADING, and ParagraphRole.TITLE.
            role_name = getattr(role, "value", role)
            role_name = str(role_name).rsplit(".", 1)[-1].replace("_", "").casefold()
            if role_name in {"pagenumber", "pageheader", "pagefooter"}:#, "sectionheading", "title"
                continue
            marker = f" [{role}]" if role else ""
            #print(f"{page.page_number:02d}.{index:03d} {column} x={left:7.1f} y={top:7.1f} {line.content}{marker}")
            #print(f"{page.page_number:02d}.{index:03d} {line.content}{marker}")
            print(line.content)

    print("\n" + "=" * 100)
    print("Expected for normal two-column flow: left-column lines finish before right-column lines start.")
    print("Heading roles appear as [title] or [sectionHeading].")


if __name__ == "__main__":
    analyze_layout()
