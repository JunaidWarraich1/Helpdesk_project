"""CLI script to seed an initial administrator into the database."""

import argparse
import sys
from app.core.security import hash_password
from app.db.base import Base
from app.db.session import SessionLocal, engine
from app.models.user import User, UserRole


def seed_admin(email: str, password: str, full_name: str) -> None:
    # Ensure tables are created
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        existing = db.query(User).filter(User.email == email).first()
        if existing:
            if existing.role != UserRole.ADMIN:
                existing.role = UserRole.ADMIN
                db.commit()
                print(f"[SUCCESS] Existing user '{email}' promoted to ADMIN.")
            else:
                print(f"[INFO] Admin user '{email}' already exists.")
            return

        admin_user = User(
            email=email,
            full_name=full_name,
            hashed_password=hash_password(password),
            role=UserRole.ADMIN,
        )
        db.add(admin_user)
        db.commit()
        db.refresh(admin_user)
        print(f"[SUCCESS] Admin user '{email}' (ID: {admin_user.id}) created successfully.")
    except Exception as exc:
        db.rollback()
        print(f"[ERROR] Failed to seed admin: {exc}", file=sys.stderr)
        sys.exit(1)
    finally:
        db.close()


def main():
    parser = argparse.ArgumentParser(description="Seed initial Administrator into the system.")
    parser.add_argument(
        "--email",
        default="admin@company.com",
        help="Email address of the admin (default: admin@company.com)",
    )
    parser.add_argument(
        "--password",
        default="admin123456",
        help="Password for the admin account (default: admin123456)",
    )
    parser.add_argument(
        "--name",
        default="System Administrator",
        help="Full name of the admin (default: System Administrator)",
    )

    args = parser.parse_args()
    seed_admin(email=args.email, password=args.password, full_name=args.name)


if __name__ == "__main__":
    main()
