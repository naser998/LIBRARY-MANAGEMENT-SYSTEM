from __future__ import annotations

from datetime import date
from functools import wraps

from flask import Blueprint, flash, redirect, render_template, request, session, url_for

from app.services.member_service import DeliveryError, DuplicateReservationError, MemberService

member_bp = Blueprint("member", __name__)


def member_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if session.get("user_id") is None:
            flash("Please log in first.", "warning")
            return redirect(url_for("auth.login"))
        if session.get("role") != "MEMBER":
            flash("Member access required.", "danger")
            return redirect(url_for("auth.index"))
        return view(*args, **kwargs)

    return wrapped


@member_bp.route("/", methods=["GET"])
@member_required
def member_dashboard():
    member_service = MemberService()
    loans = member_service.viewMyLoans()
    active_loans = [loan for loan in loans if loan.status.value == "ACTIVE"]
    overdue_loans = [loan for loan in loans if loan.status.value == "OVERDUE"]
    return render_template(
        "member/dashboard.html",
        active_loans=len(active_loans),
        overdue_count=len(overdue_loans),
    )


@member_bp.route("/search", methods=["GET", "POST"])
@member_required
def search():
    member_service = MemberService()
    query = ""
    books = []

    if request.method == "POST":
        # Sequence (Member): Step 2 -> searchBooks(query)
        query = request.form.get("query", "").strip()
        books = member_service.searchBooks(query)
        flash(member_service.last_message, "info")

    return render_template("member/search.html", books=books, query=query)


@member_bp.route("/borrow", methods=["POST"])
@member_required
def borrow_book():
    member_service = MemberService()
    book_id = request.form.get("bookID", "").strip()

    # Sequence (Member): Step 3 -> borrowBook(bookID)
    loan = member_service.borrowBook(book_id)
    if loan is None:
        flash(member_service.last_message, "danger")
    else:
        flash(member_service.last_message, "success")
    return redirect(url_for("member.search"))


@member_bp.route("/loans", methods=["GET"])
@member_required
def my_loans():
    member_service = MemberService()
    loans = member_service.viewMyLoans()
    reservations = member_service.getActiveReservations()
    return render_template(
        "member/my_loans.html",
        loans=loans,
        reservations=reservations,
        today=date.today(),
    )


@member_bp.route("/return", methods=["POST"])
@member_required
def return_book():
    member_service = MemberService()
    loan_id = request.form.get("loanID", "").strip()
    success = member_service.returnBook(loan_id)
    flash(member_service.last_message, "success" if success else "danger")
    return redirect(url_for("member.my_loans"))


@member_bp.route("/books/<string:book_id>", methods=["GET"])
@member_required
def book_detail(book_id: str):
    member_service = MemberService()
    book = member_service.getBookById(book_id)
    if book is None:
        flash("Book not found.", "danger")
        return redirect(url_for("member.search"))
    has_active_loan = any(
        loan.bookID == book.bookID and loan.status.value in {"ACTIVE", "OVERDUE"}
        for loan in member_service.viewMyLoans()
    )
    has_active_reservation = any(r.book_id == book.bookID for r in member_service.getActiveReservations())
    return render_template(
        "member/book_detail.html",
        book=book,
        has_active_loan=has_active_loan,
        has_active_reservation=has_active_reservation,
    )


@member_bp.route("/books/<string:book_id>/reserve", methods=["POST"])
@member_required
def reserve_book(book_id: str):
    member_service = MemberService()
    try:
        member_service.reserveBook(session["user_id"], book_id)
        flash(member_service.last_message, "success")
    except DuplicateReservationError as exc:
        flash(str(exc), "danger")
    except Exception as exc:
        flash(str(exc), "danger")
    return redirect(url_for("member.book_detail", book_id=book_id))


@member_bp.route("/reservations/<int:reservation_id>/cancel", methods=["POST"])
@member_required
def cancel_reservation(reservation_id: int):
    member_service = MemberService()
    success = member_service.cancelReservation(reservation_id, session["user_id"])
    flash(member_service.last_message, "success" if success else "danger")
    return redirect(url_for("member.my_loans"))


@member_bp.route("/loans/<string:loan_id>/delivery", methods=["GET"])
@member_required
def delivery_form(loan_id: str):
    member_service = MemberService()
    loan = next((ln for ln in member_service.viewMyLoans() if ln.loanID == loan_id), None)
    if loan is None:
        flash("Loan not found.", "danger")
        return redirect(url_for("member.my_loans"))
    return render_template("member/delivery_form.html", loan=loan)


@member_bp.route("/loans/<string:loan_id>/delivery", methods=["POST"])
@member_required
def request_delivery(loan_id: str):
    member_service = MemberService()
    address = request.form.get("delivery_address", "").strip()
    try:
        member_service.requestDelivery(loan_id, session["user_id"], address)
        flash(member_service.last_message, "success")
    except DeliveryError as exc:
        flash(str(exc), "danger")
    except Exception as exc:
        flash(str(exc), "danger")
    return redirect(url_for("member.my_loans"))


@member_bp.route("/delivery/<int:delivery_id>/cancel", methods=["POST"])
@member_required
def cancel_delivery(delivery_id: int):
    member_service = MemberService()
    success = member_service.cancelDelivery(delivery_id, session["user_id"])
    flash(member_service.last_message, "success" if success else "danger")
    return redirect(url_for("member.my_loans"))
