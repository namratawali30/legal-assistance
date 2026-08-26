import argparse
import asyncio
import json

from bson import ObjectId
from bson.errors import InvalidId

from app.services.evidence_reconciliation_service import (
    build_evidence_health_report,
)


def parse_arguments():
    parser = argparse.ArgumentParser(
        description=(
            "Report inconsistencies between "
            "evidence metadata and private storage."
        )
    )

    parser.add_argument(
        "--user-id",
        default=None,
        help=(
            "Optional MongoDB user ObjectId. "
            "When omitted, all evidence is checked."
        ),
    )

    parser.add_argument(
        "--skip-hashes",
        action="store_true",
        help=(
            "Skip SHA-256 verification for a faster scan."
        ),
    )

    parser.add_argument(
        "--fail-on-issues",
        action="store_true",
        help=(
            "Exit with status 1 when inconsistencies "
            "are detected."
        ),
    )

    return parser.parse_args()


def normalize_user_id(
    value,
):
    if value is None:
        return None

    try:
        return ObjectId(
            value
        )

    except (
        InvalidId,
        TypeError,
        ValueError,
    ) as exc:
        raise SystemExit(
            "Invalid --user-id ObjectId."
        ) from exc


async def main():
    args = parse_arguments()

    user_id = normalize_user_id(
        args.user_id
    )

    report = await build_evidence_health_report(
        user_id=user_id,
        verify_hashes=(
            not args.skip_hashes
        ),
    )

    print(
        json.dumps(
            report,
            indent=2,
            default=str,
        )
    )

    if (
        args.fail_on_issues
        and not report[
            "healthy"
        ]
    ):
        raise SystemExit(
            1
        )


if __name__ == "__main__":
    asyncio.run(
        main()
    )