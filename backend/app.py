import os
from flask import Flask, flash, jsonify, redirect, render_template, request, session, url_for
import mysql.connector
from mysql.connector import errorcode
from datetime import date, datetime
from werkzeug.security import check_password_hash, generate_password_hash

BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(BACKEND_DIR)
FRONTEND_DIR = os.path.join(PROJECT_ROOT, "frontend")
TEMPLATES_DIR = os.path.join(FRONTEND_DIR, "templates")
STATIC_DIR = os.path.join(FRONTEND_DIR, "static")
DB_DIR = os.path.join(PROJECT_ROOT, "db")

app = Flask(__name__, template_folder=TEMPLATES_DIR, static_folder=STATIC_DIR)
app.config["SECRET_KEY"] = os.environ.get("FLASK_SECRET_KEY", "cesoms-dev-secret")

def normalize_config_key(key):
    normalized = key.strip().lower()
    if normalized.startswith("db_"):
        normalized = normalized[3:]
    return normalized


def parse_config_value(value):
    return value.strip().strip('"').strip("'")


def load_db_config():
    config_path = os.environ.get("DB_CONFIG_FILE")
    candidate_paths = (
        [config_path]
        if config_path
        else [
            os.path.join(DB_DIR, ".DB_info.txt"),
            os.path.join(DB_DIR, "DB_info.txt"),
            os.path.join(BACKEND_DIR, ".DB_info.txt"),
            os.path.join(BACKEND_DIR, "DB_info.txt"),
            ".DB_info.txt",
            "DB_info.txt",
        ]
    )
    parsed = {}
    used_path = ""

    for path in candidate_paths:
        if not path or not os.path.exists(path):
            continue
        used_path = path
        with open(path, encoding="utf-8") as config_file:
            for raw_line in config_file:
                line = raw_line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, value = line.split("=", 1)
                parsed[normalize_config_key(key)] = parse_config_value(value)
        break

    if not used_path:
        raise RuntimeError(
            "Database config file not found. Create .DB_info.txt or set DB_CONFIG_FILE."
        )

    required_keys = ("host", "user", "password", "database")
    missing_keys = [key for key in required_keys if not parsed.get(key)]
    if missing_keys:
        raise RuntimeError(
            f"Missing required DB keys in {used_path}: {', '.join(missing_keys)}"
        )

    config = {
        "host": parsed["host"],
        "user": parsed["user"],
        "password": parsed["password"],
        "database": parsed["database"],
    }

    if parsed.get("port"):
        try:
            config["port"] = int(parsed["port"])
        except ValueError as exc:
            raise RuntimeError(f"Invalid DB port in {used_path}: {parsed['port']}") from exc

    return config


DB_CONFIG = load_db_config()


def get_connection():
    return mysql.connector.connect(**DB_CONFIG)


def normalize_student_id(raw_student_id):
    candidate = (raw_student_id or "").strip()
    if not candidate or not candidate.isdigit():
        return None

    normalized = str(int(candidate))
    if normalized == "0":
        return None

    return normalized


def ensure_auth_schema():
    conn = None
    cursor = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS APP_USER (
                UserID INT AUTO_INCREMENT PRIMARY KEY,
                AccountType VARCHAR(20) NOT NULL,
                AccountRefID VARCHAR(50) NOT NULL,
                PasswordHash VARCHAR(255) NOT NULL,
                CreatedAt DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                LastPasswordChangedAt DATETIME NULL,
                UNIQUE KEY uq_app_user_account (AccountType, AccountRefID)
            )
        """)
        conn.commit()
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


ensure_auth_schema()


def serialize_value(value):
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    return value


def fetch_all_dict(cursor, query, params=None):
    cursor.execute(query, params or ())
    columns = [col[0] for col in cursor.description]
    rows = cursor.fetchall()
    results = []

    for row in rows:
        item = {}
        for index, column in enumerate(columns):
            item[column] = serialize_value(row[index])
        results.append(item)

    return results


def safe_fetch(cursor, query, params=None):
    try:
        return fetch_all_dict(cursor, query, params)
    except mysql.connector.Error:
        return []


def fetch_student_by_id(cursor, student_id):
    rows = fetch_all_dict(cursor, """
        SELECT
            StudentID AS studentId,
            FirstName AS firstName,
            LastName AS lastName,
            Email AS email,
            ClassYear AS classYear,
            Major AS major,
            AccountStatus AS accountStatus
        FROM STUDENT
        WHERE StudentID = %s
        LIMIT 1
    """, (student_id,))
    return rows[0] if rows else None


def fetch_student_by_credentials(cursor, student_id, email):
    rows = fetch_all_dict(cursor, """
        SELECT
            StudentID AS studentId,
            FirstName AS firstName,
            LastName AS lastName,
            Email AS email,
            ClassYear AS classYear,
            Major AS major,
            AccountStatus AS accountStatus
        FROM STUDENT
        WHERE StudentID = %s
          AND LOWER(Email) = LOWER(%s)
        LIMIT 1
    """, (student_id, email))
    return rows[0] if rows else None


def fetch_auth_user(cursor, account_type, account_ref_id):
    rows = safe_fetch(cursor, """
        SELECT
            UserID AS userId,
            AccountType AS accountType,
            AccountRefID AS accountRefId,
            PasswordHash AS passwordHash,
            CreatedAt AS createdAt,
            LastPasswordChangedAt AS lastPasswordChangedAt
        FROM APP_USER
        WHERE AccountType = %s
          AND AccountRefID = %s
        LIMIT 1
    """, (account_type, account_ref_id))
    return rows[0] if rows else None


def create_auth_user(cursor, account_type, account_ref_id, password):
    now = datetime.now()
    cursor.execute("""
        INSERT INTO APP_USER (
            AccountType,
            AccountRefID,
            PasswordHash,
            CreatedAt,
            LastPasswordChangedAt
        )
        VALUES (%s, %s, %s, %s, %s)
    """, (
        account_type,
        account_ref_id,
        generate_password_hash(password),
        now,
        now,
    ))


def delete_auth_user(cursor, account_type, account_ref_id):
    cursor.execute("""
        DELETE FROM APP_USER
        WHERE AccountType = %s
          AND (
              AccountRefID = %s
              OR CAST(AccountRefID AS UNSIGNED) = %s
          )
    """, (account_type, str(account_ref_id), int(account_ref_id)))


def update_auth_password(cursor, account_type, account_ref_id, password):
    cursor.execute("""
        UPDATE APP_USER
        SET PasswordHash = %s,
            LastPasswordChangedAt = %s
        WHERE AccountType = %s
          AND AccountRefID = %s
    """, (
        generate_password_hash(password),
        datetime.now(),
        account_type,
        account_ref_id,
    ))


def count_admin_auth_users(cursor):
    rows = safe_fetch(cursor, """
        SELECT COUNT(*) AS total
        FROM APP_USER
        WHERE AccountType = 'admin'
    """)
    return rows[0]["total"] if rows else 0


def fetch_admin_by_id(cursor, admin_id):
    rows = fetch_all_dict(cursor, """
        SELECT
            AdminID AS adminId,
            FirstName AS firstName,
            LastName AS lastName,
            Email AS email,
            Department AS department,
            AdminStatus AS adminStatus
        FROM ADMINISTRATOR
        WHERE AdminID = %s
        LIMIT 1
    """, (admin_id,))
    return rows[0] if rows else None


def fetch_admin_by_credentials(cursor, admin_id, email):
    rows = fetch_all_dict(cursor, """
        SELECT
            AdminID AS adminId,
            FirstName AS firstName,
            LastName AS lastName,
            Email AS email,
            Department AS department,
            AdminStatus AS adminStatus
        FROM ADMINISTRATOR
        WHERE AdminID = %s
          AND LOWER(Email) = LOWER(%s)
        LIMIT 1
    """, (admin_id, email))
    return rows[0] if rows else None


def fetch_active_officer_roles(cursor, student_id):
    return fetch_all_dict(cursor, """
        SELECT
            oo.StudentID AS studentId,
            oo.OrgID AS orgId,
            oo.StartDate AS startDate,
            oo.RoleTitle AS roleTitle,
            oo.EndDate AS endDate,
            o.OrgName AS orgName
        FROM ORGANIZATION_OFFICER oo
        JOIN ORGANIZATION o ON o.OrgID = oo.OrgID
        WHERE oo.StudentID = %s
          AND (oo.EndDate IS NULL OR oo.EndDate >= CURDATE())
        ORDER BY oo.StartDate DESC, oo.OrgID
    """, (student_id,))


def fetch_student_signups(cursor, student_id):
    return fetch_all_dict(cursor, """
        SELECT
            r.EventID AS eventId,
            r.RegisteredAt AS registeredAt,
            r.RegistrationStatus AS registrationStatus,
            e.Title AS eventTitle,
            e.Description AS eventDescription,
            e.StartDateTime AS startDateTime,
            e.EndDateTime AS endDateTime,
            e.EventStatus AS eventStatus,
            o.OrgName AS organizationName,
            l.LocationName AS locationName,
            l.IsVirtual AS isVirtual
        FROM REGISTRATION r
        JOIN EVENT e ON e.EventID = r.EventID
        LEFT JOIN ORGANIZATION o ON o.OrgID = e.OrgID
        LEFT JOIN LOCATION l ON l.LocationID = e.LocationID
        WHERE r.StudentID = %s
        ORDER BY e.StartDateTime DESC, r.RegisteredAt DESC
    """, (student_id,))


def fetch_registration_record(cursor, student_id, event_id):
    rows = fetch_all_dict(cursor, """
        SELECT
            StudentID AS studentId,
            EventID AS eventId,
            RegisteredAt AS registeredAt,
            RegistrationStatus AS registrationStatus
        FROM REGISTRATION
        WHERE StudentID = %s
          AND EventID = %s
        LIMIT 1
    """, (student_id, event_id))
    return rows[0] if rows else None


def fetch_event_for_registration(cursor, event_id):
    rows = fetch_all_dict(cursor, """
        SELECT
            EventID AS eventId,
            Title AS title,
            Capacity AS capacity,
            StartDateTime AS startDateTime,
            EndDateTime AS endDateTime,
            EventStatus AS eventStatus
        FROM EVENT
        WHERE EventID = %s
        LIMIT 1
    """, (event_id,))
    return rows[0] if rows else None


def count_registered_students(cursor, event_id):
    rows = fetch_all_dict(cursor, """
        SELECT COUNT(*) AS total
        FROM REGISTRATION
        WHERE EventID = %s
          AND RegistrationStatus = 'Registered'
    """, (event_id,))
    return rows[0]["total"] if rows else 0


def fetch_available_events(cursor, student_id):
    return fetch_all_dict(cursor, """
        SELECT
            e.EventID AS eventId,
            e.Title AS eventTitle,
            e.Description AS eventDescription,
            e.StartDateTime AS startDateTime,
            e.EndDateTime AS endDateTime,
            e.EventStatus AS eventStatus,
            e.Capacity AS capacity,
            o.OrgName AS organizationName,
            l.LocationName AS locationName,
            l.IsVirtual AS isVirtual,
            (
                SELECT COUNT(*)
                FROM REGISTRATION r2
                WHERE r2.EventID = e.EventID
                  AND r2.RegistrationStatus = 'Registered'
            ) AS registeredCount,
            r.RegistrationStatus AS myRegistrationStatus
        FROM EVENT e
        LEFT JOIN ORGANIZATION o ON o.OrgID = e.OrgID
        LEFT JOIN LOCATION l ON l.LocationID = e.LocationID
        LEFT JOIN REGISTRATION r
            ON r.EventID = e.EventID
           AND r.StudentID = %s
        WHERE e.EventStatus IN ('Approved', 'Scheduled')
        ORDER BY e.StartDateTime ASC, e.EventID ASC
    """, (student_id,))


def fetch_student_memberships(cursor, student_id):
    return fetch_all_dict(cursor, """
        SELECT
            m.OrgID AS orgId,
            o.OrgName AS orgName,
            o.Description AS description,
            o.ContactEmail AS contactEmail,
            o.OrgStatus AS orgStatus,
            m.JoinDate AS joinDate,
            m.LeaveDate AS leaveDate,
            m.MemberRole AS memberRole
        FROM MEMBERSHIP m
        JOIN ORGANIZATION o ON o.OrgID = m.OrgID
        WHERE m.StudentID = %s
        ORDER BY
            CASE WHEN m.LeaveDate IS NULL THEN 0 ELSE 1 END,
            o.OrgName
    """, (student_id,))


def fetch_joinable_organizations(cursor, student_id):
    return fetch_all_dict(cursor, """
        SELECT
            o.OrgID AS orgId,
            o.OrgName AS orgName,
            o.Description AS description,
            o.ContactEmail AS contactEmail,
            o.OrgStatus AS orgStatus
        FROM ORGANIZATION o
        WHERE o.OrgStatus = 'Active'
          AND NOT EXISTS (
              SELECT 1
              FROM MEMBERSHIP m
              WHERE m.StudentID = %s
                AND m.OrgID = o.OrgID
                AND m.LeaveDate IS NULL
          )
        ORDER BY o.OrgName
    """, (student_id,))


def fetch_active_membership(cursor, student_id, org_id):
    rows = fetch_all_dict(cursor, """
        SELECT
            StudentID AS studentId,
            OrgID AS orgId,
            JoinDate AS joinDate,
            LeaveDate AS leaveDate,
            MemberRole AS memberRole
        FROM MEMBERSHIP
        WHERE StudentID = %s
          AND OrgID = %s
          AND LeaveDate IS NULL
        LIMIT 1
    """, (student_id, org_id))
    return rows[0] if rows else None


def fetch_membership_record(cursor, student_id, org_id):
    rows = fetch_all_dict(cursor, """
        SELECT
            StudentID AS studentId,
            OrgID AS orgId,
            JoinDate AS joinDate,
            LeaveDate AS leaveDate,
            MemberRole AS memberRole
        FROM MEMBERSHIP
        WHERE StudentID = %s
          AND OrgID = %s
        LIMIT 1
    """, (student_id, org_id))
    return rows[0] if rows else None


def fetch_officer_role_for_org(cursor, student_id, org_id):
    rows = fetch_all_dict(cursor, """
        SELECT
            StudentID AS studentId,
            OrgID AS orgId,
            StartDate AS startDate,
            RoleTitle AS roleTitle,
            EndDate AS endDate
        FROM ORGANIZATION_OFFICER
        WHERE StudentID = %s
          AND OrgID = %s
          AND (EndDate IS NULL OR EndDate >= CURDATE())
        ORDER BY StartDate DESC
        LIMIT 1
    """, (student_id, org_id))
    return rows[0] if rows else None


def fetch_event_detail(cursor, event_id):
    rows = fetch_all_dict(cursor, """
        SELECT
            e.EventID AS eventId,
            e.OrgID AS orgId,
            e.LocationID AS locationId,
            e.CategoryID AS categoryId,
            e.TermID AS termId,
            e.Title AS title,
            e.Description AS description,
            e.Capacity AS capacity,
            e.StartDateTime AS startDateTime,
            e.EndDateTime AS endDateTime,
            e.EventStatus AS eventStatus,
            o.OrgName AS orgName,
            l.LocationName AS locationName
        FROM EVENT e
        LEFT JOIN ORGANIZATION o ON o.OrgID = e.OrgID
        LEFT JOIN LOCATION l ON l.LocationID = e.LocationID
        WHERE e.EventID = %s
        LIMIT 1
    """, (event_id,))
    return rows[0] if rows else None


def fetch_event_approval(cursor, event_id):
    rows = safe_fetch(cursor, """
        SELECT
            EventID AS eventId,
            SubmittedByOfficerStudentID AS submittedByOfficerStudentId,
            SubmittedByOfficerOrgID AS submittedByOfficerOrgId,
            SubmittedByOfficerStartDate AS submittedByOfficerStartDate,
            ReviewedByAdminID AS reviewedByAdminId,
            SubmittedAt AS submittedAt,
            ReviewedAt AS reviewedAt,
            DecisionStatus AS decisionStatus,
            DecisionNotes AS decisionNotes
        FROM APPROVAL
        WHERE EventID = %s
        LIMIT 1
    """, (event_id,))
    return rows[0] if rows else None


def fetch_officer_event_registrations(cursor, event_id):
    return fetch_all_dict(cursor, """
        SELECT
            r.StudentID AS studentId,
            s.FirstName AS firstName,
            s.LastName AS lastName,
            s.Email AS email,
            r.RegisteredAt AS registeredAt,
            r.RegistrationStatus AS registrationStatus,
            a.CheckInTime AS checkInTime,
            a.AttendanceFlag AS attendanceFlag
        FROM REGISTRATION r
        JOIN STUDENT s ON s.StudentID = r.StudentID
        LEFT JOIN ATTENDANCE a
            ON a.StudentID = r.StudentID
           AND a.EventID = r.EventID
        WHERE r.EventID = %s
        ORDER BY
            CASE
                WHEN r.RegistrationStatus = 'Registered' THEN 0
                WHEN r.RegistrationStatus = 'Waitlisted' THEN 1
                ELSE 2
            END,
            s.LastName,
            s.FirstName
    """, (event_id,))


def fetch_admin_review_queue(cursor):
    return safe_fetch(cursor, """
        SELECT
            e.EventID AS eventId,
            e.Title AS eventTitle,
            e.EventStatus AS eventStatus,
            e.StartDateTime AS startDateTime,
            o.OrgName AS orgName,
            a.SubmittedAt AS submittedAt,
            a.ReviewedAt AS reviewedAt,
            a.DecisionStatus AS decisionStatus,
            a.DecisionNotes AS decisionNotes
        FROM EVENT e
        JOIN ORGANIZATION o ON o.OrgID = e.OrgID
        LEFT JOIN APPROVAL a ON a.EventID = e.EventID
        WHERE e.EventStatus = 'Submitted'
           OR a.DecisionStatus = 'Pending'
        ORDER BY COALESCE(a.SubmittedAt, e.StartDateTime) DESC, e.EventID DESC
    """)


def fetch_admin_student_management(cursor):
    return fetch_all_dict(cursor, """
        SELECT
            StudentID AS studentId,
            FirstName AS firstName,
            LastName AS lastName,
            Email AS email,
            ClassYear AS classYear,
            Major AS major,
            AccountStatus AS accountStatus
        FROM STUDENT
        ORDER BY LastName, FirstName, StudentID
    """)


def fetch_admin_membership_management(cursor):
    return fetch_all_dict(cursor, """
        SELECT
            m.StudentID AS studentId,
            s.FirstName AS firstName,
            s.LastName AS lastName,
            m.OrgID AS orgId,
            o.OrgName AS orgName,
            m.JoinDate AS joinDate,
            m.LeaveDate AS leaveDate,
            m.MemberRole AS memberRole
        FROM MEMBERSHIP m
        JOIN STUDENT s ON s.StudentID = m.StudentID
        JOIN ORGANIZATION o ON o.OrgID = m.OrgID
        ORDER BY
            CASE WHEN m.LeaveDate IS NULL THEN 0 ELSE 1 END,
            o.OrgName,
            s.LastName,
            s.FirstName
    """)


def fetch_admin_officer_management(cursor):
    return fetch_all_dict(cursor, """
        SELECT
            oo.StudentID AS studentId,
            s.FirstName AS firstName,
            s.LastName AS lastName,
            oo.OrgID AS orgId,
            o.OrgName AS orgName,
            oo.StartDate AS startDate,
            oo.EndDate AS endDate,
            oo.RoleTitle AS roleTitle
        FROM ORGANIZATION_OFFICER oo
        JOIN STUDENT s ON s.StudentID = oo.StudentID
        JOIN ORGANIZATION o ON o.OrgID = oo.OrgID
        ORDER BY
            CASE WHEN oo.EndDate IS NULL OR oo.EndDate >= CURDATE() THEN 0 ELSE 1 END,
            o.OrgName,
            oo.StartDate DESC
    """)


def fetch_all_organizations(cursor):
    return fetch_all_dict(cursor, """
        SELECT
            OrgID AS orgId,
            OrgName AS orgName,
            Description AS description,
            ContactEmail AS contactEmail,
            OrgStatus AS orgStatus
        FROM ORGANIZATION
        ORDER BY OrgName
    """)


def fetch_all_locations(cursor):
    return fetch_all_dict(cursor, """
        SELECT
            LocationID AS locationId,
            LocationName AS locationName,
            Building AS building,
            Room AS room,
            Address AS address,
            IsVirtual AS isVirtual,
            VirtualLink AS virtualLink,
            Capacity AS capacity
        FROM LOCATION
        ORDER BY LocationName
    """)


def fetch_all_categories(cursor):
    return fetch_all_dict(cursor, """
        SELECT
            CategoryID AS categoryId,
            CategoryName AS categoryName,
            Description AS description
        FROM EVENT_CATEGORY
        ORDER BY CategoryName
    """)


def fetch_all_terms(cursor):
    return fetch_all_dict(cursor, """
        SELECT
            TermID AS termId,
            TermName AS termName,
            StartDate AS startDate,
            EndDate AS endDate
        FROM ACADEMIC_TERM
        ORDER BY StartDate DESC, TermName
    """)


def promote_waitlisted_registration(cursor, event_id):
    next_waitlist = safe_fetch(cursor, """
        SELECT
            StudentID AS studentId
        FROM REGISTRATION
        WHERE EventID = %s
          AND RegistrationStatus = 'Waitlisted'
        ORDER BY RegisteredAt ASC, StudentID ASC
        LIMIT 1
    """, (event_id,))

    if next_waitlist:
        cursor.execute("""
            UPDATE REGISTRATION
            SET RegistrationStatus = 'Registered'
            WHERE StudentID = %s
              AND EventID = %s
        """, (next_waitlist[0]["studentId"], event_id))


def current_student_id():
    return session.get("student_id")


def current_admin_id():
    return session.get("admin_id")


def current_user_role():
    return session.get("user_role")


def current_auth_account_type():
    return "admin" if current_user_role() == "admin" else "student"


def current_auth_account_ref_id():
    if current_user_role() == "admin":
        return current_admin_id()
    return current_student_id()


def fetch_event_creation_options(cursor, allowed_org_ids=None):
    org_filter = ""
    params = ()
    if allowed_org_ids is not None:
        if not allowed_org_ids:
            return {
                "organizations": [],
                "locations": fetch_all_dict(cursor, """
                    SELECT
                        LocationID AS locationId,
                        LocationName AS locationName
                    FROM LOCATION
                    ORDER BY LocationName
                """),
                "categories": fetch_all_dict(cursor, """
                    SELECT
                        CategoryID AS categoryId,
                        CategoryName AS categoryName
                    FROM EVENT_CATEGORY
                    ORDER BY CategoryName
                """),
                "terms": fetch_all_dict(cursor, """
                    SELECT
                        TermID AS termId,
                        TermName AS termName
                    FROM ACADEMIC_TERM
                    ORDER BY StartDate DESC
                """),
            }

        placeholders = ", ".join(["%s"] * len(allowed_org_ids))
        org_filter = f" AND OrgID IN ({placeholders})"
        params = tuple(allowed_org_ids)

    return {
        "organizations": fetch_all_dict(cursor, """
            SELECT
                OrgID AS orgId,
                OrgName AS orgName
            FROM ORGANIZATION
            WHERE OrgStatus = 'Active'
        """ + org_filter + """
            ORDER BY OrgName
        """, params),
        "locations": fetch_all_locations(cursor),
        "categories": fetch_all_categories(cursor),
        "terms": fetch_all_terms(cursor),
    }


def parse_datetime_local(value):
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def parse_date_value(value):
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def student_required():
    student_id = current_student_id()
    if not student_id:
        return None, redirect(url_for("login"))
    return student_id, None


def officer_required():
    student_id, redirect_response = student_required()
    if redirect_response:
        return None, None, redirect_response

    conn = None
    cursor = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        student = fetch_student_by_id(cursor, student_id)
        officer_roles = fetch_active_officer_roles(cursor, student_id)
        if not student or not officer_roles:
            flash("Officer access is required for that page.", "error")
            return None, None, redirect(url_for("portal_home"))
        return student, officer_roles, None
    except mysql.connector.Error:
        flash("Could not verify officer permissions right now.", "error")
        return None, None, redirect(url_for("portal_home"))
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


def admin_required():
    admin_id = current_admin_id()
    if not admin_id or current_user_role() != "admin":
        flash("Administrator access is required for that page.", "error")
        return None, redirect(url_for("login"))
    return admin_id, None


def role_home_endpoint():
    role = current_user_role()
    if role == "admin":
        return "admin_dashboard"
    if role == "officer":
        return "officer_dashboard"
    return "my_signups"


def build_session_for_student(student, officer_roles):
    session.clear()
    session["student_id"] = student["studentId"]
    session["student_name"] = f"{student['firstName']} {student['lastName']}"
    session["user_role"] = "officer" if officer_roles else "student"


def build_session_for_admin(admin):
    session.clear()
    session["admin_id"] = admin["adminId"]
    session["admin_name"] = f"{admin['firstName']} {admin['lastName']}"
    session["user_role"] = "admin"


def fetch_officer_dashboard_data(cursor, student_id):
    officer_roles = fetch_active_officer_roles(cursor, student_id)
    org_ids = [role["orgId"] for role in officer_roles]
    if not org_ids:
        return {
            "officerRoles": [],
            "managedEvents": [],
            "roster": [],
            "approvals": [],
            "draftEvents": [],
        }

    org_placeholders = ", ".join(["%s"] * len(org_ids))

    managed_events = fetch_all_dict(cursor, f"""
        SELECT
            e.EventID AS eventId,
            e.Title AS title,
            e.EventStatus AS eventStatus,
            e.StartDateTime AS startDateTime,
            e.EndDateTime AS endDateTime,
            o.OrgName AS orgName,
            (
                SELECT COUNT(*)
                FROM REGISTRATION r
                WHERE r.EventID = e.EventID
                  AND r.RegistrationStatus = 'Registered'
            ) AS registeredCount
        FROM EVENT e
        JOIN ORGANIZATION o ON o.OrgID = e.OrgID
        WHERE e.OrgID IN ({org_placeholders})
        ORDER BY e.StartDateTime DESC, e.EventID DESC
    """, tuple(org_ids))

    roster = fetch_all_dict(cursor, f"""
        SELECT
            m.OrgID AS orgId,
            o.OrgName AS orgName,
            m.StudentID AS studentId,
            s.FirstName AS firstName,
            s.LastName AS lastName,
            m.MemberRole AS memberRole,
            m.JoinDate AS joinDate,
            m.LeaveDate AS leaveDate
        FROM MEMBERSHIP m
        JOIN STUDENT s ON s.StudentID = m.StudentID
        JOIN ORGANIZATION o ON o.OrgID = m.OrgID
        WHERE m.OrgID IN ({org_placeholders})
        ORDER BY o.OrgName, s.LastName, s.FirstName
    """, tuple(org_ids))

    approvals = safe_fetch(cursor, f"""
        SELECT
            a.EventID AS eventId,
            e.Title AS eventTitle,
            o.OrgName AS orgName,
            a.SubmittedAt AS submittedAt,
            a.ReviewedAt AS reviewedAt,
            a.DecisionStatus AS decisionStatus,
            a.DecisionNotes AS decisionNotes,
            ad.FirstName AS reviewerFirstName,
            ad.LastName AS reviewerLastName
        FROM APPROVAL a
        JOIN EVENT e ON e.EventID = a.EventID
        JOIN ORGANIZATION o ON o.OrgID = e.OrgID
        LEFT JOIN ADMINISTRATOR ad ON ad.AdminID = a.ReviewedByAdminID
        WHERE e.OrgID IN ({org_placeholders})
        ORDER BY a.SubmittedAt DESC, a.EventID DESC
    """, tuple(org_ids))

    draft_events = fetch_all_dict(cursor, f"""
        SELECT
            e.EventID AS eventId,
            e.Title AS title,
            e.EventStatus AS eventStatus,
            e.StartDateTime AS startDateTime,
            o.OrgName AS orgName
        FROM EVENT e
        JOIN ORGANIZATION o ON o.OrgID = e.OrgID
        WHERE e.OrgID IN ({org_placeholders})
          AND e.EventStatus IN ('Draft', 'Rejected')
        ORDER BY e.StartDateTime DESC, e.EventID DESC
    """, tuple(org_ids))

    return {
        "officerRoles": officer_roles,
        "managedEvents": managed_events,
        "roster": roster,
        "approvals": approvals,
        "draftEvents": draft_events,
    }


def fetch_admin_dashboard_data(cursor):
    pending_approvals = fetch_admin_review_queue(cursor)
    organizations = fetch_all_organizations(cursor)

    admins = fetch_all_dict(cursor, """
        SELECT
            AdminID AS adminId,
            FirstName AS firstName,
            LastName AS lastName,
            Department AS department,
            AdminStatus AS adminStatus
        FROM ADMINISTRATOR
        ORDER BY LastName, FirstName
    """)

    return {
        "approvals": pending_approvals,
        "organizations": organizations,
        "reports": build_reports(cursor),
        "admins": admins,
        "students": fetch_admin_student_management(cursor),
        "memberships": fetch_admin_membership_management(cursor),
        "officerRoles": fetch_admin_officer_management(cursor),
        "locations": fetch_all_locations(cursor),
        "categories": fetch_all_categories(cursor),
        "terms": fetch_all_terms(cursor),
    }


def build_reports(cursor):
    reports = safe_fetch(cursor, """
        SELECT
            ReportID AS reportId,
            GeneratedByAdminID AS generatedByAdminId,
            ReportType AS reportType,
            GeneratedAt AS generatedAt,
            Summary AS summary
        FROM REPORT
        ORDER BY GeneratedAt DESC
    """)

    if reports:
        return reports

    generated_at = datetime.now().isoformat(timespec="minutes")

    active_registrations = safe_fetch(cursor, """
        SELECT COUNT(*) AS total
        FROM REGISTRATION
        WHERE RegistrationStatus = 'Registered'
    """)
    pending_approvals = safe_fetch(cursor, """
        SELECT COUNT(*) AS total
        FROM APPROVAL
        WHERE DecisionStatus = 'Pending'
    """)
    active_orgs = safe_fetch(cursor, """
        SELECT COUNT(*) AS total
        FROM ORGANIZATION
        WHERE OrgStatus = 'Active'
    """)

    reg_total = active_registrations[0]["total"] if active_registrations else 0
    pending_total = pending_approvals[0]["total"] if pending_approvals else 0
    org_total = active_orgs[0]["total"] if active_orgs else 0

    return [
        {
            "reportId": "AUTO-001",
            "generatedByAdminId": "",
            "reportType": "Registration Snapshot",
            "generatedAt": generated_at,
            "summary": f"There are {reg_total} active event registrations in the system.",
        },
        {
            "reportId": "AUTO-002",
            "generatedByAdminId": "",
            "reportType": "Approval Queue",
            "generatedAt": generated_at,
            "summary": f"There are {pending_total} event approvals still waiting for review.",
        },
        {
            "reportId": "AUTO-003",
            "generatedByAdminId": "",
            "reportType": "Organization Status",
            "generatedAt": generated_at,
            "summary": f"There are {org_total} active organizations currently on file.",
        },
    ]


@app.route("/")
def home():
    return redirect(url_for("login"))


@app.route("/dashboard")
def dashboard_page():
    return render_template("index.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if current_user_role():
        return redirect(url_for("portal_home"))

    error = ""
    form_values = {"account_type": "student", "account_id": ""}
    show_admin_setup = False

    if request.method == "POST":
        form_values["account_type"] = request.form.get("account_type", "student").strip()
        form_values["account_id"] = request.form.get("account_id", "").strip()
        password = request.form.get("password", "")

        if not form_values["account_id"] or not password:
            error = "Enter both account ID and password."
        else:
            conn = None
            cursor = None
            try:
                conn = get_connection()
                cursor = conn.cursor()
                show_admin_setup = count_admin_auth_users(cursor) == 0

                if form_values["account_type"] == "admin":
                    admin = fetch_admin_by_id(cursor, form_values["account_id"])
                    auth_user = fetch_auth_user(cursor, "admin", form_values["account_id"])

                    if not admin or not auth_user or not check_password_hash(auth_user["passwordHash"], password):
                        error = "Invalid administrator ID or password."
                    elif admin["adminStatus"] != "Active":
                        error = f"Administrator account is {admin['adminStatus']}."
                    else:
                        build_session_for_admin(admin)
                        return redirect(url_for("portal_home"))
                else:
                    normalized_student_id = normalize_student_id(form_values["account_id"])
                    if not normalized_student_id:
                        error = "Student IDs must use numbers only."
                        return render_template(
                            "login.html",
                            error=error,
                            form_values=form_values,
                            show_admin_setup=show_admin_setup,
                        )

                    form_values["account_id"] = normalized_student_id
                    student = fetch_student_by_id(cursor, normalized_student_id)
                    auth_user = fetch_auth_user(cursor, "student", normalized_student_id)

                    if not student or not auth_user or not check_password_hash(auth_user["passwordHash"], password):
                        error = "Invalid student ID or password."
                    elif student["accountStatus"] != "Active":
                        error = f"Account is {student['accountStatus']}. Contact your administrator."
                    else:
                        officer_roles = fetch_active_officer_roles(cursor, student["studentId"])
                        build_session_for_student(student, officer_roles)
                        return redirect(url_for("portal_home"))
            except mysql.connector.Error:
                error = "Unable to connect to the database right now. Please try again."
            finally:
                if cursor:
                    cursor.close()
                if conn:
                    conn.close()

    if request.method == "GET":
        conn = None
        cursor = None
        try:
            conn = get_connection()
            cursor = conn.cursor()
            show_admin_setup = count_admin_auth_users(cursor) == 0
        except mysql.connector.Error:
            show_admin_setup = False
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()

    return render_template("login.html", error=error, form_values=form_values, show_admin_setup=show_admin_setup)


@app.route("/signup", methods=["GET", "POST"])
def signup():
    if current_user_role():
        return redirect(url_for("portal_home"))

    error = ""
    success = ""
    form_values = {
        "student_id": "",
        "first_name": "",
        "last_name": "",
        "email": "",
        "class_year": "",
        "major": "",
    }

    if request.method == "POST":
        form_values = {
            "student_id": request.form.get("student_id", "").strip(),
            "first_name": request.form.get("first_name", "").strip(),
            "last_name": request.form.get("last_name", "").strip(),
            "email": request.form.get("email", "").strip(),
            "class_year": request.form.get("class_year", "").strip(),
            "major": request.form.get("major", "").strip(),
        }
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")
        normalized_student_id = normalize_student_id(form_values["student_id"])

        if any(not value for value in form_values.values()):
            error = "Fill in all account fields."
        elif not normalized_student_id:
            error = "Student IDs must use numbers only."
        elif len(password) < 8:
            error = "Password must be at least 8 characters."
        elif password != confirm_password:
            error = "Password confirmation does not match."
        else:
            form_values["student_id"] = normalized_student_id
            conn = None
            cursor = None
            try:
                conn = get_connection()
                cursor = conn.cursor()

                existing_student = fetch_student_by_id(cursor, form_values["student_id"])
                existing_email = safe_fetch(cursor, """
                    SELECT StudentID
                    FROM STUDENT
                    WHERE LOWER(Email) = LOWER(%s)
                    LIMIT 1
                """, (form_values["email"],))

                if existing_student:
                    error = "That Student ID already exists."
                elif existing_email:
                    error = "That email address is already in use."
                elif fetch_auth_user(cursor, "student", form_values["student_id"]):
                    error = "A login already exists for that student account."
                else:
                    cursor.execute("""
                        INSERT INTO STUDENT (
                            StudentID,
                            FirstName,
                            LastName,
                            Email,
                            ClassYear,
                            Major,
                            AccountStatus
                        )
                        VALUES (%s, %s, %s, %s, %s, %s, 'Active')
                    """, (
                        form_values["student_id"],
                        form_values["first_name"],
                        form_values["last_name"],
                        form_values["email"],
                            form_values["class_year"],
                            form_values["major"],
                        ))
                    create_auth_user(cursor, "student", form_values["student_id"], password)
                    conn.commit()
                    success = "Account created successfully. You can sign in now."
                    form_values = {
                        "student_id": "",
                        "first_name": "",
                        "last_name": "",
                        "email": "",
                        "class_year": "",
                        "major": "",
                    }
            except mysql.connector.Error as exc:
                if conn:
                    conn.rollback()
                if exc.errno == errorcode.ER_DUP_ENTRY:
                    error = "That student record already exists."
                else:
                    error = "Could not create the account right now. Please try again."
            finally:
                if cursor:
                    cursor.close()
                if conn:
                    conn.close()

    return render_template("signup.html", error=error, success=success, form_values=form_values)


@app.route("/setup-admin", methods=["GET", "POST"])
def setup_admin():
    if current_user_role():
        return redirect(url_for("portal_home"))

    error = ""
    success = ""
    form_values = {"admin_id": "", "email": ""}

    conn = None
    cursor = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        if count_admin_auth_users(cursor) > 0:
            return redirect(url_for("login"))

        if request.method == "POST":
            form_values["admin_id"] = request.form.get("admin_id", "").strip()
            form_values["email"] = request.form.get("email", "").strip()
            password = request.form.get("password", "")
            confirm_password = request.form.get("confirm_password", "")

            if not form_values["admin_id"] or not form_values["email"] or not password:
                error = "Enter admin ID, email, and password."
            elif len(password) < 8:
                error = "Password must be at least 8 characters."
            elif password != confirm_password:
                error = "Password confirmation does not match."
            else:
                admin = fetch_admin_by_credentials(cursor, form_values["admin_id"], form_values["email"])
                if not admin:
                    error = "No active administrator record matched that ID and email."
                elif admin["adminStatus"] != "Active":
                    error = f"Administrator account is {admin['adminStatus']}."
                elif fetch_auth_user(cursor, "admin", form_values["admin_id"]):
                    error = "That administrator already has login credentials."
                else:
                    create_auth_user(cursor, "admin", form_values["admin_id"], password)
                    conn.commit()
                    success = "Administrator login created. You can sign in now."
                    form_values = {"admin_id": "", "email": ""}
    except mysql.connector.Error:
        if conn:
            conn.rollback()
        error = "Could not initialize the administrator account right now."
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

    return render_template("setup_admin.html", error=error, success=success, form_values=form_values)


@app.route("/change-password", methods=["POST"])
def change_password():
    if not current_user_role():
        return redirect(url_for("login"))

    current_password = request.form.get("current_password", "")
    new_password = request.form.get("new_password", "")
    confirm_password = request.form.get("confirm_password", "")

    if not current_password or not new_password:
        flash("Enter your current and new password.", "error")
        return redirect(url_for("portal_home"))
    if len(new_password) < 8:
        flash("New password must be at least 8 characters.", "error")
        return redirect(url_for("portal_home"))
    if new_password != confirm_password:
        flash("New password confirmation does not match.", "error")
        return redirect(url_for("portal_home"))

    conn = None
    cursor = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        account_type = current_auth_account_type()
        account_ref_id = current_auth_account_ref_id()
        auth_user = fetch_auth_user(cursor, account_type, account_ref_id)
        if not auth_user or not check_password_hash(auth_user["passwordHash"], current_password):
            flash("Current password was incorrect.", "error")
            return redirect(url_for("portal_home"))

        update_auth_password(cursor, account_type, account_ref_id, new_password)
        conn.commit()
        flash("Password changed successfully.", "success")
    except mysql.connector.Error:
        if conn:
            conn.rollback()
        flash("Could not change the password right now.", "error")
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

    return redirect(url_for("portal_home"))


@app.route("/portal")
def portal_home():
    if not current_user_role():
        return redirect(url_for("login"))
    return redirect(url_for(role_home_endpoint()))


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/my-signups")
def my_signups():
    student_id, redirect_response = student_required()
    if redirect_response:
        return redirect_response

    conn = None
    cursor = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        student = fetch_student_by_id(cursor, student_id)
        if not student:
            session.clear()
            return redirect(url_for("login"))
        signups = fetch_student_signups(cursor, student_id)
        available_events = fetch_available_events(cursor, student_id)
        memberships = fetch_student_memberships(cursor, student_id)
        joinable_organizations = fetch_joinable_organizations(cursor, student_id)
    except mysql.connector.Error:
        student = {"studentId": student_id, "firstName": "", "lastName": ""}
        signups = []
        available_events = []
        memberships = []
        joinable_organizations = []
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

    return render_template(
        "my_signups.html",
        student=student,
        signups=signups,
        available_events=available_events,
        memberships=memberships,
        joinable_organizations=joinable_organizations,
        current_role=current_user_role(),
        can_create_event=current_user_role() == "officer",
    )


@app.route("/update-profile", methods=["POST"])
def update_profile():
    student_id, redirect_response = student_required()
    if redirect_response:
        return redirect_response

    form_values = {
        "first_name": request.form.get("first_name", "").strip(),
        "last_name": request.form.get("last_name", "").strip(),
        "email": request.form.get("email", "").strip(),
        "class_year": request.form.get("class_year", "").strip(),
        "major": request.form.get("major", "").strip(),
    }
    if any(not value for value in form_values.values()):
        flash("Fill in all profile fields before saving.", "error")
        return redirect(url_for("my_signups"))

    conn = None
    cursor = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        existing_email = safe_fetch(cursor, """
            SELECT StudentID
            FROM STUDENT
            WHERE LOWER(Email) = LOWER(%s)
              AND StudentID <> %s
            LIMIT 1
        """, (form_values["email"], student_id))
        if existing_email:
            flash("That email address is already assigned to another student.", "error")
            return redirect(url_for("my_signups"))

        cursor.execute("""
            UPDATE STUDENT
            SET FirstName = %s,
                LastName = %s,
                Email = %s,
                ClassYear = %s,
                Major = %s
            WHERE StudentID = %s
        """, (
            form_values["first_name"],
            form_values["last_name"],
            form_values["email"],
            form_values["class_year"],
            form_values["major"],
            student_id,
        ))
        conn.commit()
        session["student_name"] = f"{form_values['first_name']} {form_values['last_name']}"
        flash("Profile updated successfully.", "success")
    except mysql.connector.Error:
        if conn:
            conn.rollback()
        flash("Could not update your profile right now.", "error")
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

    return redirect(url_for("my_signups"))


@app.route("/officer-dashboard")
def officer_dashboard():
    student, officer_roles, redirect_response = officer_required()
    if redirect_response:
        return redirect_response

    conn = None
    cursor = None
    dashboard_data = {
        "officerRoles": officer_roles,
        "managedEvents": [],
        "roster": [],
        "approvals": [],
        "draftEvents": [],
    }
    try:
        conn = get_connection()
        cursor = conn.cursor()
        dashboard_data = fetch_officer_dashboard_data(cursor, student["studentId"])
    except mysql.connector.Error:
        flash("Could not load officer dashboard data right now.", "error")
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

    return render_template(
        "officer_dashboard.html",
        student=student,
        officer_roles=dashboard_data["officerRoles"],
        managed_events=dashboard_data["managedEvents"],
        roster=dashboard_data["roster"],
        approvals=dashboard_data["approvals"],
        draft_events=dashboard_data["draftEvents"],
    )


@app.route("/admin-dashboard")
def admin_dashboard():
    admin_id, redirect_response = admin_required()
    if redirect_response:
        return redirect_response

    conn = None
    cursor = None
    admin = None
    dashboard_data = {
        "approvals": [],
        "organizations": [],
        "reports": [],
        "admins": [],
        "students": [],
        "memberships": [],
        "officerRoles": [],
        "locations": [],
        "categories": [],
        "terms": [],
    }
    try:
        conn = get_connection()
        cursor = conn.cursor()
        admin = fetch_admin_by_id(cursor, admin_id)
        if not admin or admin["adminStatus"] != "Active":
            session.clear()
            return redirect(url_for("login"))
        dashboard_data = fetch_admin_dashboard_data(cursor)
    except mysql.connector.Error:
        flash("Could not load administrator data right now.", "error")
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

    return render_template(
        "admin_dashboard.html",
        admin=admin,
        approvals=dashboard_data["approvals"],
        organizations=dashboard_data["organizations"],
        reports=dashboard_data["reports"],
        admins=dashboard_data["admins"],
        students=dashboard_data["students"],
        memberships=dashboard_data["memberships"],
        officer_roles=dashboard_data["officerRoles"],
        locations=dashboard_data["locations"],
        categories=dashboard_data["categories"],
        terms=dashboard_data["terms"],
    )


@app.route("/admin/create-user", methods=["POST"])
def admin_create_user():
    admin_id, redirect_response = admin_required()
    if redirect_response:
        return redirect_response

    account_type = request.form.get("account_type", "").strip()
    account_id = request.form.get("account_id", "").strip()
    first_name = request.form.get("first_name", "").strip()
    last_name = request.form.get("last_name", "").strip()
    email = request.form.get("email", "").strip()
    password = request.form.get("password", "")
    confirm_password = request.form.get("confirm_password", "")
    class_year = request.form.get("class_year", "").strip()
    major = request.form.get("major", "").strip()
    department = request.form.get("department", "").strip()

    if account_type not in {"student", "admin"}:
        flash("Choose a valid user type to create.", "error")
        return redirect(url_for("admin_dashboard"))
    if not account_id or not first_name or not last_name or not email or not password:
        flash("Fill in all required user fields.", "error")
        return redirect(url_for("admin_dashboard"))
    if len(password) < 8:
        flash("Password must be at least 8 characters.", "error")
        return redirect(url_for("admin_dashboard"))
    if password != confirm_password:
        flash("Password confirmation does not match.", "error")
        return redirect(url_for("admin_dashboard"))

    conn = None
    cursor = None
    try:
        conn = get_connection()
        cursor = conn.cursor()

        if account_type == "student":
            normalized_student_id = normalize_student_id(account_id)
            if not normalized_student_id:
                flash("Student account IDs must use numbers only.", "error")
                return redirect(url_for("admin_dashboard"))
            account_id = normalized_student_id

        if fetch_auth_user(cursor, account_type, account_id):
            flash("A login already exists for that account.", "error")
            return redirect(url_for("admin_dashboard"))

        if account_type == "student":
            existing_student = fetch_student_by_id(cursor, account_id)
            existing_email = safe_fetch(cursor, """
                SELECT StudentID
                FROM STUDENT
                WHERE LOWER(Email) = LOWER(%s)
                  AND StudentID <> %s
                LIMIT 1
            """, (email, account_id))
            if not class_year or not major:
                flash("Student users need class year and major.", "error")
                return redirect(url_for("admin_dashboard"))
            if existing_email:
                flash("That email is already used by another student.", "error")
                return redirect(url_for("admin_dashboard"))
            if existing_student:
                cursor.execute("""
                    UPDATE STUDENT
                    SET FirstName = %s,
                        LastName = %s,
                        Email = %s,
                        ClassYear = %s,
                        Major = %s,
                        AccountStatus = 'Active'
                    WHERE StudentID = %s
                """, (first_name, last_name, email, class_year, major, account_id))
            else:
                cursor.execute("""
                    INSERT INTO STUDENT (
                        StudentID,
                        FirstName,
                        LastName,
                        Email,
                        ClassYear,
                        Major,
                        AccountStatus
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, 'Active')
                """, (account_id, first_name, last_name, email, class_year, major))
        else:
            existing_admin = fetch_admin_by_id(cursor, account_id)
            existing_email = safe_fetch(cursor, """
                SELECT AdminID
                FROM ADMINISTRATOR
                WHERE LOWER(Email) = LOWER(%s)
                  AND AdminID <> %s
                LIMIT 1
            """, (email, account_id))
            if not department:
                flash("Administrator users need a department.", "error")
                return redirect(url_for("admin_dashboard"))
            if existing_email:
                flash("That email is already used by another administrator.", "error")
                return redirect(url_for("admin_dashboard"))
            if existing_admin:
                cursor.execute("""
                    UPDATE ADMINISTRATOR
                    SET FirstName = %s,
                        LastName = %s,
                        Email = %s,
                        Department = %s,
                        AdminStatus = 'Active'
                    WHERE AdminID = %s
                """, (first_name, last_name, email, department, account_id))
            else:
                cursor.execute("""
                    INSERT INTO ADMINISTRATOR (
                        AdminID,
                        FirstName,
                        LastName,
                        Email,
                        Department,
                        AdminStatus
                    )
                    VALUES (%s, %s, %s, %s, %s, 'Active')
                """, (account_id, first_name, last_name, email, department))

        create_auth_user(cursor, account_type, account_id, password)
        conn.commit()
        flash(f"{account_type.title()} user created successfully.", "success")
    except mysql.connector.Error as exc:
        if conn:
            conn.rollback()
        if exc.errno == errorcode.ER_DUP_ENTRY:
            flash("That account already exists.", "error")
        else:
            flash("Could not create the user right now.", "error")
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

    return redirect(url_for("admin_dashboard"))


@app.route("/admin/delete-user", methods=["POST"])
def admin_delete_user():
    admin_id, redirect_response = admin_required()
    if redirect_response:
        return redirect_response

    account_type = request.form.get("account_type", "").strip()
    account_id = request.form.get("account_id", "").strip()

    if account_type not in {"student", "admin"}:
        flash("Choose a valid user type to delete.", "error")
        return redirect(url_for("admin_dashboard"))
    if not account_id:
        flash("Choose a valid user account to delete.", "error")
        return redirect(url_for("admin_dashboard"))
    if account_type == "admin" and str(admin_id) == account_id:
        flash("You cannot delete your own administrator account while logged in.", "error")
        return redirect(url_for("admin_dashboard"))

    conn = None
    cursor = None
    try:
        conn = get_connection()
        cursor = conn.cursor()

        if account_type == "student":
            student = fetch_student_by_id(cursor, account_id)
            if not student:
                flash("That student account was not found.", "info")
                return redirect(url_for("admin_dashboard"))

            cursor.execute("""
                UPDATE APPROVAL
                SET SubmittedByOfficerStudentID = NULL,
                    SubmittedByOfficerOrgID = NULL,
                    SubmittedByOfficerStartDate = NULL
                WHERE SubmittedByOfficerStudentID = %s
            """, (account_id,))
            cursor.execute("""
                UPDATE ATTENDANCE
                SET RecordedByOfficerStudentID = NULL,
                    RecordedByOfficerOrgID = NULL,
                    RecordedByOfficerStartDate = NULL
                WHERE RecordedByOfficerStudentID = %s
            """, (account_id,))
            cursor.execute("""
                DELETE FROM ATTENDANCE
                WHERE StudentID = %s
            """, (account_id,))
            cursor.execute("""
                DELETE FROM REGISTRATION
                WHERE StudentID = %s
            """, (account_id,))
            cursor.execute("""
                DELETE FROM ORGANIZATION_OFFICER
                WHERE StudentID = %s
            """, (account_id,))
            cursor.execute("""
                DELETE FROM MEMBERSHIP
                WHERE StudentID = %s
            """, (account_id,))
            delete_auth_user(cursor, "student", account_id)
            cursor.execute("""
                DELETE FROM STUDENT
                WHERE StudentID = %s
            """, (account_id,))
            conn.commit()
            flash(f"Student account {account_id} deleted successfully.", "success")
        else:
            admin = fetch_admin_by_id(cursor, account_id)
            if not admin:
                flash("That administrator account was not found.", "info")
                return redirect(url_for("admin_dashboard"))

            cursor.execute("""
                UPDATE APPROVAL
                SET ReviewedByAdminID = NULL
                WHERE ReviewedByAdminID = %s
            """, (account_id,))
            delete_auth_user(cursor, "admin", account_id)
            cursor.execute("""
                DELETE FROM ADMINISTRATOR
                WHERE AdminID = %s
            """, (account_id,))
            conn.commit()
            flash(f"Administrator account {account_id} deleted successfully.", "success")
    except mysql.connector.Error:
        if conn:
            conn.rollback()
        flash("Could not delete the user right now.", "error")
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

    return redirect(url_for("admin_dashboard"))


@app.route("/create-event", methods=["GET", "POST"])
def create_event():
    student_id, redirect_response = student_required()
    if redirect_response:
        return redirect_response

    conn = None
    cursor = None
    form_values = {
        "event_id": "",
        "title": "",
        "description": "",
        "org_id": "",
        "location_id": "",
        "category_id": "",
        "term_id": "",
        "capacity": "0",
        "start_datetime": "",
        "end_datetime": "",
        "event_status": "Draft",
    }

    try:
        conn = get_connection()
        cursor = conn.cursor()

        student = fetch_student_by_id(cursor, student_id)
        officer_roles = fetch_active_officer_roles(cursor, student_id)
        if not student or student["accountStatus"] != "Active":
            session.clear()
            flash("Only active student accounts can access event creation.", "error")
            return redirect(url_for("login"))
        if not officer_roles:
            flash("Only organization officers can create events.", "error")
            return redirect(url_for("portal_home"))
        session["user_role"] = "officer"
        role = "officer"

        options = fetch_event_creation_options(
            cursor,
            allowed_org_ids=[role_item["orgId"] for role_item in officer_roles],
        )

        if not options["organizations"]:
            flash("Your officer account is not currently linked to an active organization.", "error")
            return redirect(url_for("officer_dashboard"))

        if request.method == "POST":
            form_values = {
                "event_id": request.form.get("event_id", "").strip(),
                "title": request.form.get("title", "").strip(),
                "description": request.form.get("description", "").strip(),
                "org_id": request.form.get("org_id", "").strip(),
                "location_id": request.form.get("location_id", "").strip(),
                "category_id": request.form.get("category_id", "").strip(),
                "term_id": request.form.get("term_id", "").strip(),
                "capacity": request.form.get("capacity", "0").strip(),
                "start_datetime": request.form.get("start_datetime", "").strip(),
                "end_datetime": request.form.get("end_datetime", "").strip(),
                "event_status": request.form.get("event_status", "Draft").strip(),
            }

            required_values = [
                form_values["event_id"],
                form_values["title"],
                form_values["org_id"],
                form_values["location_id"],
                form_values["category_id"],
                form_values["term_id"],
                form_values["start_datetime"],
                form_values["end_datetime"],
                form_values["event_status"],
            ]
            if any(not value for value in required_values):
                flash("Fill in all required fields.", "error")
                return render_template(
                    "create_event.html",
                    student=student,
                    current_role=role,
                    options=options,
                    form_values=form_values,
                    form_mode="create",
                )

            try:
                event_id = int(form_values["event_id"])
            except ValueError:
                flash("Event ID must be a whole number.", "error")
                return render_template(
                    "create_event.html",
                    student=student,
                    current_role=role,
                    options=options,
                    form_values=form_values,
                    form_mode="create",
                )

            if event_id <= 0:
                flash("Event ID must be greater than zero.", "error")
                return render_template(
                    "create_event.html",
                    student=student,
                    current_role=role,
                    options=options,
                    form_values=form_values,
                    form_mode="create",
                )

            try:
                capacity = int(form_values["capacity"])
            except ValueError:
                flash("Capacity must be a whole number.", "error")
                return render_template(
                    "create_event.html",
                    student=student,
                    current_role=role,
                    options=options,
                    form_values=form_values,
                    form_mode="create",
                )

            if capacity < 0:
                flash("Capacity cannot be negative.", "error")
                return render_template(
                    "create_event.html",
                    student=student,
                    current_role=role,
                    options=options,
                    form_values=form_values,
                    form_mode="create",
                )

            start_datetime = parse_datetime_local(form_values["start_datetime"])
            end_datetime = parse_datetime_local(form_values["end_datetime"])
            if not start_datetime or not end_datetime:
                flash("Enter valid start and end date/time values.", "error")
                return render_template(
                    "create_event.html",
                    student=student,
                    current_role=role,
                    options=options,
                    form_values=form_values,
                    form_mode="create",
                )

            if start_datetime >= end_datetime:
                flash("Start date/time must be earlier than end date/time.", "error")
                return render_template(
                    "create_event.html",
                    student=student,
                    current_role=role,
                    options=options,
                    form_values=form_values,
                    form_mode="create",
                )

            if form_values["event_status"] not in ("Draft", "Submitted"):
                flash("Event status must be Draft or Submitted.", "error")
                return render_template(
                    "create_event.html",
                    student=student,
                    current_role=role,
                    options=options,
                    form_values=form_values,
                    form_mode="create",
                )

            org_ids = {str(item["orgId"]) for item in options["organizations"]}
            location_ids = {str(item["locationId"]) for item in options["locations"]}
            category_ids = {str(item["categoryId"]) for item in options["categories"]}
            term_ids = {str(item["termId"]) for item in options["terms"]}

            if form_values["org_id"] not in org_ids:
                flash("Choose a valid organization.", "error")
                return render_template(
                    "create_event.html",
                    student=student,
                    current_role=role,
                    options=options,
                    form_values=form_values,
                    form_mode="create",
                )
            if form_values["location_id"] not in location_ids:
                flash("Choose a valid location.", "error")
                return render_template(
                    "create_event.html",
                    student=student,
                    current_role=role,
                    options=options,
                    form_values=form_values,
                    form_mode="create",
                )
            if form_values["category_id"] not in category_ids:
                flash("Choose a valid category.", "error")
                return render_template(
                    "create_event.html",
                    student=student,
                    current_role=role,
                    options=options,
                    form_values=form_values,
                    form_mode="create",
                )
            if form_values["term_id"] not in term_ids:
                flash("Choose a valid academic term.", "error")
                return render_template(
                    "create_event.html",
                    student=student,
                    current_role=role,
                    options=options,
                    form_values=form_values,
                )

            existing = safe_fetch(cursor, """
                SELECT EventID
                FROM EVENT
                WHERE EventID = %s
                LIMIT 1
            """, (event_id,))
            if existing:
                flash("That Event ID already exists. Use a unique ID.", "error")
                return render_template(
                    "create_event.html",
                    student=student,
                    current_role=role,
                    options=options,
                    form_values=form_values,
                    form_mode="create",
                )

            cursor.execute("""
                INSERT INTO EVENT (
                    EventID,
                    OrgID,
                    LocationID,
                    CategoryID,
                    TermID,
                    Title,
                    Description,
                    Capacity,
                    StartDateTime,
                    EndDateTime,
                    EventStatus
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                event_id,
                form_values["org_id"],
                form_values["location_id"],
                form_values["category_id"],
                form_values["term_id"],
                form_values["title"],
                form_values["description"],
                capacity,
                start_datetime,
                end_datetime,
                form_values["event_status"],
            ))
            conn.commit()
            flash(f"Event {event_id} created successfully.", "success")
            return redirect(url_for("create_event"))

        return render_template(
            "create_event.html",
            student=student,
            current_role=role,
            options=options,
            form_values=form_values,
            form_mode="create",
        )
    except mysql.connector.Error:
        if conn:
            conn.rollback()
        flash("Could not create the event right now. Please try again.", "error")
        return redirect(url_for("create_event"))
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


@app.route("/edit-event/<event_id>", methods=["GET", "POST"])
def edit_event(event_id):
    student, officer_roles, redirect_response = officer_required()
    if redirect_response:
        return redirect_response

    conn = None
    cursor = None
    form_values = {
        "event_id": event_id,
        "title": "",
        "description": "",
        "org_id": "",
        "location_id": "",
        "category_id": "",
        "term_id": "",
        "capacity": "0",
        "start_datetime": "",
        "end_datetime": "",
        "event_status": "Draft",
    }

    try:
        conn = get_connection()
        cursor = conn.cursor()
        event = fetch_event_detail(cursor, event_id)
        if not event:
            flash("Event not found.", "error")
            return redirect(url_for("officer_dashboard"))
        if event["eventStatus"] not in ("Draft", "Submitted", "Rejected"):
            flash("Only draft, submitted, or rejected events can be edited here.", "info")
            return redirect(url_for("officer_dashboard"))

        officer_role = fetch_officer_role_for_org(cursor, student["studentId"], event["orgId"])
        if not officer_role:
            flash("You can only edit events for organizations you manage.", "error")
            return redirect(url_for("officer_dashboard"))

        options = fetch_event_creation_options(
            cursor,
            allowed_org_ids=[role_item["orgId"] for role_item in officer_roles],
        )
        form_values = {
            "event_id": event["eventId"],
            "title": event["title"] or "",
            "description": event["description"] or "",
            "org_id": str(event["orgId"] or ""),
            "location_id": str(event["locationId"] or ""),
            "category_id": str(event["categoryId"] or ""),
            "term_id": str(event["termId"] or ""),
            "capacity": str(event["capacity"] if event["capacity"] is not None else 0),
            "start_datetime": event["startDateTime"][:16] if event["startDateTime"] else "",
            "end_datetime": event["endDateTime"][:16] if event["endDateTime"] else "",
            "event_status": event["eventStatus"] or "Draft",
        }

        if request.method == "POST":
            form_values.update({
                "title": request.form.get("title", "").strip(),
                "description": request.form.get("description", "").strip(),
                "org_id": request.form.get("org_id", "").strip(),
                "location_id": request.form.get("location_id", "").strip(),
                "category_id": request.form.get("category_id", "").strip(),
                "term_id": request.form.get("term_id", "").strip(),
                "capacity": request.form.get("capacity", "0").strip(),
                "start_datetime": request.form.get("start_datetime", "").strip(),
                "end_datetime": request.form.get("end_datetime", "").strip(),
                "event_status": request.form.get("event_status", "Draft").strip(),
            })

            required_values = [
                form_values["title"],
                form_values["org_id"],
                form_values["location_id"],
                form_values["category_id"],
                form_values["term_id"],
                form_values["start_datetime"],
                form_values["end_datetime"],
                form_values["event_status"],
            ]
            if any(not value for value in required_values):
                flash("Fill in all required fields.", "error")
                return render_template(
                    "create_event.html",
                    student=student,
                    current_role="officer",
                    options=options,
                    form_values=form_values,
                    form_mode="edit",
                )

            try:
                capacity = int(form_values["capacity"])
            except ValueError:
                flash("Capacity must be a whole number.", "error")
                return render_template(
                    "create_event.html",
                    student=student,
                    current_role="officer",
                    options=options,
                    form_values=form_values,
                    form_mode="edit",
                )

            if capacity < 0:
                flash("Capacity cannot be negative.", "error")
                return render_template(
                    "create_event.html",
                    student=student,
                    current_role="officer",
                    options=options,
                    form_values=form_values,
                    form_mode="edit",
                )

            start_datetime = parse_datetime_local(form_values["start_datetime"])
            end_datetime = parse_datetime_local(form_values["end_datetime"])
            if not start_datetime or not end_datetime or start_datetime >= end_datetime:
                flash("Enter valid start and end date/time values.", "error")
                return render_template(
                    "create_event.html",
                    student=student,
                    current_role="officer",
                    options=options,
                    form_values=form_values,
                    form_mode="edit",
                )

            if form_values["event_status"] not in ("Draft", "Submitted", "Rejected"):
                flash("Choose a valid event status.", "error")
                return render_template(
                    "create_event.html",
                    student=student,
                    current_role="officer",
                    options=options,
                    form_values=form_values,
                    form_mode="edit",
                )

            org_ids = {str(item["orgId"]) for item in options["organizations"]}
            location_ids = {str(item["locationId"]) for item in options["locations"]}
            category_ids = {str(item["categoryId"]) for item in options["categories"]}
            term_ids = {str(item["termId"]) for item in options["terms"]}
            if form_values["org_id"] not in org_ids or form_values["location_id"] not in location_ids:
                flash("Choose valid organization and location values.", "error")
                return render_template(
                    "create_event.html",
                    student=student,
                    current_role="officer",
                    options=options,
                    form_values=form_values,
                    form_mode="edit",
                )
            if form_values["category_id"] not in category_ids or form_values["term_id"] not in term_ids:
                flash("Choose valid category and academic term values.", "error")
                return render_template(
                    "create_event.html",
                    student=student,
                    current_role="officer",
                    options=options,
                    form_values=form_values,
                    form_mode="edit",
                )

            cursor.execute("""
                UPDATE EVENT
                SET OrgID = %s,
                    LocationID = %s,
                    CategoryID = %s,
                    TermID = %s,
                    Title = %s,
                    Description = %s,
                    Capacity = %s,
                    StartDateTime = %s,
                    EndDateTime = %s,
                    EventStatus = %s
                WHERE EventID = %s
            """, (
                form_values["org_id"],
                form_values["location_id"],
                form_values["category_id"],
                form_values["term_id"],
                form_values["title"],
                form_values["description"],
                capacity,
                start_datetime,
                end_datetime,
                form_values["event_status"],
                event_id,
            ))
            conn.commit()
            flash(f"Event {event_id} updated successfully.", "success")
            return redirect(url_for("officer_dashboard"))

        return render_template(
            "create_event.html",
            student=student,
            current_role="officer",
            options=options,
            form_values=form_values,
            form_mode="edit",
        )
    except mysql.connector.Error:
        if conn:
            conn.rollback()
        flash("Could not update the event right now.", "error")
        return redirect(url_for("officer_dashboard"))
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


@app.route("/join-organization", methods=["POST"])
def join_organization():
    student_id, redirect_response = student_required()
    if redirect_response:
        return redirect_response

    org_id = request.form.get("org_id", "").strip()
    if not org_id:
        flash("Choose a valid organization to join.", "error")
        return redirect(url_for("my_signups"))

    conn = None
    cursor = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        active_membership = fetch_active_membership(cursor, student_id, org_id)
        membership_record = fetch_membership_record(cursor, student_id, org_id)
        if active_membership:
            flash("You are already an active member of that organization.", "info")
            return redirect(url_for("my_signups"))

        if membership_record:
            cursor.execute("""
                UPDATE MEMBERSHIP
                SET JoinDate = %s,
                    LeaveDate = NULL,
                    MemberRole = %s
                WHERE StudentID = %s
                  AND OrgID = %s
            """, (date.today(), membership_record["memberRole"] or "Member", student_id, org_id))
        else:
            cursor.execute("""
                INSERT INTO MEMBERSHIP (StudentID, OrgID, JoinDate, LeaveDate, MemberRole)
                VALUES (%s, %s, %s, NULL, %s)
            """, (student_id, org_id, date.today(), "Member"))
        conn.commit()
        flash("Organization joined successfully.", "success")
    except mysql.connector.Error:
        if conn:
            conn.rollback()
        flash("Could not join the organization right now.", "error")
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

    return redirect(url_for("my_signups"))


@app.route("/leave-organization", methods=["POST"])
def leave_organization():
    student_id, redirect_response = student_required()
    if redirect_response:
        return redirect_response

    org_id = request.form.get("org_id", "").strip()
    if not org_id:
        flash("Choose a valid organization to leave.", "error")
        return redirect(url_for("my_signups"))

    conn = None
    cursor = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        active_membership = fetch_active_membership(cursor, student_id, org_id)
        if not active_membership:
            flash("No active membership was found for that organization.", "info")
            return redirect(url_for("my_signups"))

        cursor.execute("""
            UPDATE MEMBERSHIP
            SET LeaveDate = %s
            WHERE StudentID = %s
              AND OrgID = %s
              AND LeaveDate IS NULL
        """, (date.today(), student_id, org_id))
        conn.commit()
        flash("Membership ended successfully.", "success")
    except mysql.connector.Error:
        if conn:
            conn.rollback()
        flash("Could not update your membership right now.", "error")
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

    return redirect(url_for("my_signups"))


@app.route("/submit-event/<event_id>", methods=["POST"])
def submit_event(event_id):
    student, officer_roles, redirect_response = officer_required()
    if redirect_response:
        return redirect_response

    conn = None
    cursor = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        event = fetch_event_detail(cursor, event_id)
        if not event:
            flash("Event not found.", "error")
            return redirect(url_for("officer_dashboard"))

        officer_role = fetch_officer_role_for_org(cursor, student["studentId"], event["orgId"])
        if not officer_role:
            flash("You can only submit events for organizations you manage.", "error")
            return redirect(url_for("officer_dashboard"))

        if event["eventStatus"] not in ("Draft", "Rejected"):
            flash("Only draft or rejected events can be submitted for review.", "info")
            return redirect(url_for("officer_dashboard"))

        notes = request.form.get("decision_notes", "").strip() or "Submitted by officer dashboard."
        now = datetime.now()

        cursor.execute("""
            UPDATE EVENT
            SET EventStatus = 'Submitted'
            WHERE EventID = %s
        """, (event_id,))

        existing_approval = fetch_event_approval(cursor, event_id)
        if existing_approval:
            cursor.execute("""
                UPDATE APPROVAL
                SET SubmittedByOfficerStudentID = %s,
                    SubmittedByOfficerOrgID = %s,
                    SubmittedByOfficerStartDate = %s,
                    ReviewedByAdminID = NULL,
                    SubmittedAt = %s,
                    ReviewedAt = NULL,
                    DecisionStatus = 'Pending',
                    DecisionNotes = %s
                WHERE EventID = %s
            """, (
                officer_role["studentId"],
                officer_role["orgId"],
                officer_role["startDate"],
                now,
                notes,
                event_id,
            ))
        else:
            cursor.execute("""
                INSERT INTO APPROVAL (
                    EventID,
                    SubmittedByOfficerStudentID,
                    SubmittedByOfficerOrgID,
                    SubmittedByOfficerStartDate,
                    ReviewedByAdminID,
                    SubmittedAt,
                    ReviewedAt,
                    DecisionStatus,
                    DecisionNotes
                )
                VALUES (%s, %s, %s, %s, NULL, %s, NULL, 'Pending', %s)
            """, (
                event_id,
                officer_role["studentId"],
                officer_role["orgId"],
                officer_role["startDate"],
                now,
                notes,
            ))

        conn.commit()
        flash("Event submitted for administrative review.", "success")
    except mysql.connector.Error:
        if conn:
            conn.rollback()
        flash("Could not submit the event right now.", "error")
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

    return redirect(url_for("officer_dashboard"))


@app.route("/event-attendance/<event_id>")
def event_attendance(event_id):
    student, officer_roles, redirect_response = officer_required()
    if redirect_response:
        return redirect_response

    conn = None
    cursor = None
    event = None
    registrations = []
    approval = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        event = fetch_event_detail(cursor, event_id)
        if not event:
            flash("Event not found.", "error")
            return redirect(url_for("officer_dashboard"))

        officer_role = fetch_officer_role_for_org(cursor, student["studentId"], event["orgId"])
        if not officer_role:
            flash("You can only manage attendance for organizations you oversee.", "error")
            return redirect(url_for("officer_dashboard"))

        registrations = fetch_officer_event_registrations(cursor, event_id)
        approval = fetch_event_approval(cursor, event_id)
    except mysql.connector.Error:
        flash("Could not load attendance data right now.", "error")
        return redirect(url_for("officer_dashboard"))
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

    return render_template(
        "attendance.html",
        student=student,
        officer_roles=officer_roles,
        event=event,
        registrations=registrations,
        approval=approval,
    )


@app.route("/record-attendance", methods=["POST"])
def record_attendance():
    student, officer_roles, redirect_response = officer_required()
    if redirect_response:
        return redirect_response

    event_id = request.form.get("event_id", "").strip()
    attendee_student_id = request.form.get("student_id", "").strip()
    attendance_flag = request.form.get("attendance_flag", "").strip() or "Present"

    if not event_id or not attendee_student_id:
        flash("A valid event and student are required.", "error")
        return redirect(url_for("officer_dashboard"))

    conn = None
    cursor = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        event = fetch_event_detail(cursor, event_id)
        if not event:
            flash("Event not found.", "error")
            return redirect(url_for("officer_dashboard"))

        officer_role = fetch_officer_role_for_org(cursor, student["studentId"], event["orgId"])
        if not officer_role:
            flash("You can only record attendance for organizations you manage.", "error")
            return redirect(url_for("officer_dashboard"))

        registration = fetch_registration_record(cursor, attendee_student_id, event_id)
        if not registration or registration["registrationStatus"] not in ("Registered", "Waitlisted"):
            flash("Attendance can only be recorded for registered or waitlisted students.", "error")
            return redirect(url_for("event_attendance", event_id=event_id))

        existing = safe_fetch(cursor, """
            SELECT StudentID
            FROM ATTENDANCE
            WHERE StudentID = %s
              AND EventID = %s
            LIMIT 1
        """, (attendee_student_id, event_id))

        now = datetime.now()
        if existing:
            cursor.execute("""
                UPDATE ATTENDANCE
                SET CheckInTime = %s,
                    AttendanceFlag = %s,
                    RecordedByOfficerStudentID = %s,
                    RecordedByOfficerOrgID = %s,
                    RecordedByOfficerStartDate = %s
                WHERE StudentID = %s
                  AND EventID = %s
            """, (
                now,
                attendance_flag,
                officer_role["studentId"],
                officer_role["orgId"],
                officer_role["startDate"],
                attendee_student_id,
                event_id,
            ))
        else:
            cursor.execute("""
                INSERT INTO ATTENDANCE (
                    StudentID,
                    EventID,
                    CheckInTime,
                    AttendanceFlag,
                    RecordedByOfficerStudentID,
                    RecordedByOfficerOrgID,
                    RecordedByOfficerStartDate
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (
                attendee_student_id,
                event_id,
                now,
                attendance_flag,
                officer_role["studentId"],
                officer_role["orgId"],
                officer_role["startDate"],
            ))

        conn.commit()
        flash("Attendance recorded successfully.", "success")
    except mysql.connector.Error:
        if conn:
            conn.rollback()
        flash("Could not record attendance right now.", "error")
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

    return redirect(url_for("event_attendance", event_id=event_id))


@app.route("/register-event", methods=["POST"])
def register_event():
    student_id, redirect_response = student_required()
    if redirect_response:
        return redirect_response

    event_id = request.form.get("event_id", "").strip()
    if not event_id:
        flash("Choose a valid event to register.", "error")
        return redirect(url_for("my_signups"))

    conn = None
    cursor = None
    try:
        conn = get_connection()
        cursor = conn.cursor()

        student = fetch_student_by_id(cursor, student_id)
        if not student or student["accountStatus"] != "Active":
            flash("Only active student accounts can register for events.", "error")
            session.clear()
            return redirect(url_for("login"))

        event = fetch_event_for_registration(cursor, event_id)
        if not event:
            flash("Event not found.", "error")
            return redirect(url_for("my_signups"))

        if event["eventStatus"] not in ("Approved", "Scheduled"):
            flash("This event is not open for registration.", "error")
            return redirect(url_for("my_signups"))

        registration = fetch_registration_record(cursor, student_id, event_id)
        if registration and registration["registrationStatus"] in ("Registered", "Waitlisted"):
            flash(f"You are already {registration['registrationStatus'].lower()} for this event.", "info")
            return redirect(url_for("my_signups"))

        registered_count = count_registered_students(cursor, event_id)
        can_register = event["capacity"] is None or registered_count < event["capacity"]
        new_status = "Registered" if can_register else "Waitlisted"
        now = datetime.now()

        if registration:
            cursor.execute("""
                UPDATE REGISTRATION
                SET RegisteredAt = %s,
                    RegistrationStatus = %s
                WHERE StudentID = %s
                  AND EventID = %s
            """, (now, new_status, student_id, event_id))
        else:
            cursor.execute("""
                INSERT INTO REGISTRATION (StudentID, EventID, RegisteredAt, RegistrationStatus)
                VALUES (%s, %s, %s, %s)
            """, (student_id, event_id, now, new_status))

        conn.commit()
        flash(f"Registration updated: {event['title']} ({new_status}).", "success")
    except mysql.connector.Error:
        if conn:
            conn.rollback()
        flash("Could not process registration right now. Please try again.", "error")
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

    return redirect(url_for("my_signups"))


@app.route("/unregister-event", methods=["POST"])
def unregister_event():
    student_id, redirect_response = student_required()
    if redirect_response:
        return redirect_response

    event_id = request.form.get("event_id", "").strip()
    if not event_id:
        flash("Choose a valid event to unregister.", "error")
        return redirect(url_for("my_signups"))

    conn = None
    cursor = None
    try:
        conn = get_connection()
        cursor = conn.cursor()

        registration = fetch_registration_record(cursor, student_id, event_id)
        if not registration:
            flash("No registration record was found for that event.", "info")
            return redirect(url_for("my_signups"))

        if registration["registrationStatus"] == "Cancelled":
            flash("You are already unregistered from that event.", "info")
            return redirect(url_for("my_signups"))

        cursor.execute("""
            UPDATE REGISTRATION
            SET RegistrationStatus = 'Cancelled'
            WHERE StudentID = %s
              AND EventID = %s
        """, (student_id, event_id))
        promote_waitlisted_registration(cursor, event_id)
        conn.commit()
        flash("You have been unregistered from the event.", "success")
    except mysql.connector.Error:
        if conn:
            conn.rollback()
        flash("Could not process unregistration right now. Please try again.", "error")
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

    return redirect(url_for("my_signups"))


@app.route("/review-approval/<event_id>", methods=["POST"])
def review_approval(event_id):
    admin_id, redirect_response = admin_required()
    if redirect_response:
        return redirect_response

    decision = request.form.get("decision", "").strip()
    decision_notes = request.form.get("decision_notes", "").strip()
    if decision not in ("Approved", "Rejected"):
        flash("Choose a valid approval decision.", "error")
        return redirect(url_for("admin_dashboard"))

    conn = None
    cursor = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        event = fetch_event_detail(cursor, event_id)
        if not event:
            flash("Event not found.", "error")
            return redirect(url_for("admin_dashboard"))

        approval = fetch_event_approval(cursor, event_id)
        if not approval:
            officer_roles = safe_fetch(cursor, """
                SELECT
                    StudentID AS studentId,
                    OrgID AS orgId,
                    StartDate AS startDate
                FROM ORGANIZATION_OFFICER
                WHERE OrgID = %s
                ORDER BY StartDate DESC
                LIMIT 1
            """, (event["orgId"],))
            if not officer_roles:
                flash("No officer record was found for that event's organization.", "error")
                return redirect(url_for("admin_dashboard"))
            approval = {
                "submittedByOfficerStudentId": officer_roles[0]["studentId"],
                "submittedByOfficerOrgId": officer_roles[0]["orgId"],
                "submittedByOfficerStartDate": officer_roles[0]["startDate"],
                "submittedAt": datetime.now(),
            }
            cursor.execute("""
                INSERT INTO APPROVAL (
                    EventID,
                    SubmittedByOfficerStudentID,
                    SubmittedByOfficerOrgID,
                    SubmittedByOfficerStartDate,
                    ReviewedByAdminID,
                    SubmittedAt,
                    ReviewedAt,
                    DecisionStatus,
                    DecisionNotes
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                event_id,
                approval["submittedByOfficerStudentId"],
                approval["submittedByOfficerOrgId"],
                approval["submittedByOfficerStartDate"],
                admin_id,
                approval["submittedAt"],
                datetime.now(),
                decision,
                decision_notes or f"{decision} through admin dashboard.",
            ))
        else:
            cursor.execute("""
                UPDATE APPROVAL
                SET ReviewedByAdminID = %s,
                    ReviewedAt = %s,
                    DecisionStatus = %s,
                    DecisionNotes = %s
                WHERE EventID = %s
            """, (
                admin_id,
                datetime.now(),
                decision,
                decision_notes or f"{decision} through admin dashboard.",
                event_id,
            ))

        new_event_status = "Approved" if decision == "Approved" else "Rejected"
        cursor.execute("""
            UPDATE EVENT
            SET EventStatus = %s
            WHERE EventID = %s
        """, (new_event_status, event_id))
        conn.commit()
        flash(f"Event {decision.lower()} successfully.", "success")
    except mysql.connector.Error:
        if conn:
            conn.rollback()
        flash("Could not save the approval decision right now.", "error")
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

    return redirect(url_for("admin_dashboard"))


@app.route("/admin/update-student-status", methods=["POST"])
def update_student_status():
    admin_id, redirect_response = admin_required()
    if redirect_response:
        return redirect_response

    student_id = request.form.get("student_id", "").strip()
    account_status = request.form.get("account_status", "").strip()
    allowed_statuses = {"Active", "Inactive", "Suspended"}

    if not student_id or account_status not in allowed_statuses:
        flash("Choose a valid student and account status.", "error")
        return redirect(url_for("admin_dashboard"))

    conn = None
    cursor = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        student = fetch_student_by_id(cursor, student_id)
        if not student:
            flash("Student not found.", "error")
            return redirect(url_for("admin_dashboard"))

        cursor.execute("""
            UPDATE STUDENT
            SET AccountStatus = %s
            WHERE StudentID = %s
        """, (account_status, student_id))
        conn.commit()
        flash(f"Updated {student['firstName']} {student['lastName']} to {account_status}.", "success")
    except mysql.connector.Error:
        if conn:
            conn.rollback()
        flash("Could not update the student account right now.", "error")
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

    return redirect(url_for("admin_dashboard"))


@app.route("/admin/assign-membership", methods=["POST"])
def admin_assign_membership():
    admin_id, redirect_response = admin_required()
    if redirect_response:
        return redirect_response

    student_id = request.form.get("student_id", "").strip()
    org_id = request.form.get("org_id", "").strip()
    member_role = request.form.get("member_role", "").strip() or "Member"
    if not student_id or not org_id:
        flash("Choose both a student and an organization.", "error")
        return redirect(url_for("admin_dashboard"))

    conn = None
    cursor = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        student = fetch_student_by_id(cursor, student_id)
        membership_record = fetch_membership_record(cursor, student_id, org_id)
        if not student:
            flash("Student not found.", "error")
            return redirect(url_for("admin_dashboard"))

        if membership_record and membership_record["leaveDate"] is None:
            cursor.execute("""
                UPDATE MEMBERSHIP
                SET MemberRole = %s
                WHERE StudentID = %s
                  AND OrgID = %s
            """, (member_role, student_id, org_id))
        elif membership_record:
            cursor.execute("""
                UPDATE MEMBERSHIP
                SET JoinDate = %s,
                    LeaveDate = NULL,
                    MemberRole = %s
                WHERE StudentID = %s
                  AND OrgID = %s
            """, (date.today(), member_role, student_id, org_id))
        else:
            cursor.execute("""
                INSERT INTO MEMBERSHIP (StudentID, OrgID, JoinDate, LeaveDate, MemberRole)
                VALUES (%s, %s, %s, NULL, %s)
            """, (student_id, org_id, date.today(), member_role))

        conn.commit()
        flash("Membership updated successfully.", "success")
    except mysql.connector.Error:
        if conn:
            conn.rollback()
        flash("Could not update the membership right now.", "error")
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

    return redirect(url_for("admin_dashboard"))


@app.route("/admin/end-membership", methods=["POST"])
def admin_end_membership():
    admin_id, redirect_response = admin_required()
    if redirect_response:
        return redirect_response

    student_id = request.form.get("student_id", "").strip()
    org_id = request.form.get("org_id", "").strip()
    if not student_id or not org_id:
        flash("Choose a valid membership to end.", "error")
        return redirect(url_for("admin_dashboard"))

    conn = None
    cursor = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        active_membership = fetch_active_membership(cursor, student_id, org_id)
        if not active_membership:
            flash("No active membership was found for that student and organization.", "info")
            return redirect(url_for("admin_dashboard"))

        cursor.execute("""
            UPDATE MEMBERSHIP
            SET LeaveDate = %s
            WHERE StudentID = %s
              AND OrgID = %s
              AND LeaveDate IS NULL
        """, (date.today(), student_id, org_id))
        conn.commit()
        flash("Membership ended successfully.", "success")
    except mysql.connector.Error:
        if conn:
            conn.rollback()
        flash("Could not end the membership right now.", "error")
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

    return redirect(url_for("admin_dashboard"))


@app.route("/admin/assign-officer", methods=["POST"])
def admin_assign_officer():
    admin_id, redirect_response = admin_required()
    if redirect_response:
        return redirect_response

    student_id = request.form.get("student_id", "").strip()
    org_id = request.form.get("org_id", "").strip()
    role_title = request.form.get("role_title", "").strip() or "Officer"
    start_date_raw = request.form.get("start_date", "").strip()
    start_date = None

    if start_date_raw:
        try:
            start_date = date.fromisoformat(start_date_raw)
        except ValueError:
            flash("Enter a valid officer start date.", "error")
            return redirect(url_for("admin_dashboard"))
    else:
        start_date = date.today()

    if not student_id or not org_id:
        flash("Choose both a student and organization for the officer role.", "error")
        return redirect(url_for("admin_dashboard"))

    conn = None
    cursor = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        student = fetch_student_by_id(cursor, student_id)
        existing_officer = fetch_officer_role_for_org(cursor, student_id, org_id)
        membership_record = fetch_membership_record(cursor, student_id, org_id)
        if not student:
            flash("Student not found.", "error")
            return redirect(url_for("admin_dashboard"))

        if existing_officer:
            flash("That student already has an active officer role for this organization.", "info")
            return redirect(url_for("admin_dashboard"))

        if membership_record and membership_record["leaveDate"] is None:
            cursor.execute("""
                UPDATE MEMBERSHIP
                SET MemberRole = %s
                WHERE StudentID = %s
                  AND OrgID = %s
            """, (role_title, student_id, org_id))
        elif membership_record:
            cursor.execute("""
                UPDATE MEMBERSHIP
                SET JoinDate = %s,
                    LeaveDate = NULL,
                    MemberRole = %s
                WHERE StudentID = %s
                  AND OrgID = %s
            """, (start_date, role_title, student_id, org_id))
        else:
            cursor.execute("""
                INSERT INTO MEMBERSHIP (StudentID, OrgID, JoinDate, LeaveDate, MemberRole)
                VALUES (%s, %s, %s, NULL, %s)
            """, (student_id, org_id, start_date, role_title))

        cursor.execute("""
            INSERT INTO ORGANIZATION_OFFICER (
                StudentID,
                OrgID,
                StartDate,
                RoleTitle,
                EndDate
            )
            VALUES (%s, %s, %s, %s, NULL)
        """, (student_id, org_id, start_date, role_title))
        conn.commit()
        flash("Officer role assigned successfully.", "success")
    except mysql.connector.Error as exc:
        if conn:
            conn.rollback()
        if exc.errno == errorcode.ER_DUP_ENTRY:
            flash("That officer role already exists for the chosen start date.", "error")
        else:
            flash("Could not assign the officer role right now.", "error")
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

    return redirect(url_for("admin_dashboard"))


@app.route("/admin/end-officer-role", methods=["POST"])
def admin_end_officer_role():
    admin_id, redirect_response = admin_required()
    if redirect_response:
        return redirect_response

    student_id = request.form.get("student_id", "").strip()
    org_id = request.form.get("org_id", "").strip()
    start_date_raw = request.form.get("start_date", "").strip()
    if not student_id or not org_id or not start_date_raw:
        flash("Choose a valid officer assignment to end.", "error")
        return redirect(url_for("admin_dashboard"))

    try:
        start_date = date.fromisoformat(start_date_raw)
    except ValueError:
        flash("Officer start date was invalid.", "error")
        return redirect(url_for("admin_dashboard"))

    conn = None
    cursor = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE ORGANIZATION_OFFICER
            SET EndDate = %s
            WHERE StudentID = %s
              AND OrgID = %s
              AND StartDate = %s
              AND (EndDate IS NULL OR EndDate >= CURDATE())
        """, (date.today(), student_id, org_id, start_date))
        if cursor.rowcount == 0:
            flash("No active officer role matched that assignment.", "info")
            return redirect(url_for("admin_dashboard"))

        conn.commit()
        flash("Officer role ended successfully.", "success")
    except mysql.connector.Error:
        if conn:
            conn.rollback()
        flash("Could not end the officer role right now.", "error")
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

    return redirect(url_for("admin_dashboard"))


@app.route("/admin/save-organization", methods=["POST"])
def admin_save_organization():
    admin_id, redirect_response = admin_required()
    if redirect_response:
        return redirect_response

    org_id = request.form.get("org_id", "").strip()
    org_name = request.form.get("org_name", "").strip()
    description = request.form.get("description", "").strip()
    contact_email = request.form.get("contact_email", "").strip()
    org_status = request.form.get("org_status", "").strip() or "Active"
    if not org_id or not org_name or not contact_email:
        flash("Organization ID, name, and contact email are required.", "error")
        return redirect(url_for("admin_dashboard"))

    conn = None
    cursor = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        existing = safe_fetch(cursor, """
            SELECT OrgID
            FROM ORGANIZATION
            WHERE OrgID = %s
            LIMIT 1
        """, (org_id,))
        if existing:
            cursor.execute("""
                UPDATE ORGANIZATION
                SET OrgName = %s,
                    Description = %s,
                    ContactEmail = %s,
                    OrgStatus = %s
                WHERE OrgID = %s
            """, (org_name, description, contact_email, org_status, org_id))
            flash("Organization updated successfully.", "success")
        else:
            cursor.execute("""
                INSERT INTO ORGANIZATION (OrgID, OrgName, Description, ContactEmail, OrgStatus)
                VALUES (%s, %s, %s, %s, %s)
            """, (org_id, org_name, description, contact_email, org_status))
            flash("Organization created successfully.", "success")
        conn.commit()
    except mysql.connector.Error as exc:
        if conn:
            conn.rollback()
        if exc.errno == errorcode.ER_DUP_ENTRY:
            flash("That organization ID already exists.", "error")
        else:
            flash("Could not save the organization right now.", "error")
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

    return redirect(url_for("admin_dashboard"))


@app.route("/admin/save-location", methods=["POST"])
def admin_save_location():
    admin_id, redirect_response = admin_required()
    if redirect_response:
        return redirect_response

    location_id = request.form.get("location_id", "").strip()
    location_name = request.form.get("location_name", "").strip()
    building = request.form.get("building", "").strip()
    room = request.form.get("room", "").strip()
    address = request.form.get("address", "").strip()
    virtual_link = request.form.get("virtual_link", "").strip()
    is_virtual = "is_virtual" in request.form
    capacity_raw = request.form.get("capacity", "").strip()
    if not location_id or not location_name:
        flash("Location ID and name are required.", "error")
        return redirect(url_for("admin_dashboard"))

    try:
        capacity = int(capacity_raw) if capacity_raw else None
    except ValueError:
        flash("Location capacity must be a whole number.", "error")
        return redirect(url_for("admin_dashboard"))

    conn = None
    cursor = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        existing = safe_fetch(cursor, """
            SELECT LocationID
            FROM LOCATION
            WHERE LocationID = %s
            LIMIT 1
        """, (location_id,))
        if existing:
            cursor.execute("""
                UPDATE LOCATION
                SET LocationName = %s,
                    Building = %s,
                    Room = %s,
                    Address = %s,
                    IsVirtual = %s,
                    VirtualLink = %s,
                    Capacity = %s
                WHERE LocationID = %s
            """, (
                location_name,
                building,
                room,
                address,
                is_virtual,
                virtual_link,
                capacity,
                location_id,
            ))
            flash("Location updated successfully.", "success")
        else:
            cursor.execute("""
                INSERT INTO LOCATION (
                    LocationID,
                    LocationName,
                    Building,
                    Room,
                    Address,
                    IsVirtual,
                    VirtualLink,
                    Capacity
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                location_id,
                location_name,
                building,
                room,
                address,
                is_virtual,
                virtual_link,
                capacity,
            ))
            flash("Location created successfully.", "success")
        conn.commit()
    except mysql.connector.Error as exc:
        if conn:
            conn.rollback()
        if exc.errno == errorcode.ER_DUP_ENTRY:
            flash("That location ID already exists.", "error")
        else:
            flash("Could not save the location right now.", "error")
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

    return redirect(url_for("admin_dashboard"))


@app.route("/admin/save-category", methods=["POST"])
def admin_save_category():
    admin_id, redirect_response = admin_required()
    if redirect_response:
        return redirect_response

    category_id = request.form.get("category_id", "").strip()
    category_name = request.form.get("category_name", "").strip()
    description = request.form.get("description", "").strip()
    if not category_id or not category_name:
        flash("Category ID and name are required.", "error")
        return redirect(url_for("admin_dashboard"))

    conn = None
    cursor = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        existing = safe_fetch(cursor, """
            SELECT CategoryID
            FROM EVENT_CATEGORY
            WHERE CategoryID = %s
            LIMIT 1
        """, (category_id,))
        if existing:
            cursor.execute("""
                UPDATE EVENT_CATEGORY
                SET CategoryName = %s,
                    Description = %s
                WHERE CategoryID = %s
            """, (category_name, description, category_id))
            flash("Category updated successfully.", "success")
        else:
            cursor.execute("""
                INSERT INTO EVENT_CATEGORY (CategoryID, CategoryName, Description)
                VALUES (%s, %s, %s)
            """, (category_id, category_name, description))
            flash("Category created successfully.", "success")
        conn.commit()
    except mysql.connector.Error as exc:
        if conn:
            conn.rollback()
        if exc.errno == errorcode.ER_DUP_ENTRY:
            flash("That category ID already exists.", "error")
        else:
            flash("Could not save the category right now.", "error")
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

    return redirect(url_for("admin_dashboard"))


@app.route("/admin/save-term", methods=["POST"])
def admin_save_term():
    admin_id, redirect_response = admin_required()
    if redirect_response:
        return redirect_response

    term_id = request.form.get("term_id", "").strip()
    term_name = request.form.get("term_name", "").strip()
    start_date = parse_date_value(request.form.get("start_date", "").strip())
    end_date = parse_date_value(request.form.get("end_date", "").strip())
    if not term_id or not term_name or not start_date or not end_date:
        flash("Term ID, name, start date, and end date are required.", "error")
        return redirect(url_for("admin_dashboard"))
    if start_date >= end_date:
        flash("Term start date must be before the end date.", "error")
        return redirect(url_for("admin_dashboard"))

    conn = None
    cursor = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        existing = safe_fetch(cursor, """
            SELECT TermID
            FROM ACADEMIC_TERM
            WHERE TermID = %s
            LIMIT 1
        """, (term_id,))
        if existing:
            cursor.execute("""
                UPDATE ACADEMIC_TERM
                SET TermName = %s,
                    StartDate = %s,
                    EndDate = %s
                WHERE TermID = %s
            """, (term_name, start_date, end_date, term_id))
            flash("Academic term updated successfully.", "success")
        else:
            cursor.execute("""
                INSERT INTO ACADEMIC_TERM (TermID, TermName, StartDate, EndDate)
                VALUES (%s, %s, %s, %s)
            """, (term_id, term_name, start_date, end_date))
            flash("Academic term created successfully.", "success")
        conn.commit()
    except mysql.connector.Error as exc:
        if conn:
            conn.rollback()
        if exc.errno == errorcode.ER_DUP_ENTRY:
            flash("That academic term ID already exists.", "error")
        else:
            flash("Could not save the academic term right now.", "error")
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

    return redirect(url_for("admin_dashboard"))


@app.route("/api/dashboard")
def api_dashboard():
    conn = get_connection()
    cursor = conn.cursor()

    data = {
        "students": fetch_all_dict(cursor, """
            SELECT
                StudentID AS studentId,
                FirstName AS firstName,
                LastName AS lastName,
                Email AS email,
                ClassYear AS classYear,
                Major AS major,
                AccountStatus AS accountStatus
            FROM STUDENT
            ORDER BY StudentID
        """),
        "administrators": fetch_all_dict(cursor, """
            SELECT
                AdminID AS adminId,
                FirstName AS firstName,
                LastName AS lastName,
                Email AS email,
                Department AS department,
                AdminStatus AS adminStatus
            FROM ADMINISTRATOR
            ORDER BY AdminID
        """),
        "organizations": fetch_all_dict(cursor, """
            SELECT
                OrgID AS orgId,
                OrgName AS orgName,
                Description AS description,
                ContactEmail AS contactEmail,
                OrgStatus AS orgStatus
            FROM ORGANIZATION
            ORDER BY OrgID
        """),
        "organizationOfficers": fetch_all_dict(cursor, """
            SELECT
                StudentID AS studentId,
                OrgID AS orgId,
                StartDate AS startDate,
                RoleTitle AS roleTitle,
                EndDate AS endDate
            FROM ORGANIZATION_OFFICER
            ORDER BY OrgID, StudentID, StartDate
        """),
        "memberships": fetch_all_dict(cursor, """
            SELECT
                StudentID AS studentId,
                OrgID AS orgId,
                JoinDate AS joinDate,
                LeaveDate AS leaveDate,
                MemberRole AS memberRole
            FROM MEMBERSHIP
            ORDER BY OrgID, StudentID
        """),
        "locations": fetch_all_dict(cursor, """
            SELECT
                LocationID AS locationId,
                LocationName AS locationName,
                Building AS building,
                Room AS room,
                Address AS address,
                IsVirtual AS isVirtual,
                VirtualLink AS virtualLink,
                Capacity AS capacity
            FROM LOCATION
            ORDER BY LocationID
        """),
        "categories": fetch_all_dict(cursor, """
            SELECT
                CategoryID AS categoryId,
                CategoryName AS categoryName,
                Description AS description
            FROM EVENT_CATEGORY
            ORDER BY CategoryID
        """),
        "events": fetch_all_dict(cursor, """
            SELECT
                EventID AS eventId,
                OrgID AS orgId,
                LocationID AS locationId,
                CategoryID AS categoryId,
                TermID AS termId,
                Title AS title,
                Description AS description,
                Capacity AS capacity,
                StartDateTime AS startDateTime,
                EndDateTime AS endDateTime,
                EventStatus AS eventStatus
            FROM EVENT
            ORDER BY StartDateTime, EventID
        """),
        "registrations": fetch_all_dict(cursor, """
            SELECT
                StudentID AS studentId,
                EventID AS eventId,
                RegisteredAt AS registeredAt,
                RegistrationStatus AS registrationStatus
            FROM REGISTRATION
            ORDER BY RegisteredAt, StudentID, EventID
        """),
        "attendance": fetch_all_dict(cursor, """
            SELECT
                StudentID AS studentId,
                EventID AS eventId,
                CheckInTime AS checkInTime,
                AttendanceFlag AS attendanceFlag,
                RecordedByOfficerStudentID AS recordedByOfficerStudentId,
                RecordedByOfficerOrgID AS recordedByOfficerOrgId,
                RecordedByOfficerStartDate AS recordedByOfficerStartDate
            FROM ATTENDANCE
            ORDER BY CheckInTime, StudentID, EventID
        """),
        "approvals": fetch_all_dict(cursor, """
            SELECT
                EventID AS eventId,
                SubmittedByOfficerStudentID AS submittedByOfficerStudentId,
                SubmittedByOfficerOrgID AS submittedByOfficerOrgId,
                SubmittedByOfficerStartDate AS submittedByOfficerStartDate,
                ReviewedByAdminID AS reviewedByAdminId,
                SubmittedAt AS submittedAt,
                ReviewedAt AS reviewedAt,
                DecisionStatus AS decisionStatus,
                DecisionNotes AS decisionNotes
            FROM APPROVAL
            ORDER BY SubmittedAt DESC, EventID
        """),
    }

    academic_terms = fetch_all_dict(cursor, """
        SELECT
            TermID AS termId,
            TermName AS termName,
            StartDate AS startDate,
            EndDate AS endDate
        FROM ACADEMIC_TERM
        ORDER BY StartDate DESC
        LIMIT 1
    """)

    data["academicTerm"] = academic_terms[0] if academic_terms else {}
    data["reports"] = build_reports(cursor)

    cursor.close()
    conn.close()

    return jsonify(data)


if __name__ == "__main__":
    app.run(debug=True)
