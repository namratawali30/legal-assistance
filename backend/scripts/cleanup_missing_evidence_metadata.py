import argparse
import asyncio
import json
from pathlib import Path

from bson import ObjectId
from bson.errors import InvalidId

from app.database import database
from app.db.collections import (
    EVIDENCE_COLLECTION,
)
from app.services.evidence_reconciliation_service import (
    build_evidence_health_report,
)


CONFIRMATION_TEXT = (
    "DELETE_MISSING_EVIDENCE_METADATA"
)

PLAN_TYPE = (
    "missing_evidence_metadata_cleanup_plan"
)


def parse_arguments():
    parser = argparse.ArgumentParser(
        description=(
            "Safely review and remove MongoDB "
            "evidence metadata whose physical "
            "files are confirmed missing."
        )
    )

    parser.add_argument(
        "--write-plan",
        metavar="FILE",
        help=(
            "Write an exact cleanup plan to a JSON "
            "file. No database changes are made."
        ),
    )

    parser.add_argument(
        "--apply-plan",
        metavar="FILE",
        help=(
            "Apply a previously reviewed cleanup "
            "plan after rechecking current state."
        ),
    )

    parser.add_argument(
        "--confirm",
        default=None,
        help=(
            "Required confirmation text when "
            "applying a cleanup plan."
        ),
    )

    return parser.parse_args()


def build_plan(
    missing_files: list[dict],
) -> dict:
    return {
        "plan_type":
            PLAN_TYPE,

        "record_count":
            len(
                missing_files
            ),

        "records": [
            {
                "evidence_id":
                    item[
                        "evidence_id"
                    ],

                "user_id":
                    item[
                        "user_id"
                    ],

                "complaint_id":
                    item.get(
                        "complaint_id"
                    ),

                "original_filename":
                    item.get(
                        "original_filename"
                    ),

                "storage_path":
                    item.get(
                        "storage_path"
                    ),
            }
            for item in missing_files
        ],
    }


def read_plan(
    path: Path,
) -> dict:
    try:
        data = json.loads(
            path.read_text(
                encoding="utf-8"
            )
        )

    except (
        OSError,
        json.JSONDecodeError,
    ) as exc:
        raise SystemExit(
            "Cleanup plan could not be read."
        ) from exc

    if data.get(
        "plan_type"
    ) != PLAN_TYPE:
        raise SystemExit(
            "Invalid cleanup plan type."
        )

    records = data.get(
        "records"
    )

    if not isinstance(
        records,
        list,
    ):
        raise SystemExit(
            "Cleanup plan does not contain "
            "a valid record list."
        )

    return data


def display_missing_records(
    missing_files: list[dict],
) -> None:
    print()
    print(
        "Missing evidence metadata records:"
    )
    print(
        "=" * 60
    )

    for item in missing_files:
        print(
            f"Evidence ID: "
            f"{item.get('evidence_id')}"
        )

        print(
            f"User ID:     "
            f"{item.get('user_id')}"
        )

        print(
            f"Complaint:   "
            f"{item.get('complaint_id')}"
        )

        print(
            f"Filename:    "
            f"{item.get('original_filename')}"
        )

        print(
            f"Storage:     "
            f"{item.get('storage_path')}"
        )

        print(
            "-" * 60
        )


async def create_cleanup_plan(
    output_path: Path,
) -> None:
    report = (
        await build_evidence_health_report(
            verify_hashes=False
        )
    )

    missing_files = report[
        "missing_files"
    ]

    print(
        f"Missing records found: "
        f"{len(missing_files)}"
    )

    if not missing_files:
        print(
            "Nothing needs to be planned."
        )
        return

    plan = build_plan(
        missing_files
    )

    output_path.write_text(
        json.dumps(
            plan,
            indent=2,
        ),
        encoding="utf-8",
    )

    print(
        f"Cleanup plan written to: "
        f"{output_path}"
    )

    print(
        "No database changes were made."
    )


async def apply_cleanup_plan(
    plan_path: Path,
    confirmation: str | None,
) -> None:
    if confirmation != CONFIRMATION_TEXT:
        raise SystemExit(
            "Cleanup was NOT applied.\n"
            "Required confirmation:\n"
            f"{CONFIRMATION_TEXT}"
        )

    plan = read_plan(
        plan_path
    )

    # Re-run health check immediately before
    # deleting anything.
    current_report = (
        await build_evidence_health_report(
            verify_hashes=False
        )
    )

    current_missing = {
        item[
            "evidence_id"
        ]:
            item
        for item in current_report[
            "missing_files"
        ]
    }

    collection = database[
        EVIDENCE_COLLECTION
    ]

    deleted_count = 0
    skipped_count = 0

    for planned in plan[
        "records"
    ]:
        evidence_id = planned.get(
            "evidence_id"
        )

        current = current_missing.get(
            evidence_id
        )

        # If it is no longer missing, skip it.
        if not current:
            print(
                f"SKIP {evidence_id}: "
                "record is no longer reported "
                "as missing."
            )

            skipped_count += 1
            continue

        # Storage path must still exactly match
        # the reviewed cleanup plan.
        if (
            current.get(
                "storage_path"
            )
            != planned.get(
                "storage_path"
            )
        ):
            print(
                f"SKIP {evidence_id}: "
                "storage path changed."
            )

            skipped_count += 1
            continue

        # User ownership metadata must also still
        # match the reviewed plan.
        if (
            current.get(
                "user_id"
            )
            != planned.get(
                "user_id"
            )
        ):
            print(
                f"SKIP {evidence_id}: "
                "user ID changed."
            )

            skipped_count += 1
            continue

        try:
            object_id = ObjectId(
                evidence_id
            )

            user_id = ObjectId(
                planned[
                    "user_id"
                ]
            )

        except (
            InvalidId,
            TypeError,
            ValueError,
        ):
            print(
                f"SKIP {evidence_id}: "
                "invalid ObjectId."
            )

            skipped_count += 1
            continue

        result = await collection.delete_one(
            {
                "_id":
                    object_id,

                "user_id":
                    user_id,

                "storage_path":
                    planned.get(
                        "storage_path"
                    ),
            }
        )

        if result.deleted_count == 1:
            deleted_count += 1

            print(
                f"DELETE {evidence_id}"
            )

        else:
            skipped_count += 1

            print(
                f"SKIP {evidence_id}: "
                "database record did not "
                "match the reviewed plan."
            )

    print()
    print(
        "Cleanup completed."
    )

    print(
        f"Deleted metadata records: "
        f"{deleted_count}"
    )

    print(
        f"Skipped records: "
        f"{skipped_count}"
    )

    print()
    print(
        "No physical evidence files "
        "were deleted by this command."
    )


async def show_dry_run():
    report = (
        await build_evidence_health_report(
            verify_hashes=False
        )
    )

    missing_files = report[
        "missing_files"
    ]

    print(
        f"Missing metadata records: "
        f"{len(missing_files)}"
    )

    display_missing_records(
        missing_files
    )

    print()
    print(
        "DRY RUN ONLY."
    )

    print(
        "No database records or files "
        "were changed."
    )


async def main():
    args = parse_arguments()

    if (
        args.write_plan
        and args.apply_plan
    ):
        raise SystemExit(
            "Use either --write-plan or "
            "--apply-plan, not both."
        )

    if args.write_plan:
        await create_cleanup_plan(
            Path(
                args.write_plan
            )
        )

        return

    if args.apply_plan:
        await apply_cleanup_plan(
            Path(
                args.apply_plan
            ),
            args.confirm,
        )

        return

    await show_dry_run()


if __name__ == "__main__":
    asyncio.run(
        main()
    )