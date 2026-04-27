from __future__ import annotations

import argparse

from app import create_app, db


def main() -> None:
    parser = argparse.ArgumentParser(description="Initialize LMS database.")
    parser.add_argument("--reset", action="store_true", help="Drop all tables before creating them again.")
    args = parser.parse_args()

    app = create_app()
    with app.app_context():
        from app import models  # noqa: F401

        if args.reset:
            db.drop_all()
        db.create_all()
    print("Database initialized successfully.")


if __name__ == "__main__":
    main()
