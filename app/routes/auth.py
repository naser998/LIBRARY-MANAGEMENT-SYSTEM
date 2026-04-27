from __future__ import annotations

from functools import wraps

from flask import Blueprint, flash, redirect, render_template, request, session, url_for

from app.services.auth_service import AuthService
from app.services.member_service import MemberService

auth_bp = Blueprint("auth", __name__)


def _redirect_by_role():
    role = session.get("role")
    if role == "MEMBER":
        return redirect(url_for("member.member_dashboard"))
    if role == "LIBRARIAN":
        return redirect(url_for("librarian.librarian_dashboard"))
    if role == "ADMINISTRATOR":
        return redirect(url_for("admin.admin_dashboard"))
    return redirect(url_for("auth.login"))


def guest_only(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if session.get("user_id"):
            return _redirect_by_role()
        return view(*args, **kwargs)

    return wrapped


@auth_bp.route("/", methods=["GET"])
def index():
    return _redirect_by_role()


@auth_bp.route("/login", methods=["GET", "POST"])
@guest_only
def login():
    auth_service = AuthService()
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()
        success = auth_service.login(username, password)

        if success:
            flash(auth_service.last_message, "success")
            return _redirect_by_role()

        flash(auth_service.last_message, "danger")
        return render_template("auth/login.html", username=username)

    return render_template("auth/login.html")


@auth_bp.route("/logout", methods=["POST"])
def logout():
    auth_service = AuthService()
    auth_service.logout()
    flash(auth_service.last_message, "info")
    return redirect(url_for("auth.login"))


@auth_bp.route("/availability", methods=["GET"])
def availability():
    member_service = MemberService()
    query = request.args.get("q", "").strip()
    books = member_service.searchBooks(query) if query else []
    return render_template("availability.html", books=books, query=query)
