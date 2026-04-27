from __future__ import annotations

from app.models import Book, Loan, LoanStatus


def _login(client, username: str, password: str):
    return client.post(
        "/login",
        data={"username": username, "password": password},
        follow_redirects=True,
    )


def test_member_search_borrow_return_flow(client, app):
    # Sequence flow: Member login -> searchBooks(query) -> borrowBook(bookID) -> returnBook(loanID)
    response = _login(client, "member1", "member123")
    assert response.status_code == 200
    assert b"Member Dashboard" in response.data

    response = client.post("/member/search", data={"query": "Clean"}, follow_redirects=True)
    assert response.status_code == 200
    assert b"Clean Code" in response.data

    response = client.post("/member/borrow", data={"bookID": "B001"}, follow_redirects=True)
    assert response.status_code == 200
    assert b"Book borrowed successfully" in response.data

    with app.app_context():
        book = Book.query.filter_by(bookID="B001").first()
        assert book is not None
        assert book.availableCopies == 1

        loan = (
            Loan.query.filter_by(bookID="B001", memberID="M001")
            .order_by(Loan.borrowDate.desc())
            .first()
        )
        assert loan is not None
        assert loan.status == LoanStatus.ACTIVE
        loan_id = loan.loanID

    response = client.post("/member/return", data={"loanID": loan_id}, follow_redirects=True)
    assert response.status_code == 200
    assert b"Book returned successfully" in response.data

    with app.app_context():
        book = Book.query.filter_by(bookID="B001").first()
        assert book.availableCopies == 2

        loan = Loan.query.filter_by(loanID=loan_id).first()
        assert loan.status == LoanStatus.RETURNED
        assert loan.returnDate is not None


def test_librarian_add_book_flow(client, app):
    # Sequence flow: Librarian login -> addBook(newBook)
    response = _login(client, "librarian1", "librarian123")
    assert response.status_code == 200
    assert b"Book Management" in response.data

    response = client.post(
        "/librarian/books/add",
        data={
            "bookID": "B002",
            "title": "Refactoring",
            "author": "Martin Fowler",
            "isbn": "9780201485677",
            "genre": "Software Engineering",
            "location": "Shelf A2",
            "totalCopies": "3",
        },
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"Book added successfully" in response.data

    with app.app_context():
        added = Book.query.filter_by(bookID="B002").first()
        assert added is not None
        assert added.availableCopies == 3

    client.post("/logout", follow_redirects=True)
    response = _login(client, "member1", "member123")
    assert response.status_code == 200

    response = client.post("/member/search", data={"query": "Refactoring"}, follow_redirects=True)
    assert response.status_code == 200
    assert b"Refactoring" in response.data
    assert b"Martin Fowler" in response.data


def test_admin_generate_overdue_report_flow(client):
    # Sequence flow: Admin login -> generateReport(reportType="overdue", filters)
    response = _login(client, "admin1", "admin123")
    assert response.status_code == 200
    assert b"User Management" in response.data

    response = client.post(
        "/admin/reports",
        data={"reportType": "overdue", "startDate": "", "endDate": ""},
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"Overdue report generated" in response.data
    assert b"LN_OVERDUE_1" in response.data


def test_role_access_protection(client):
    # Member should not access admin routes.
    _login(client, "member1", "member123")
    response = client.get("/admin/reports", follow_redirects=True)
    assert response.status_code == 200
    assert b"Administrator access required." in response.data
