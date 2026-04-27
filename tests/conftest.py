from __future__ import annotations

from datetime import date, timedelta

import pytest
from werkzeug.security import generate_password_hash

from app import create_app, db
from app.models import Administrator, Book, Loan, LoanStatus, Member, UserRole, Librarian


@pytest.fixture
def app():
    test_app = create_app(
        {
            "TESTING": True,
            "SECRET_KEY": "test-secret",
            "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
            "SQLALCHEMY_TRACK_MODIFICATIONS": False,
        }
    )

    with test_app.app_context():
        db.drop_all()
        db.create_all()

        member = Member(
            userID="M001",
            username="member1",
            passwordHash=generate_password_hash("member123"),
            email="member1@example.com",
            role=UserRole.MEMBER,
        )
        librarian = Librarian(
            userID="L001",
            username="librarian1",
            passwordHash=generate_password_hash("librarian123"),
            email="librarian1@example.com",
            role=UserRole.LIBRARIAN,
        )
        admin = Administrator(
            userID="A001",
            username="admin1",
            passwordHash=generate_password_hash("admin123"),
            email="admin1@example.com",
            role=UserRole.ADMINISTRATOR,
        )

        book = Book(
            bookID="B001",
            title="Clean Code",
            author="Robert C. Martin",
            isbn="9780132350884",
            genre="Software Engineering",
            location="Shelf A1",
            totalCopies=2,
            availableCopies=2,
        )

        overdue_loan = Loan(
            loanID="LN_OVERDUE_1",
            bookID="B001",
            memberID="M001",
            borrowDate=date.today() - timedelta(days=20),
            dueDate=date.today() - timedelta(days=6),
            returnDate=None,
            status=LoanStatus.ACTIVE,
        )

        db.session.add_all([member, librarian, admin, book, overdue_loan])
        db.session.commit()

    yield test_app


@pytest.fixture
def client(app):
    return app.test_client()
