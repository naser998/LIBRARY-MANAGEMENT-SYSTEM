from __future__ import annotations

from werkzeug.security import generate_password_hash

from app import create_app, db
from app.models import Administrator, Librarian, Member, UserRole

app = create_app()


def seed_users() -> None:
    with app.app_context():
        users_to_create = [
            {
                "cls": Member,
                "userID": "M001",
                "username": "member1",
                "password": "member123",
                "email": "member1@example.com",
                "role": UserRole.MEMBER,
            },
            {
                "cls": Librarian,
                "userID": "L001",
                "username": "librarian1",
                "password": "librarian123",
                "email": "librarian1@example.com",
                "role": UserRole.LIBRARIAN,
            },
            {
                "cls": Administrator,
                "userID": "A001",
                "username": "admin1",
                "password": "admin123",
                "email": "admin1@example.com",
                "role": UserRole.ADMINISTRATOR,
            },
        ]

        created_count = 0
        for data in users_to_create:
            exists = data["cls"].query.filter_by(username=data["username"]).first()
            if exists:
                continue

            user = data["cls"](
                userID=data["userID"],
                username=data["username"],
                passwordHash=generate_password_hash(data["password"]),
                email=data["email"],
                role=data["role"],
            )
            db.session.add(user)
            created_count += 1

        db.session.commit()
        print(f"Seeding complete. Created {created_count} user(s).")


if __name__ == "__main__":
    seed_users()
