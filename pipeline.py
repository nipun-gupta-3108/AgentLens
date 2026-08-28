from agents import build_search_agent, writer_chain, critic_chain
from tools import scrape_url
import re


def generate_report(topic, research, max_retries=2):
    for attempt in range(max_retries + 1):
        report = writer_chain.invoke(
            {
                "topic": topic,
                "research": research,
            }
        )

        if report and report.strip():
            return report

        print(
            f"\nWriter returned an empty response. "
            f"Retry {attempt + 1}/{max_retries}"
        )

    raise RuntimeError("Writer failed to generate a report after multiple attempts.")


def extract_score(feedback: str) -> int:
    """
    Extract score from critic output.

    Expected format:
    Score: X/10
    """

    match = re.search(r"Score:\s*(\d+(?:\.\d+)?)\s*/\s*10", feedback)

    if match:
        return int(float(match.group(1)))

    return 0


def revise_report(topic: str, report: str, feedback: str, research: str) -> str:

    revision_prompt = f"""
You are revising a research report based on critic feedback.

Topic:
{topic}

Original Report:
{report}

Critic Feedback:
{feedback}

Research Sources:
{research}

Rewrite the report to address the critic's concerns.

Important instructions:
- Keep factual claims grounded in the provided research.
- Improve weak or unsupported sections.
- Keep useful information from the original report.
- Do not invent sources or facts.
- Preserve a clear and professional structure.
- Return only the revised research report.
"""

    for attempt in range(3):

        revised_report = writer_chain.invoke(
            {
                "topic": topic,
                "research": revision_prompt,
            }
        )

        if revised_report and revised_report.strip():
            return revised_report

        print(f"\nRevision returned empty response. " f"Retry {attempt + 1}/3")

    raise RuntimeError("Writer failed during revision.")


def run_research_pipeline(topic: str) -> dict:

    state = {}

    # ============================================================
    # STEP 1 - SEARCH AGENT
    # ============================================================

    print("\n" + " =" * 50)
    print("step 1 - search agent is working ...")
    print("=" * 50)

    search_agent = build_search_agent()

    search_result = search_agent.invoke(
        {
            "messages": [
                (
                    "user",
                    f"Find recent, reliable and detailed information about: {topic}",
                )
            ]
        }
    )

    search_content = search_result["messages"][-1].content

    # Gemini can return structured content as a list.
    # Convert it into a plain string for further processing.
    if isinstance(search_content, list):

        state["search_results"] = "\n".join(
            item.get("text", "") for item in search_content if isinstance(item, dict)
        )

    else:
        state["search_results"] = search_content

    print("\nSearch result:\n")
    print(state["search_results"])

    # ============================================================
    # STEP 2 - DETERMINISTIC MULTI-SOURCE SCRAPING
    # ============================================================

    print("\n" + " =" * 50)
    print("step 2 - scraping top research sources ...")
    print("=" * 50)

    search_text = state["search_results"]

    # Extract URLs
    urls = re.findall(r"https?://[^\s\)\]\>]+", search_text)

    # Remove duplicates while preserving order
    unique_urls = []

    for url in urls:

        url = url.rstrip(".,;:")

        if url not in unique_urls:
            unique_urls.append(url)

    print(f"\nFound {len(unique_urls)} unique URLs.")

    # Scrape top 3 sources
    scraped_sources = []

    for i, url in enumerate(unique_urls[:3], start=1):

        print(f"\nScraping source {i}: {url}")

        try:

            content = scrape_url.invoke({"url": url})

            scraped_sources.append(f"""
SOURCE {i}
URL: {url}

CONTENT:
{content}
""")

        except Exception as e:

            print(f"Failed to scrape {url}: {e}")

            scraped_sources.append(f"""
SOURCE {i}
URL: {url}

CONTENT:
Unable to scrape this source.
""")

    state["scraped_content"] = "\n".join(scraped_sources)

    print("\nScraped content:\n")
    print(state["scraped_content"])

    # ============================================================
    # COMBINE RESEARCH
    # ============================================================

    research_combined = (
        f"SEARCH RESULTS:\n"
        f"{state['search_results']}\n\n"
        f"DETAILED CONTENT FROM MULTIPLE SOURCES:\n"
        f"{state['scraped_content']}"
    )

    # ============================================================
    # STEP 3 - WRITER
    # ============================================================

    print("\n" + " =" * 50)
    print("step 3 - Writer is drafting the report ...")
    print("=" * 50)

    state["report"] = generate_report(topic=topic, research=research_combined)

    print("\nInitial Report\n")
    print(state["report"])

    # ============================================================
    # STEP 4 - CRITIC + REVISION LOOP
    # ============================================================

    print("\n" + " =" * 50)
    print("step 4 - critic is reviewing the report")
    print("=" * 50)

    max_revisions = 2

    for revision in range(max_revisions + 1):

        if revision == 0:

            print("\nCritic: Reviewing initial report...")

        else:

            print(f"\nCritic: Reviewing revised report " f"(revision {revision})...")

        state["feedback"] = critic_chain.invoke({"report": state["report"]})

        print("\nCritic report:\n")
        print(state["feedback"])

        score = extract_score(state["feedback"])

        state["score"] = score

        print(f"\nCritic score: {score}/10")

        # --------------------------------------------------------
        # ACCEPT REPORT
        # --------------------------------------------------------

        if score >= 7:

            print("\nReport passed the quality threshold.")

            break

        # --------------------------------------------------------
        # MAXIMUM REVISIONS REACHED
        # --------------------------------------------------------

        if revision == max_revisions:

            print("\nMaximum revision attempts reached.")

            break

        # --------------------------------------------------------
        # REVISE REPORT
        # --------------------------------------------------------

        print("\nReport needs improvement.")

        print("Sending critic feedback back to Writer...")

        state["report"] = revise_report(
            topic=topic,
            report=state["report"],
            feedback=state["feedback"],
            research=research_combined,
        )

        print("\nRevised Report\n")
        print(state["report"])

    # ============================================================
    # FINAL RESULT
    # ============================================================

    print("\n" + " =" * 50)
    print("RESEARCH PIPELINE COMPLETED")
    print("=" * 50)

    print(f"\nFinal Critic Score: " f"{state['score']}/10")

    return state


if __name__ == "__main__":

    topic = input("\nEnter a research topic: ")

    run_research_pipeline(topic)
