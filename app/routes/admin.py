from __future__ import annotations

from functools import wraps

from flask import Blueprint, flash, redirect, render_template, request, session, url_for

from app.models import User, UserRole
from app.services.report_service import ReportService
from app.services.user_service import UserService

admin_bp = Blueprint("admin", __name__)


def admin_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if session.get("user_id") is None:
            flash("Please log in first.", "warning")
            return redirect(url_for("auth.login"))
        if session.get("role") != "ADMINISTRATOR":
            flash("Administrator access required.", "danger")
            return redirect(url_for("auth.index"))
        return view(*args, **kwargs)

    return wrapped


@admin_bp.route("/", methods=["GET"])
@admin_required
def admin_dashboard():
    return render_template("admin/users.html")


@admin_bp.route("/users", methods=["GET", "POST"])
@admin_required
def user_management():
    user_service = UserService()

    if request.method == "POST":
        action = request.form.get("action", "").strip().lower()
        user_id = request.form.get("userID", "").strip()
        role_value = request.form.get("role", "").strip().upper()
        role = UserRole(role_value) if role_value in {"MEMBER", "LIBRARIAN", "ADMINISTRATOR"} else None

        data = User(
            userID=user_id,
            username=request.form.get("username", "").strip(),
            passwordHash=request.form.get("password", "").strip(),
            email=request.form.get("email", "").strip(),
            role=role,
        )

        success = user_service.manageUser(user_id, action, data)
        flash(user_service.last_message, "success" if success else "danger")
        return redirect(url_for("admin.user_management"))

    return render_template("admin/users.html")


@admin_bp.route("/reports", methods=["GET", "POST"])
@admin_required
def reports():
    report_service = ReportService()
    report_html = ""
    report_type = "overdue"

    if request.method == "POST":
        # Sequence (Admin): Step 3 -> generateReport(reportType, filters)
        report_type = request.form.get("reportType", "").strip().lower()
        filters = {
            "startDate": request.form.get("startDate", "").strip(),
            "endDate": request.form.get("endDate", "").strip(),
        }
        report_html = report_service.generateReport(report_type, filters)
        flash(report_service.last_message, "info")

    return render_template("admin/reports.html", report_html=report_html, report_type=report_type)


@admin_bp.route("/settings", methods=["GET", "POST"])
@admin_required
def settings():
    user_service = UserService()
    if request.method == "POST":
        key = request.form.get("key", "").strip()
        value = request.form.get("value", "").strip()
        success = user_service.configureSetting(key, value)
        flash(user_service.last_message, "success" if success else "danger")
        return redirect(url_for("admin.settings"))
    return render_template("admin/settings.html")
