from __future__ import annotations

from datetime import date, datetime
from typing import Any

from flask import session

from app.models import Book, Loan, LoanStatus, User, UserRole


class ReportService:
    def __init__(self) -> None:
        self.last_message: str = ""

    def _require_admin(self) -> bool:
        if "user_id" not in session or "role" not in session:
            self.last_message = "Please log in first."
            return False
        if UserRole(session["role"]) != UserRole.ADMINISTRATOR:
            self.last_message = "Administrator role required."
            return False
        return True

    def generateReport(self, reportType: str, filters: dict[str, Any]) -> str:
        # Sequence (Admin): Step 3 generateReport(reportType="overdue", filters)
        if not self._require_admin():
            return self.last_message

        report_type = (reportType or "").strip().lower()
        if report_type == "overdue":
            return self.generateOverdueReport()
        if report_type == "inventory":
            return self.generateInventoryReport()
        if report_type == "borrowing":
            start = self._parse_date(filters.get("startDate") if filters else None)
            end = self._parse_date(filters.get("endDate") if filters else None)
            if start is None or end is None:
                self.last_message = "startDate and endDate are required (YYYY-MM-DD)."
                return self.last_message
            return self.generateBorrowingReport(start, end)

        self.last_message = "Unsupported report type."
        return self.last_message

    def generateBorrowingReport(self, startDate: date, endDate: date) -> str:
        if not self._require_admin():
            return self.last_message
        if startDate > endDate:
            self.last_message = "startDate cannot be after endDate."
            return self.last_message

        loans = Loan.query.filter(Loan.borrowDate >= startDate, Loan.borrowDate <= endDate).all()
        rows = []
        for loan in loans:
            rows.append(
                "<tr>"
                f"<td>{loan.loanID}</td>"
                f"<td>{loan.bookID}</td>"
                f"<td>{loan.memberID}</td>"
                f"<td>{loan.borrowDate}</td>"
                f"<td>{loan.dueDate}</td>"
                f"<td>{loan.status.value}</td>"
                "</tr>"
            )
        self.last_message = f"Borrowing report generated with {len(loans)} record(s)."
        return (
            "<table class='table table-striped'>"
            "<thead><tr><th>Loan ID</th><th>Book ID</th><th>Member ID</th><th>Borrow Date</th><th>Due Date</th><th>Status</th></tr></thead>"
            f"<tbody>{''.join(rows)}</tbody></table>"
        )

    def generateOverdueReport(self) -> str:
        # Sequence DB step: active loans where dueDate < CURRENT_DATE with joins to Book and Member(User)
        if not self._require_admin():
            return self.last_message

        loans = Loan.query.filter(Loan.status == LoanStatus.ACTIVE, Loan.dueDate < date.today()).all()
        rows = []
        for loan in loans:
            book = Book.query.filter_by(bookID=loan.bookID).first()
            member = User.query.filter_by(userID=loan.memberID).first()
            rows.append(
                "<tr>"
                f"<td>{loan.loanID}</td>"
                f"<td>{book.title if book else loan.bookID}</td>"
                f"<td>{member.username if member else loan.memberID}</td>"
                f"<td>{loan.dueDate}</td>"
                "</tr>"
            )
        self.last_message = f"Overdue report generated with {len(loans)} record(s)."
        return (
            "<table class='table table-striped'>"
            "<thead><tr><th>Loan ID</th><th>Book Title</th><th>Member Username</th><th>Due Date</th></tr></thead>"
            f"<tbody>{''.join(rows)}</tbody></table>"
        )

    def generateInventoryReport(self) -> str:
        if not self._require_admin():
            return self.last_message

        books = Book.query.order_by(Book.title.asc()).all()
        rows = []
        for book in books:
            rows.append(
                "<tr>"
                f"<td>{book.bookID}</td>"
                f"<td>{book.title}</td>"
                f"<td>{book.totalCopies}</td>"
                f"<td>{book.availableCopies}</td>"
                "</tr>"
            )
        self.last_message = f"Inventory report generated with {len(books)} record(s)."
        return (
            "<table class='table table-striped'>"
            "<thead><tr><th>Book ID</th><th>Title</th><th>Total Copies</th><th>Available Copies</th></tr></thead>"
            f"<tbody>{''.join(rows)}</tbody></table>"
        )

    def _parse_date(self, value: Any) -> date | None:
        if isinstance(value, date):
            return value
        if not value:
            return None
        try:
            return datetime.strptime(str(value), "%Y-%m-%d").date()
        except ValueError:
            return None
