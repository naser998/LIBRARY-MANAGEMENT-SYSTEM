from __future__ import annotations

from uuid import uuid4

from flask import session
from sqlalchemy import or_

from app import db
from app.models import Book, UserRole


class BookService:
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

    def _catalogue_query(self):
        # Shared catalogue query for all roles.
        return Book.query.order_by(Book.title.asc())

    def listBooks(self) -> list[Book]:
        if not self._require_role({UserRole.MEMBER, UserRole.LIBRARIAN, UserRole.ADMINISTRATOR}):
            return []

        books = self._catalogue_query().all()
        self.last_message = f"Found {len(books)} book(s) in catalogue."
        return books

    def searchBooks(self, query: str) -> list[Book]:
        # Sequence (Member): Step 2 searchBooks(query)
        if not self._require_role({UserRole.MEMBER, UserRole.LIBRARIAN, UserRole.ADMINISTRATOR}):
            return []

        q = (query or "").strip()
        if not q:
            self.last_message = "Please enter a search query."
            return []

        like_value = f"%{q}%"
        books = (
            self._catalogue_query().filter(
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

    def addBook(self, book: Book) -> bool:
        # Sequence (Librarian): validateInput + INSERT Book
        if not self._require_role({UserRole.LIBRARIAN}):
            return False
        if book is None:
            self.last_message = "Book data is required."
            return False
        if not book.title or not book.author or not book.isbn or not book.genre or not book.location:
            self.last_message = "Title, author, ISBN, genre, and location are required."
            return False
        if book.totalCopies is None or book.totalCopies <= 0:
            self.last_message = "totalCopies must be greater than zero."
            return False
        if book.availableCopies is None:
            book.availableCopies = book.totalCopies
        if book.availableCopies != book.totalCopies:
            self.last_message = "availableCopies must equal totalCopies for a new book."
            return False

        existing = Book.query.filter_by(isbn=book.isbn).first()
        if existing is not None:
            self.last_message = "ISBN already exists."
            return False

        if not book.bookID:
            book.bookID = uuid4().hex[:12]

        db.session.add(book)
        db.session.commit()
        self.last_message = f"Book added successfully with ID: {book.bookID}."
        return True

    def updateBook(self, bookID: str, updatedInfo: Book) -> bool:
        if not self._require_role({UserRole.LIBRARIAN}):
            return False

        book = Book.query.filter_by(bookID=bookID).first()
        if book is None:
            self.last_message = "Book not found."
            return False

        if updatedInfo.title:
            book.title = updatedInfo.title
        if updatedInfo.author:
            book.author = updatedInfo.author
        if updatedInfo.genre:
            book.genre = updatedInfo.genre
        if updatedInfo.location:
            book.location = updatedInfo.location

        if updatedInfo.isbn and updatedInfo.isbn != book.isbn:
            duplicate = Book.query.filter_by(isbn=updatedInfo.isbn).first()
            if duplicate is not None:
                self.last_message = "ISBN already exists."
                return False
            book.isbn = updatedInfo.isbn

        if updatedInfo.totalCopies is not None:
            if updatedInfo.totalCopies < 0:
                self.last_message = "totalCopies cannot be negative."
                return False
            borrowed_count = book.totalCopies - book.availableCopies
            if updatedInfo.totalCopies < borrowed_count:
                self.last_message = "totalCopies cannot be less than currently borrowed copies."
                return False
            book.totalCopies = updatedInfo.totalCopies
            book.availableCopies = updatedInfo.totalCopies - borrowed_count

        db.session.commit()
        self.last_message = "Book updated successfully."
        return True

    def removeBook(self, bookID: str) -> bool:
        if not self._require_role({UserRole.LIBRARIAN}):
            return False

        book = Book.query.filter_by(bookID=bookID).first()
        if book is None:
            self.last_message = "Book not found."
            return False

        if book.availableCopies < book.totalCopies:
            self.last_message = "Cannot remove a book while it is currently borrowed."
            return False

        db.session.delete(book)
        db.session.commit()
        self.last_message = "Book removed successfully."
        return True
