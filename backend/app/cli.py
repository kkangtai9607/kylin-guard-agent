from __future__ import annotations

import argparse
import getpass
import os

from sqlalchemy import select

from backend.app.audit.service import write_audit
from backend.app.auth.security import hash_password
from backend.app.db.models import Role, User
from backend.app.db.session import SessionLocal


def create_admin(username: str, password: str) -> None:
    with SessionLocal() as db:
        if db.scalar(select(User).where(User.username == username)) is not None:
            raise ValueError("user already exists")
        roles: list[Role] = []
        for name in ("admin", "operator", "approver", "auditor"):
            role = db.scalar(select(Role).where(Role.name == name)) or Role(name=name)
            db.add(role)
            roles.append(role)
        user = User(username=username, password_hash=hash_password(password), roles=roles)
        db.add(user)
        db.flush()
        write_audit(db, "ADMIN_CREATED", {"username": username}, actor_id=user.id)
        db.commit()


def main() -> None:
    parser = argparse.ArgumentParser(description="KylinGuard administration CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)
    create = subparsers.add_parser("create-admin")
    create.add_argument("--username", required=True)
    create.add_argument("--password-env", default="KYLIN_GUARD_BOOTSTRAP_PASSWORD")
    args = parser.parse_args()
    if args.command == "create-admin":
        password = os.getenv(args.password_env) or getpass.getpass("Password: ")
        create_admin(args.username, password)


if __name__ == "__main__":
    main()
