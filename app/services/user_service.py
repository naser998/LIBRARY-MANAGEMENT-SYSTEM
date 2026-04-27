from __future__ import annotations

from flask import session
from werkzeug.security import generate_password_hash

from app import db
from app.models import Administrator, Librarian, Member, User, UserRole


class UserService:
    _settings: dict[str, object] = {}

    def __init__(self) -> None:
        self.last_message: str = ""

    def _require_admin(self) -> bool:
        if "user_id" not in session or "role" not in session:
            self.last_message = "Please log in first."
            return False
        if UserRole(session["role"]) != UserRole.ADMINISTRATOR:
            self.last_message = "Administrator role required."
            return False
        return True

    def manageUser(self, userID: str, action: str, data: User) -> bool:
        if not self._require_admin():
            return False

        act = (action or "").strip().lower()
        if act not in {"create", "update", "delete"}:
            self.last_message = "Action must be one of: create, update, delete."
            return False

        if act in {"create", "update"} and data is None:
            self.last_message = "User data is required for create/update."
            return False

        if act == "create":
            if User.query.filter_by(userID=data.userID).first():
                self.last_message = "User ID already exists."
                return False
            if User.query.filter_by(username=data.username).first():
                self.last_message = "Username already exists."
                return False
            if User.query.filter_by(email=data.email).first():
                self.last_message = "Email already exists."
                return False
            if not data.passwordHash:
                self.last_message = "Password is required."
                return False

            password_hash = data.passwordHash
            if not password_hash.startswith(("pbkdf2:", "scrypt:")):
                password_hash = generate_password_hash(password_hash)

            if data.role == UserRole.MEMBER:
                new_user = Member(
                    userID=data.userID,
                    username=data.username,
                    passwordHash=password_hash,
                    email=data.email,
                    role=UserRole.MEMBER,
                )
            elif data.role == UserRole.LIBRARIAN:
                new_user = Librarian(
                    userID=data.userID,
                    username=data.username,
                    passwordHash=password_hash,
                    email=data.email,
                    role=UserRole.LIBRARIAN,
                )
            elif data.role == UserRole.ADMINISTRATOR:
                new_user = Administrator(
                    userID=data.userID,
                    username=data.username,
                    passwordHash=password_hash,
                    email=data.email,
                    role=UserRole.ADMINISTRATOR,
                )
            else:
                self.last_message = "Invalid role."
                return False

            db.session.add(new_user)
            db.session.commit()
            self.last_message = "User created successfully."
            return True

        if act == "update":
            user = User.query.filter_by(userID=userID).first()
            if user is None:
                self.last_message = "User not found."
                return False

            if data.username and data.username != user.username:
                if User.query.filter_by(username=data.username).first():
                    self.last_message = "Username already exists."
                    return False
                user.username = data.username
            if data.email and data.email != user.email:
                if User.query.filter_by(email=data.email).first():
                    self.last_message = "Email already exists."
                    return False
                user.email = data.email
            if data.passwordHash:
                user.passwordHash = (
                    data.passwordHash
                    if data.passwordHash.startswith(("pbkdf2:", "scrypt:"))
                    else generate_password_hash(data.passwordHash)
                )

            db.session.commit()
            self.last_message = "User updated successfully."
            return True

        user = User.query.filter_by(userID=userID).first()
        if user is None:
            self.last_message = "User not found."
            return False
        if user.userID == session.get("user_id"):
            self.last_message = "Administrator cannot delete their own active account."
            return False

        db.session.delete(user)
        db.session.commit()
        self.last_message = "User deleted successfully."
        return True

    def configureSetting(self, key: str, value: object) -> bool:
        if not self._require_admin():
            return False
        k = (key or "").strip()
        if not k:
            self.last_message = "Setting key cannot be empty."
            return False
        self._settings[k] = value
        self.last_message = f"Setting '{k}' updated successfully."
        return True
