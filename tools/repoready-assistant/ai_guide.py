
"""RepoGuide AI: generate an onboarding guide for a repository."""
import argparse
import os
from pathlib import Path

from main import inspect_repository



def create_onboarding_guide(root: Path) -> str:
    """Create an AI guide using the repository README and file checks."""
    root = root.expanduser().resolve()

    if not root.exists() or not root.is_dir():
       raise FileNotFoundError(f"Repository directory does not exist: {root}")

    report = inspect_repository(root)

    readme_path = root.expanduser().resolve() / "README.md"
    readme = ""

    if readme_path.is_file():
        # Keep the prompt bounded; inspect the README before sharing it.
        readme = readme_path.read_text(
            encoding="utf-8", errors="replace"
        )[:12000]

    findings = "\n".join(
        f"- {item['status']}: {item['check']} — {item['message']}"
        for item in report["results"]
    )

    if not os.environ.get("GEMINI_API_KEY"):
        return (
            "AI mode is unavailable because GEMINI_API_KEY is not set.\n\n"
            "Local repository checks:\n"
            f"{findings}\n\n"
            "Set GEMINI_API_KEY to enable AI-generated guidance."
        )

    # Import only when AI mode is enabled.
    from google import genai

    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

    prompt = f"""
You are RepoGuide AI, a repository onboarding assistant.

Use only the evidence provided below. Do not invent commands,
dependencies, files, or project capabilities. Clearly label assumptions.
Recommend safe next steps and never suggest exposing secrets.

Repository path: {report["repository"]}

Local inspection findings:
{findings}

README content:
---
{readme}
---

Write an onboarding guide with these sections:
1. What this project appears to do
2. Prerequisites supported by the README
3. Setup and run instructions supported by the README
4. Missing files or documentation to review
5. Recommended next steps for a new contributor

If information is unavailable, say so. Do not claim that you ran
the repository's code or tests.
"""

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
    )

    if not response.text:
        raise RuntimeError("The AI provider returned an empty response.")

    return response.text


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate a repository onboarding guide."
    )
    parser.add_argument(
        "path",
        nargs="?",
        default=".",
        help="Repository path to inspect",
    )
    args = parser.parse_args()

    root = Path(args.path)

    try:
        guide = create_onboarding_guide(root)
        print("\nRepoGuide AI — Onboarding Guide")
        print("=" * 40)
        print(guide)
    except (FileNotFoundError, NotADirectoryError) as exc:
        parser.error(str(exc))
    except Exception as exc:
        print(f"Could not generate the AI guide: {exc}")
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
