from __future__ import annotations

from functools import wraps

from flask import Blueprint, flash, redirect, render_template, request, session, url_for

from app.models import Book
from app.services.book_service import BookService
from app.services.librarian_service import LibrarianService
from app.services.loan_service import LoanService

librarian_bp = Blueprint("librarian", __name__)


def librarian_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if session.get("user_id") is None:
            flash("Please log in first.", "warning")
            return redirect(url_for("auth.login"))
        if session.get("role") != "LIBRARIAN":
            flash("Librarian access required.", "danger")
            return redirect(url_for("auth.index"))
        return view(*args, **kwargs)

    return wrapped


@librarian_bp.route("/", methods=["GET"])
@librarian_required
def librarian_dashboard():
    book_service = BookService()
    books = book_service.listBooks()
    librarian_service = LibrarianService()
    pending_deliveries = librarian_service.getPendingDeliveries()
    return render_template("librarian/books.html", books=books, pending_deliveries_count=len(pending_deliveries))


@librarian_bp.route("/books/add", methods=["POST"])
@librarian_required
def add_book():
    # Sequence (Librarian): Step 3 -> addBook(newBook)
    book = Book(
        bookID=request.form.get("bookID", "").strip() or None,
        title=request.form.get("title", "").strip(),
        author=request.form.get("author", "").strip(),
        isbn=request.form.get("isbn", "").strip(),
        genre=request.form.get("genre", "").strip(),
        location=request.form.get("location", "").strip(),
        totalCopies=int(request.form.get("totalCopies", "0")),
        availableCopies=int(request.form.get("totalCopies", "0")),
    )
    book_service = BookService()
    success = book_service.addBook(book)
    flash(book_service.last_message, "success" if success else "danger")
    return redirect(url_for("librarian.librarian_dashboard"))


@librarian_bp.route("/books/update", methods=["POST"])
@librarian_required
def update_book():
    book_id = request.form.get("bookID", "").strip()

    # Keep values optional in update object; only provided fields will be applied in service.
    updated = Book(
        title=request.form.get("title") or None,
        author=request.form.get("author") or None,
        isbn=request.form.get("isbn") or None,
        genre=request.form.get("genre") or None,
        location=request.form.get("location") or None,
        totalCopies=int(request.form["totalCopies"]) if request.form.get("totalCopies") else None,
    )
    book_service = BookService()
    success = book_service.updateBook(book_id, updated)
    flash(book_service.last_message, "success" if success else "danger")
    return redirect(url_for("librarian.librarian_dashboard"))


@librarian_bp.route("/books/delete", methods=["POST"])
@librarian_required
def delete_book():
    book_id = request.form.get("bookID", "").strip()
    book_service = BookService()
    success = book_service.removeBook(book_id)
    flash(book_service.last_message, "success" if success else "danger")
    return redirect(url_for("librarian.librarian_dashboard"))


@librarian_bp.route("/loans/process-return", methods=["POST"])
@librarian_required
def process_return():
    loan_id = request.form.get("loanID", "").strip()
    loan_service = LoanService()
    success = loan_service.processReturn(loan_id)
    flash(loan_service.last_message, "success" if success else "danger")
    return redirect(url_for("librarian.librarian_dashboard"))


@librarian_bp.route("/loans/notify-overdue", methods=["POST"])
@librarian_required
def notify_overdue():
    loan_service = LoanService()
    loan_service.notifyOverdue()
    flash(loan_service.last_message, "info")
    return redirect(url_for("librarian.librarian_dashboard"))


@librarian_bp.route("/deliveries", methods=["GET"])
@librarian_required
def deliveries():
    librarian_service = LibrarianService()
    deliveries_list = librarian_service.getPendingDeliveries()
    return render_template("librarian/deliveries.html", deliveries=deliveries_list)


@librarian_bp.route("/deliveries/<int:delivery_id>/mark-delivered", methods=["POST"])
@librarian_required
def mark_delivered(delivery_id: int):
    librarian_service = LibrarianService()
    notes = request.form.get("notes", "").strip()
    try:
        librarian_service.markDelivered(delivery_id, session.get("user_id", ""), notes)
        flash(librarian_service.last_message, "success")
    except Exception as exc:
        flash(str(exc), "danger")
    return redirect(url_for("librarian.deliveries"))
