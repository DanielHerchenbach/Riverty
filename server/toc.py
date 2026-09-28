SYSTEM_PROMPT_TOC = r"""
Your task is to extract the structure from a legal text or contract and build a tree.
Unlike a simple TOC, this tree must contain a node for EVERY structuring element such as heading, chapter, section, §, number, clause, bullet point etc.

For example, the following input:
Immigration Act
24 Illegal entry.
(B1) A person who—
(a) requires leave to enter the United Kingdom under this Act, and
(b) knowingly enters the United Kingdom without such leave, commits an offence.

yields this output:
Immigration Act
  24 Illegal entry.
    (B1)
      A person who—
      (a)
        requires leave to enter the United Kingdom under this Act, and
      (b)
        knowingly enters the United Kingdom without such leave,
      commits an offence.
 
For each level of indentation, the output uses exactly two spaces.
IMPORTANT: All extracted text must be taken VERBATIM from the input.
Omit any text which clearly is not part of the legal text, such as footers, headers or page numbers.

IMPORTANT: DO NOT PUT STRUCTURING ELEMENTS WITH THE ACTUAL CONTENT IN THE SAME LINE!
WRONG:
  1) Legal text...
  2) Legal text...
CORRECT:
  1)
    Legal text...
  2)
    Legal text...

However, text merely being a label for a structuring element, must be put on the same line,
for example the following is CORRECT:
  Chapter 1 Introduction
    Legal text...
  Chapter 2 Scope
    Legal text...  
"""

# USAGE:
#
#load_dotenv(Path(__file__).resolve().with_name(".env"))
#KEY = os.environ['OPENAI_API_KEY']
#
# client = AsyncOpenAI(
#     api_key=KEY,
#     max_retries=0,
#     timeout=60,
# )
# response = await client.chat.completions.create(
#     model="gpt-6-sol",
#     reasoning_effort="medium",
#     temperature=1,
#     messages=[
#         {
#             "role": "system",
#             "content": SYSTEM_PROMPT_TOC_SIMPLE,
#         },
#         {"role": "user", "content": layout_result.replace('\n', ' ')},
#     ],
# )
# print(response.choices[0].message.content)