"""Run with python -m agri_data INPUT.kml --mode live."""
import argparse
from agri_data.pipeline import run_pipeline


def main():
    parser = argparse.ArgumentParser(description="Collect agricultural observations for KML plots")
    parser.add_argument("kml")
    parser.add_argument("--mode", choices=["live", "demo"], default="live")
    parser.add_argument("--start-date", default="2025-01-01")
    parser.add_argument("--end-date", default="2025-12-31")
    parser.add_argument("--project-name")
    args = parser.parse_args()
    result = run_pipeline(args.kml, mode=args.mode, start_date=args.start_date, end_date=args.end_date, project_name=args.project_name)
    print(result["project_report"])


if __name__ == "__main__":
    main()
