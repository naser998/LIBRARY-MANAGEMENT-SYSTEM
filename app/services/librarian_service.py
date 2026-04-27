from __future__ import annotations

from datetime import datetime

from flask import session

from app import db
from app.models import DeliveryRequest, UserRole


class LibrarianService:
    def __init__(self) -> None:
        self.last_message: str = ""

    def _require_librarian_or_admin(self, librarianId: str | None = None) -> bool:
        if "user_id" not in session or "role" not in session:
            self.last_message = "Please log in first."
            return False
        if session["role"] not in {UserRole.LIBRARIAN.value, UserRole.ADMINISTRATOR.value}:
            self.last_message = "Librarian or administrator role required."
            return False
        if librarianId is not None and str(librarianId) != str(session["user_id"]):
            self.last_message = "Invalid librarian context."
            return False
        return True

    def getPendingDeliveries(self) -> list[DeliveryRequest]:
        if not self._require_librarian_or_admin():
            return []
        deliveries = (
            DeliveryRequest.query.filter_by(status="pending")
            .order_by(DeliveryRequest.requested_at.asc())
            .all()
        )
        self.last_message = f"Found {len(deliveries)} pending delivery request(s)."
        return deliveries

    def markDelivered(self, deliveryId: int, librarianId: int, notes: str = "") -> DeliveryRequest:
        if not self._require_librarian_or_admin(str(librarianId)):
            raise PermissionError(self.last_message)
        delivery = DeliveryRequest.query.filter_by(id=deliveryId).first()
        if delivery is None:
            raise ValueError("Delivery request not found.")
        if delivery.status != "pending":
            raise ValueError("Only pending requests can be marked delivered.")
        delivery.status = "delivered"
        delivery.notes = (notes or "").strip() or None
        if delivery.requested_at is None:
            delivery.requested_at = datetime.utcnow()
        db.session.commit()
        self.last_message = "Delivery marked as delivered."
        return delivery
