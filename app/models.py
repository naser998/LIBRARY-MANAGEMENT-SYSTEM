from __future__ import annotations

from datetime import date, datetime, timedelta
from enum import Enum
from typing import Any

from app import db


class UserRole(str, Enum):
    MEMBER = "MEMBER"
    LIBRARIAN = "LIBRARIAN"
    ADMINISTRATOR = "ADMINISTRATOR"


class LoanStatus(str, Enum):
    ACTIVE = "ACTIVE"
    RETURNED = "RETURNED"
    OVERDUE = "OVERDUE"


class User(db.Model):
    __tablename__ = "users"

    userID = db.Column(db.String, primary_key=True)
    username = db.Column(db.String, unique=True, nullable=False)
    passwordHash = db.Column(db.String, nullable=False)
    email = db.Column(db.String, unique=True, nullable=False)
    role = db.Column(db.Enum(UserRole), nullable=False)

    __mapper_args__ = {"polymorphic_on": role}

    def login(self, username: str, password: str) -> bool:
        raise NotImplementedError

    def logout(self) -> None:
        raise NotImplementedError


class Member(User):
    __tablename__ = "members"

    userID = db.Column(db.String, db.ForeignKey("users.userID"), primary_key=True)
    loans = db.relationship("Loan", back_populates="member", cascade="all, delete-orphan")
    reservations = db.relationship("Reservation", back_populates="member", cascade="all, delete-orphan")
    deliveryRequests = db.relationship("DeliveryRequest", back_populates="member", cascade="all, delete-orphan")

    __mapper_args__ = {"polymorphic_identity": UserRole.MEMBER}

    def searchBooks(self, query: str) -> list["Book"]:
        raise NotImplementedError

    def borrowBook(self, bookID: str) -> "Loan":
        raise NotImplementedError

    def returnBook(self, loanID: str) -> bool:
        raise NotImplementedError

    def viewMyLoans(self) -> list["Loan"]:
        raise NotImplementedError


class Librarian(User):
    __tablename__ = "librarians"

    userID = db.Column(db.String, db.ForeignKey("users.userID"), primary_key=True)

    __mapper_args__ = {"polymorphic_identity": UserRole.LIBRARIAN}

    def addBook(self, book: "Book") -> bool:
        raise NotImplementedError

    def updateBook(self, bookID: str, updatedInfo: "Book") -> bool:
        raise NotImplementedError

    def removeBook(self, bookID: str) -> bool:
        raise NotImplementedError

    def processReturn(self, loanID: str) -> bool:
        raise NotImplementedError

    def notifyOverdue(self) -> None:
        raise NotImplementedError


class Administrator(User):
    __tablename__ = "administrators"

    userID = db.Column(db.String, db.ForeignKey("users.userID"), primary_key=True)

    __mapper_args__ = {"polymorphic_identity": UserRole.ADMINISTRATOR}

    def manageUser(self, userID: str, action: str, data: User) -> bool:
        raise NotImplementedError

    def generateReport(self, reportType: str, filters: dict[str, Any]) -> str:
        raise NotImplementedError

    def configureSetting(self, key: str, value: object) -> bool:
        raise NotImplementedError


class Book(db.Model):
    __tablename__ = "books"

    bookID = db.Column(db.String, primary_key=True)
    title = db.Column(db.String, nullable=False)
    author = db.Column(db.String, nullable=False)
    isbn = db.Column(db.String, unique=True, nullable=False)
    genre = db.Column(db.String, nullable=False)
    location = db.Column(db.String, nullable=False)
    totalCopies = db.Column(db.Integer, nullable=False)
    availableCopies = db.Column(db.Integer, nullable=False)

    loans = db.relationship("Loan", back_populates="book")
    reservations = db.relationship("Reservation", back_populates="book", cascade="all, delete-orphan")

    def checkAvailability(self) -> bool:
        return self.availableCopies > 0

    def updateAvailability(self, delta: int) -> None:
        self.availableCopies += delta


class Loan(db.Model):
    __tablename__ = "loans"

    loanID = db.Column(db.String, primary_key=True)
    bookID = db.Column(db.String, db.ForeignKey("books.bookID"), nullable=False)
    memberID = db.Column(db.String, db.ForeignKey("members.userID"), nullable=False)
    borrowDate = db.Column(db.Date, nullable=False)
    dueDate = db.Column(db.Date, nullable=False)
    returnDate = db.Column(db.Date, nullable=True)
    status = db.Column(db.Enum(LoanStatus), nullable=False)

    member = db.relationship("Member", back_populates="loans")
    book = db.relationship("Book", back_populates="loans")
    deliveryRequest = db.relationship("DeliveryRequest", back_populates="loan", uselist=False, cascade="all, delete-orphan")

    def isOverdue(self) -> bool:
        return self.status != LoanStatus.RETURNED and date.today() > self.dueDate

    def calculateFine(self) -> float:
        if self.status == LoanStatus.RETURNED and self.returnDate:
            overdue_days = (self.returnDate - self.dueDate).days
        else:
            overdue_days = (date.today() - self.dueDate).days
        return float(max(0, overdue_days))


class Reservation(db.Model):
    __tablename__ = "reservations"

    id = db.Column(db.Integer, primary_key=True)
    member_id = db.Column(db.String, db.ForeignKey("members.userID"), nullable=False, index=True)
    book_id = db.Column(db.String, db.ForeignKey("books.bookID"), nullable=False, index=True)
    reserved_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.utcnow() + timedelta(hours=24))
    status = db.Column(db.String(20), nullable=False, default="active")

    member = db.relationship("Member", back_populates="reservations")
    book = db.relationship("Book", back_populates="reservations")


class DeliveryRequest(db.Model):
    __tablename__ = "delivery_requests"

    id = db.Column(db.Integer, primary_key=True)
    loan_id = db.Column(db.String, db.ForeignKey("loans.loanID"), nullable=False, unique=True, index=True)
    member_id = db.Column(db.String, db.ForeignKey("members.userID"), nullable=False, index=True)
    delivery_address = db.Column(db.String(500), nullable=False)
    requested_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    status = db.Column(db.String(20), nullable=False, default="pending")
    notes = db.Column(db.String(500), nullable=True)

    loan = db.relationship("Loan", back_populates="deliveryRequest")
    member = db.relationship("Member", back_populates="deliveryRequests")


class Report:
    def generateBorrowingReport(self, startDate: date, endDate: date) -> str:
        raise NotImplementedError

    def generateOverdueReport(self) -> str:
        raise NotImplementedError

    def generateInventoryReport(self) -> str:
        raise NotImplementedError
