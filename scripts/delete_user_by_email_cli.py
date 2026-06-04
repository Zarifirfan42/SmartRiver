"""One-off CLI: delete a user by email from SQLite."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.db.repository import delete_user_by_email, get_user_by_email, _sqlite_conn


def main() -> int:
    email = (sys.argv[1] if len(sys.argv) > 1 else "").strip()
    if not email:
        print("Usage: python scripts/delete_user_by_email_cli.py <email>")
        return 1
    before = get_user_by_email(email)
    if not before:
        print(f"No user found for: {email}")
        return 0
    print(f"Found: id={before.get('id')} role={before.get('role')} email={before.get('email')}")
    if delete_user_by_email(email):
        print(f"Deleted user and OTP rows for: {email}")
    else:
        print("Delete returned False")
        return 1
    if get_user_by_email(email):
        print("ERROR: user still exists")
        return 1
    with _sqlite_conn() as conn:
        rows = conn.execute("SELECT id, email, role FROM users ORDER BY id").fetchall()
    print("Remaining users:")
    for r in rows:
        print(f"  {dict(r)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
