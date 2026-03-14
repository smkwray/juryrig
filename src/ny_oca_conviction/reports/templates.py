from __future__ import annotations


def report_header(run_id: str, best_model: str | None) -> str:
    return "\n".join(
        [
            f"# Run Report - {run_id}",
            "",
            f"- best_model: {best_model or 'unknown'}",
            "",
        ]
    )
