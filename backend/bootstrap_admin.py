import argparse

import mysql.connector
from mysql.connector import errorcode
from werkzeug.security import generate_password_hash

from app import create_auth_user, fetch_admin_by_id, fetch_auth_user, get_connection


def main():
    parser = argparse.ArgumentParser(description="Seed or update the first CESOMS admin login.")
    parser.add_argument("--admin-id", required=True)
    parser.add_argument("--first-name", required=True)
    parser.add_argument("--last-name", required=True)
    parser.add_argument("--email", required=True)
    parser.add_argument("--department", required=True)
    parser.add_argument("--password", required=True)
    args = parser.parse_args()

    if len(args.password) < 8:
        raise SystemExit("Password must be at least 8 characters.")

    conn = None
    cursor = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        admin = fetch_admin_by_id(cursor, args.admin_id)

        if admin:
            cursor.execute(
                """
                UPDATE ADMINISTRATOR
                SET FirstName = %s,
                    LastName = %s,
                    Email = %s,
                    Department = %s,
                    AdminStatus = 'Active'
                WHERE AdminID = %s
                """,
                (
                    args.first_name,
                    args.last_name,
                    args.email,
                    args.department,
                    args.admin_id,
                ),
            )
        else:
            cursor.execute(
                """
                INSERT INTO ADMINISTRATOR (
                    AdminID,
                    FirstName,
                    LastName,
                    Email,
                    Department,
                    AdminStatus
                )
                VALUES (%s, %s, %s, %s, %s, 'Active')
                """,
                (
                    args.admin_id,
                    args.first_name,
                    args.last_name,
                    args.email,
                    args.department,
                ),
            )

        auth_user = fetch_auth_user(cursor, "admin", args.admin_id)
        if auth_user:
            cursor.execute(
                """
                UPDATE APP_USER
                SET PasswordHash = %s,
                    LastPasswordChangedAt = NOW()
                WHERE AccountType = 'admin'
                  AND AccountRefID = %s
                """,
                (
                    generate_password_hash(args.password),
                    args.admin_id,
                ),
            )
            print(f"Updated login for admin {args.admin_id}.")
        else:
            create_auth_user(cursor, "admin", args.admin_id, args.password)
            print(f"Created login for admin {args.admin_id}.")

        conn.commit()
        print("Bootstrap complete.")
    except mysql.connector.Error as exc:
        if conn:
            conn.rollback()
        if exc.errno == errorcode.ER_DUP_ENTRY:
            raise SystemExit("A conflicting admin record already exists.")
        raise SystemExit(f"Database error: {exc}")
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


if __name__ == "__main__":
    main()
