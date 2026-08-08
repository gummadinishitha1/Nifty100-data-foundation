"""Sector report entry point."""

from __future__ import annotations

from src.reports.tearsheet import generate_sector_reports, load_report_data


def main() -> None:
    paths = generate_sector_reports(load_report_data())
    print(f"Wrote {len(paths)} sector reports")


if __name__ == "__main__":
    main()
