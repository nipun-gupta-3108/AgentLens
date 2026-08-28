from langchain.agents import create_agent
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from tools import web_search, scrape_url
from dotenv import load_dotenv

load_dotenv()

# model setup
llm = ChatGoogleGenerativeAI(model="gemini-3.5-flash-lite")


# 1st agent
def build_search_agent():
    return create_agent(model=llm, tools=[web_search])


# 2nd agent


def build_reader_agent():
    return create_agent(model=llm, tools=[scrape_url])


# writer chain

writer_prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """
You are an expert research writer.

Write reports strictly from the research material provided by the user.

Rules:
- Use only information supported by the provided research.
- Do not rely on your pretrained knowledge to add factual claims.
- Do not invent statistics, dates, products, studies, organizations, or URLs.
- Do not present speculation as established fact.
- If the provided evidence is insufficient for a claim, explicitly state that evidence is insufficient.
- Every important factual claim should be traceable to one of the provided sources.
- Prefer precise, evidence-based language over exaggerated claims.
""",
        ),
        (
            "human",
            """
Write a detailed research report on the topic below.

Topic:
{topic}

Research Gathered:
{research}

Structure the report as:

1. Introduction
2. Key Findings
3. Critical Analysis / Limitations
4. Conclusion
5. Sources

For each important finding:
- Clearly explain the finding.
- Mention the supporting source number when possible, such as [Source 1].
- Do not create sources that are not present in the research.

Return only the research report.
""",
        ),
    ]
)

writer_chain = writer_prompt | llm | StrOutputParser()

# critic_chain

critic_prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """
You are a rigorous research evaluator.

Evaluate the report against the provided research sources.

Score these criteria from 0 to 10:

1. Accuracy
2. Source Quality
3. Citation Quality
4. Completeness
5. Critical Analysis
6. Clarity

Important rules:
- Check whether major claims are supported by the provided sources.
- Penalize unsupported or fabricated claims.
- Penalize invented statistics, dates, products, studies, or URLs.
- Penalize claims that are presented as facts when the sources only provide predictions or opinions.
- Do not assume a claim is true just because it sounds plausible.
""",
        ),
        (
            "human",
            """
Evaluate the following research report against the provided research material.

REPORT:
{report}

RESEARCH SOURCES:
{research}

Return your evaluation in exactly this format:

Accuracy: X/10
Source Quality: X/10
Citation Quality: X/10
Completeness: X/10
Critical Analysis: X/10
Clarity: X/10

Overall Score: X/10

Strengths:
- ...
- ...
- ...

Areas to Improve:
- ...
- ...
- ...

One line verdict:
...
""",
        ),
    ]
)

critic_chain = critic_prompt | llm | StrOutputParser()
