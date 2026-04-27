from __future__ import annotations

from datetime import date, timedelta
from uuid import uuid4

from flask import session

from app import db
from app.models import Book, Loan, LoanStatus, UserRole


class LoanService:
    def __init__(self) -> None:
        self.last_message: str = ""

    def _require_role(self, allowed_roles: set[UserRole]) -> bool:
        if "user_id" not in session or "role" not in session:
            self.last_message = "Please log in first."
            return False
        role = UserRole(session["role"])
        if role not in allowed_roles:
            self.last_message = "Access denied for this action."
            return False
        return True

    def borrowBook(self, bookID: str):
        # Sequence (Member) Step 3: availability check -> create loan (14 days) -> decrement copies
        if not self._require_role({UserRole.MEMBER}):
            return None

        book = Book.query.filter_by(bookID=bookID).first()
        if book is None:
            self.last_message = "Book not found."
            return None
        if book.availableCopies <= 0:
            self.last_message = "Book not available."
            return None

        loan = Loan(
            loanID=uuid4().hex[:12],
            bookID=book.bookID,
            memberID=session["user_id"],
            borrowDate=date.today(),
            dueDate=date.today() + timedelta(days=14),
            returnDate=None,
            status=LoanStatus.ACTIVE,
        )
        book.availableCopies -= 1

        db.session.add(loan)
        db.session.commit()
        self.last_message = f"Book borrowed successfully. Due: {loan.dueDate.isoformat()}."
        return loan

    def returnBook(self, loanID: str) -> bool:
        if not self._require_role({UserRole.MEMBER, UserRole.LIBRARIAN}):
            return False
        loan = Loan.query.filter_by(loanID=loanID).first()
        if loan is None:
            self.last_message = "Loan not found."
            return False
        if UserRole(session["role"]) == UserRole.MEMBER and loan.memberID != session["user_id"]:
            self.last_message = "You can only return your own loans."
            return False
        return self.processReturn(loanID)

    def viewMyLoans(self) -> list[Loan]:
        if not self._require_role({UserRole.MEMBER}):
            return []
        loans = Loan.query.filter_by(memberID=session["user_id"]).order_by(Loan.borrowDate.desc()).all()
        self.last_message = f"Found {len(loans)} loan(s)."
        return loans

    def processReturn(self, loanID: str) -> bool:
        if not self._require_role({UserRole.MEMBER, UserRole.LIBRARIAN}):
            return False
        loan = Loan.query.filter_by(loanID=loanID).first()
        if loan is None:
            self.last_message = "Loan not found."
            return False
        if loan.status == LoanStatus.RETURNED:
            self.last_message = "Loan already returned."
            return False

        book = Book.query.filter_by(bookID=loan.bookID).first()
        if book is None:
            self.last_message = "Related book not found."
            return False

        loan.returnDate = date.today()
        loan.status = LoanStatus.RETURNED
        book.availableCopies += 1
        db.session.commit()

        fine = loan.calculateFine()
        self.last_message = f"Book returned successfully. Fine: {fine:.2f}." if fine > 0 else "Book returned successfully."
        return True

    def notifyOverdue(self) -> None:
        if not self._require_role({UserRole.LIBRARIAN}):
            return

        overdue = Loan.query.filter(Loan.status == LoanStatus.ACTIVE, Loan.dueDate < date.today()).all()
        for loan in overdue:
            loan.status = LoanStatus.OVERDUE
        db.session.commit()
        self.last_message = f"Marked {len(overdue)} loan(s) as overdue."
