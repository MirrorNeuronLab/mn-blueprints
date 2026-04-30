from pathlib import Path


def collect_research_summary(topic: str, instructions: str) -> dict:
    return {
        "topic": topic,
        "instructions": instructions,
        "findings": [
            "Public charging availability is a visible adoption constraint.",
            "Utility make-ready programs reduce site deployment friction.",
            "Cold-weather range confidence remains important for consumers.",
        ],
        "recommendation": "Prioritize corridor fast charging and workplace Level 2 charging.",
    }


def save_summary(summary: dict) -> str:
    path = Path("research_summary.json")
    path.write_text(__import__("json").dumps(summary, indent=2, sort_keys=True) + "\n")
    return str(path)
