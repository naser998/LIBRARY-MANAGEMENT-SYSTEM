from __future__ import annotations

from datetime import datetime, timedelta
from uuid import uuid4

from flask import session
from sqlalchemy import or_

from app import db
from app.models import Book, DeliveryRequest, Loan, LoanStatus, Member, Reservation, UserRole


class DuplicateReservationError(Exception):
    pass


class DeliveryError(Exception):
    pass


class MemberService:
    def __init__(self) -> None:
        self.last_message: str = ""

    def _is_authenticated_member(self) -> bool:
        return session.get("user_id") is not None and session.get("role") == UserRole.MEMBER.value

    def _expire_reservations(self) -> None:
        now = datetime.utcnow()
        expired = Reservation.query.filter(Reservation.status == "active", Reservation.expires_at < now).all()
        if expired:
            for reservation in expired:
                reservation.status = "expired"
            db.session.commit()

    def searchBooks(self, query: str) -> list[Book]:
        q = (query or "").strip()
        if not q:
            self.last_message = "Please enter a search query."
            return []
        like_value = f"%{q}%"
        books = (
            Book.query.order_by(Book.title.asc())
            .filter(
                or_(
                    Book.title.ilike(like_value),
                    Book.author.ilike(like_value),
                    Book.isbn.ilike(like_value),
                    Book.genre.ilike(like_value),
                )
            )
            .all()
        )
        self.last_message = f"Found {len(books)} matching book(s)."
        return books

    def viewActiveLoans(self) -> list[Loan]:
        if not self._is_authenticated_member():
            self.last_message = "Please log in first."
            return []
        self._expire_reservations()
        loans = (
            Loan.query.filter_by(memberID=session["user_id"])
            .filter(Loan.status.in_([LoanStatus.ACTIVE, LoanStatus.OVERDUE]))
            .order_by(Loan.borrowDate.desc())
            .all()
        )
        self.last_message = f"Found {len(loans)} active loan(s)."
        return loans

    def viewMyLoans(self) -> list[Loan]:
        if not self._is_authenticated_member():
            self.last_message = "Please log in first."
            return []
        self._expire_reservations()
        loans = Loan.query.filter_by(memberID=session["user_id"]).order_by(Loan.borrowDate.desc()).all()
        self.last_message = f"Found {len(loans)} loan(s)."
        return loans

    def getBookById(self, bookID: str) -> Book | None:
        return Book.query.filter_by(bookID=bookID).first()

    def getActiveReservations(self, memberId: str | None = None) -> list[Reservation]:
        if memberId is None:
            if not self._is_authenticated_member():
                return []
            memberId = session["user_id"]
        self._expire_reservations()
        return (
            Reservation.query.filter_by(member_id=memberId, status="active")
            .order_by(Reservation.reserved_at.desc())
            .all()
        )

    def reserveBook(self, memberId: int, bookId: int) -> Reservation:
        self._expire_reservations()
        member = Member.query.filter_by(userID=str(memberId)).first()
        if member is None:
            raise ValueError("Member not found.")
        book = Book.query.filter_by(bookID=str(bookId)).first()
        if book is None:
            raise ValueError("Book not found.")

        existing_reservation = Reservation.query.filter_by(member_id=member.userID, book_id=book.bookID, status="active").first()
        if existing_reservation is not None:
            raise DuplicateReservationError("You already have an active reservation for this book.")

        active_loan = Loan.query.filter_by(memberID=member.userID, bookID=book.bookID).filter(
            Loan.status.in_([LoanStatus.ACTIVE, LoanStatus.OVERDUE])
        ).first()
        if active_loan is not None:
            raise ValueError("You already have an active loan for this book.")

        reservation = Reservation(member_id=member.userID, book_id=book.bookID, status="active")
        db.session.add(reservation)
        db.session.commit()
        self.last_message = "Reservation created for 24 hours."
        return reservation

    def cancelReservation(self, reservationId: int, memberId: int) -> bool:
        reservation = Reservation.query.filter_by(id=reservationId, member_id=str(memberId), status="active").first()
        if reservation is None:
            self.last_message = "Active reservation not found."
            return False
        reservation.status = "expired"
        db.session.commit()
        self.last_message = "Reservation cancelled."
        return True

    def borrowBook(self, bookID: str):
        if not self._is_authenticated_member():
            self.last_message = "Please log in first."
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
            borrowDate=datetime.utcnow().date(),
            dueDate=datetime.utcnow().date() + timedelta(days=14),
            returnDate=None,
            status=LoanStatus.ACTIVE,
        )
        book.availableCopies -= 1
        db.session.add(loan)
        db.session.commit()
        self.last_message = f"Book borrowed successfully. Due: {loan.dueDate.isoformat()}."
        return loan

    def returnBook(self, loanID: str) -> bool:
        if "user_id" not in session or "role" not in session:
            self.last_message = "Please log in first."
            return False
        role = session["role"]
        if role not in {UserRole.MEMBER.value, UserRole.LIBRARIAN.value}:
            self.last_message = "Access denied for this action."
            return False
        loan = Loan.query.filter_by(loanID=loanID).first()
        if loan is None:
            self.last_message = "Loan not found."
            return False
        if role == UserRole.MEMBER.value and loan.memberID != session["user_id"]:
            self.last_message = "You can only return your own loans."
            return False
        if loan.status == LoanStatus.RETURNED:
            self.last_message = "Loan already returned."
            return False
        book = Book.query.filter_by(bookID=loan.bookID).first()
        if book is None:
            self.last_message = "Related book not found."
            return False

        loan.returnDate = datetime.utcnow().date()
        loan.status = LoanStatus.RETURNED
        book.availableCopies += 1

        active_reservation = Reservation.query.filter_by(member_id=loan.memberID, book_id=loan.bookID, status="active").first()
        if active_reservation is not None:
            active_reservation.status = "fulfilled"

        db.session.commit()
        self.last_message = "Book returned successfully."
        return True

    def requestDelivery(self, loanId: int, memberId: int, address: str) -> DeliveryRequest:
        loan = Loan.query.filter_by(loanID=str(loanId), memberID=str(memberId)).first()
        if loan is None:
            raise DeliveryError("Loan not found.")
        if loan.status != LoanStatus.ACTIVE:
            raise DeliveryError("Delivery can only be requested for active loans.")
        if not (address or "").strip():
            raise DeliveryError("Delivery address is required.")

        pending = DeliveryRequest.query.filter_by(loan_id=loan.loanID, status="pending").first()
        if pending is not None:
            raise DeliveryError("A pending delivery request already exists for this loan.")

        delivery = DeliveryRequest(
            loan_id=loan.loanID,
            member_id=loan.memberID,
            delivery_address=address.strip(),
            status="pending",
        )
        db.session.add(delivery)
        db.session.commit()
        self.last_message = "Delivery request submitted successfully."
        return delivery

    def cancelDelivery(self, deliveryId: int, memberId: int) -> bool:
        delivery = DeliveryRequest.query.filter_by(id=deliveryId, member_id=str(memberId), status="pending").first()
        if delivery is None:
            self.last_message = "Pending delivery request not found."
            return False
        delivery.status = "cancelled"
        db.session.commit()
        self.last_message = "Delivery request cancelled."
        return True
