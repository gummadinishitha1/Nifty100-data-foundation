"""Simple validation entry point for the ETL foundation."""

from pathlib import Path


OUTPUT_DIR = Path("output")


def run_validation() -> None:
    """Placeholder validation runner for the current sprint."""
    OUTPUT_DIR.mkdir(exist_ok=True)
    print("Validation pipeline is ready.")


if __name__ == "__main__":
    run_validation()
