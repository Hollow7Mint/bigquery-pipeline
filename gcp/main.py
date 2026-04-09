import argparse
import logging
import sys

from config import GCPConfig
from logger_setup import setup


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument("--project", help="GCP project ID (overrides env)")
    parser.add_argument("--region",  default="us-central1")
    parser.add_argument("--credentials", default=None,
                        help="Path to service account JSON")
    parser.add_argument("--debug", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    return parser


def main() -> int:
    parser = build_parser()
    args   = parser.parse_args()

    log = setup(level="DEBUG" if args.debug else "INFO")

    try:
        cfg = GCPConfig.from_env()
        if args.project:
            cfg.project_id = args.project
        if args.region:
            cfg.region = args.region
        cfg.validate()
    except (EnvironmentError, ValueError) as exc:
        log.error("Configuration error: %s", exc)
        return 1

    log.info("Project: %s  Region: %s  Dry-run: %s",
             cfg.project_id, cfg.region, args.dry_run)

    if args.dry_run:
        log.info("[dry-run] no changes will be made")
        return 0

    try:
        run(cfg, args, log)
    except KeyboardInterrupt:
        log.info("Interrupted")
        return 130
    except Exception as exc:
        log.exception("Unhandled error: %s", exc)
        return 1

    return 0


def run(cfg: GCPConfig, args: argparse.Namespace,
        log: logging.Logger) -> None:
    log.info("Running with project=%s", cfg.project_id)


if __name__ == "__main__":
    sys.exit(main())
