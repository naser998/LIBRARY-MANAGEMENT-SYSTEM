from __future__ import annotations

from flask import session
from werkzeug.security import check_password_hash

from app.models import User


class AuthService:
    def __init__(self) -> None:
        self.last_message: str = ""

    def authenticateUser(self, username: str, password: str):
        # Sequence step: Presentation -> BLL authenticateUser(username, password)
        user = User.query.filter_by(username=username).first()
        if user is None or not check_password_hash(user.passwordHash, password):
            self.last_message = "Invalid username or password."
            return None
        return user

    def login(self, username: str, password: str) -> bool:
        # Class method signature: login(username, password): boolean
        user = self.authenticateUser(username, password)
        if user is None:
            return False

        # Sequence step: return success + session token
        session["user_id"] = user.userID
        session["username"] = user.username
        session["role"] = user.role.value
        self.last_message = "Login successful."
        return True

    def logout(self) -> None:
        # Class method signature: logout()
        session.clear()
        self.last_message = "Logged out successfully."
