from datetime import datetime
from database import get_connection, ensure_database_ready

PORTAL_ACCESS_PASSWORD = "1234"

def show_guidelines(title, guidelines):
    print("\n" + "=" * 60)
    print("📌 INPUT GUIDELINES".center(60))
    print("-" * 60)
    print(title.center(60))
    print("-" * 60)

    for guideline in guidelines:
        print("  •", guideline)

    print("=" * 60)


def get_non_empty_input(message):
    while True:
        value = input(message).strip()

        if value:
            return value

        print("\n⚠ This field cannot be empty.")


def get_admin_status():
    print("\n" + "=" * 60)
    print("SELECT USER ACCOUNT STATUS".center(60))
    print("=" * 60)
    print("  1. ACTIVE")
    print("  2. BLOCKED")
    print("  3. INACTIVE")

    show_guidelines(
        "ACCOUNT STATUS SELECTION",
        [
            "Enter 1 for an active account.",
            "Enter 2 to block an account.",
            "Enter 3 to make an account inactive."
        ]
    )

    while True:
        choice = input("\n➜ Enter your choice (1-3): ").strip()

        if choice == "1":
            return "ACTIVE"
        elif choice == "2":
            return "BLOCKED"
        elif choice == "3":
            return "INACTIVE"
        else:
            print("\n⚠ Invalid choice. Please try again.")


def get_vehicle_status():
    print("\n" + "=" * 60)
    print("SELECT VEHICLE STATUS".center(60))
    print("=" * 60)
    print("  1. ACTIVE")
    print("  2. INACTIVE")

    show_guidelines(
        "VEHICLE STATUS SELECTION",
        [
            "Enter 1 to make the vehicle active.",
            "Enter 2 to make the vehicle inactive."
        ]
    )

    while True:
        choice = input("\n➜ Enter your choice (1-2): ").strip()

        if choice == "1":
            return "ACTIVE"
        elif choice == "2":
            return "INACTIVE"
        else:
            print("\n⚠ Invalid choice. Please try again.")


def portal_access():
    print("\n" + "=" * 60)
    print("🔐 ADMIN PORTAL ACCESS".center(60))
    print("=" * 60)

    show_guidelines(
        "PORTAL ACCESS PASSWORD",
        [
            "Enter the Admin Portal Access Password.",
            "Contact the project administrator if you do not know it."
        ]
    )

    password = input("\n➜ Enter Admin Portal Password: ").strip()

    if password == PORTAL_ACCESS_PASSWORD:
        print("\n✓ Admin Portal Access Granted.")
        return True

    print("\n✗ Incorrect Portal Password.")
    print("✗ Access Denied.")
    return False


def add_audit_record(admin_id, action, details):
    conn = None
    cursor = None

    try:
        conn = get_connection()

        if conn is None:
            print("\n✗ Unable to connect to database.")
            return

        cursor = conn.cursor()

        admin_details = "Admin ID: " + str(admin_id) + " | " + details

        cursor.execute(
            """
            INSERT INTO Audit_Records
            (user_id, action, details)
            VALUES (NULL, %s, %s)
            """,
            (action, admin_details)
        )

        conn.commit()

    except Exception as e:
        if conn:
            conn.rollback()

        print("\n⚠ Audit record could not be saved:", e)

    finally:
        if cursor:
            cursor.close()

        if conn:
            conn.close()


def admin_registration():
    print("\n" + "=" * 60)
    print("📝 ADMIN REGISTRATION".center(60))
    print("=" * 60)

    conn = None
    cursor = None

    try:
        conn = get_connection()

        if conn is None:
            print("\n✗ Unable to connect to database.")
            return None

        cursor = conn.cursor()

        print("\nEnter the following registration details:")

        show_guidelines(
            "FULL NAME",
            [
                "Enter your complete name.",
                "Include your first name and last name."
            ]
        )
        full_name = get_non_empty_input("\n➜ Enter Full Name: ")

        show_guidelines(
            "EMAIL ADDRESS",
            [
                "Enter a valid email address.",
                "Example: name@gmail.com"
            ]
        )
        email = get_non_empty_input("\n➜ Enter Email: ")

        if "@" not in email or "." not in email:
            print("\n✗ Invalid email address.")
            return None
        
        print()
        phone = input("\n➜ Enter Phone Number: ").strip()

        if phone == "":
            phone = None

        cursor.execute(
            """
            SELECT admin_id
            FROM Admin
            WHERE email = %s
            """,
            (email,)
        )

        if cursor.fetchone():
            print("\n⚠ Email already exists.")
            return None

        if phone is not None:
            cursor.execute(
                """
                SELECT admin_id
                FROM Admin
                WHERE phone = %s
                """,
                (phone,)
            )

            if cursor.fetchone():
                print("\n⚠ Phone number is already registered.")
                return None

        show_guidelines(
            "CREATE PASSWORD",
            [
                "Create a password containing at least 6 characters.",
                "Remember your password for future login."
            ]
        )
        password = get_non_empty_input("\n➜ Create Password: ")

        if len(password) < 6:
            print("\n⚠ Password must contain at least 6 characters.")
            return None

        show_guidelines(
            "CONFIRM PASSWORD",
            [
                "Enter the same password again.",
                "Both passwords must match."
            ]
        )
        confirm_password = get_non_empty_input("\n➜ Confirm Password: ")

        if password != confirm_password:
            print("\n✗ Passwords do not match.")
            return None

        cursor.execute(
            """
            INSERT INTO Admin
            (full_name, email, phone, password)
            VALUES (%s, %s, %s, %s)
            """,
            (full_name, email, phone, password)
        )

        admin_id = cursor.lastrowid
        conn.commit()

        print("\n" + "=" * 60)
        print("✓ ADMIN REGISTRATION SUCCESSFUL!".center(60))
        print("=" * 60)

        print("\n  Your Admin ID is:", admin_id)
        print("\n➜ Please remember your Admin ID for login.")

        return admin_id

    except Exception as e:
        if conn:
            conn.rollback()

        print("\n✗ Admin registration failed:", e)
        return None

    finally:
        if cursor:
            cursor.close()

        if conn:
            conn.close()


def admin_login():
    print("\n" + "=" * 60)
    print("🔐 ADMIN LOGIN".center(60))
    print("=" * 60)

    conn = None
    cursor = None

    try:
        conn = get_connection()

        if conn is None:
            print("\n✗ Unable to connect to database.")
            return None

        cursor = conn.cursor()

        show_guidelines(
            "ADMIN ID",
            [
                "Enter the Admin ID generated during registration.",
                "Enter only the numeric Admin ID."
            ]
        )
        admin_id = get_non_empty_input("\n➜ Enter Admin ID: ")

        if not admin_id.isdigit():
            print("\n✗ Admin ID must be a number.")
            return None

        admin_id = int(admin_id)

        show_guidelines(
            "ADMIN PASSWORD",
            [
                "Enter the password created during registration.",
                "You have a maximum of 5 incorrect password attempts."
            ]
        )
        password = get_non_empty_input("\n➜ Enter Password: ")

        cursor.execute(
            """
            SELECT password, admin_status,
                   failed_login_attempts, locked_until
            FROM Admin
            WHERE admin_id = %s
            """,
            (admin_id,)
        )

        admin = cursor.fetchone()

        if admin is None:
            print("\n✗ Admin account not found.")
            return None

        stored_password = admin[0]
        admin_status = admin[1]
        failed_attempts = admin[2]
        locked_until = admin[3]

        if admin_status != "ACTIVE":
            print("\n⚠ Your Admin account is not ACTIVE.")
            return None

        if locked_until is not None:
            if locked_until > datetime.now():
                print("\n⚠ Your account is temporarily locked.")
                print("➜ Try again after:", locked_until)
                return None

            cursor.execute(
                """
                UPDATE Admin
                SET failed_login_attempts = 0,
                    locked_until = NULL
                WHERE admin_id = %s
                """,
                (admin_id,)
            )

            conn.commit()
            failed_attempts = 0

        if password == stored_password:
            cursor.execute(
                """
                UPDATE Admin
                SET failed_login_attempts = 0,
                    locked_until = NULL
                WHERE admin_id = %s
                """,
                (admin_id,)
            )

            conn.commit()

            print("\n" + "=" * 60)
            print("✓ ADMIN LOGIN SUCCESSFUL!".center(60))
            print("=" * 60)

            return admin_id

        failed_attempts += 1

        if failed_attempts >= 5:
            cursor.execute(
                """
                UPDATE Admin
                SET failed_login_attempts = 0,
                    locked_until = DATE_ADD(NOW(), INTERVAL 5 MINUTE)
                WHERE admin_id = %s
                """,
                (admin_id,)
            )

            conn.commit()

            print("\n✗ Too many incorrect attempts.")
            print("⚠ Your account is locked for 5 minutes.")

        else:
            cursor.execute(
                """
                UPDATE Admin
                SET failed_login_attempts = %s
                WHERE admin_id = %s
                """,
                (failed_attempts, admin_id)
            )

            conn.commit()

            print("\n✗ Incorrect Password.")
            print("⚠ Remaining attempts:", 5 - failed_attempts)

        return None

    except Exception as e:
        if conn:
            conn.rollback()

        print("\n✗ Admin login failed:", e)
        return None

    finally:
        if cursor:
            cursor.close()

        if conn:
            conn.close()


def display_users():
    conn = None
    cursor = None

    try:
        conn = get_connection()

        if conn is None:
            print("\n✗ Unable to connect to database.")
            return None

        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT user_id, full_name, college_id,
                   email, phone, account_status
            FROM Users
            ORDER BY user_id
            """
        )

        users = cursor.fetchall()

        print("\n" + "=" * 60)
        print("👥 REGISTERED USERS".center(60))
        print("=" * 60)

        if not users:
            print("\n⚠ No users found.")
            return []

        for user in users:
            print("\n" + "-" * 60)

            print("  User ID        :", user[0])
            print("  Name           :", user[1])
            print("  College ID     :", user[2])
            print("  Email          :", user[3])
            print("  Phone          :", user[4])
            print("  Account Status :", user[5])

        print("\n" + "=" * 60)

        return users

    except Exception as e:
        print("\n✗ Unable to display users:", e)
        return None

    finally:
        if cursor:
            cursor.close()

        if conn:
            conn.close()


def manage_users(admin_id):
    print("\n" + "=" * 60)
    print("👥 MANAGE USERS".center(60))
    print("=" * 60)

    users = display_users()

    if not users:
        print("\n⚠ No users available to manage.")
        return

    show_guidelines(
        "USER ID",
        [
            "Enter the User ID shown in the registered users list.",
            "Enter only the numeric User ID."
        ]
    )
    user_id = get_non_empty_input("\n➜ Enter User ID to manage: ")

    user_found = False

    for user in users:
        if str(user[0]) == user_id:
            user_found = True
            break

    if not user_found:
        print("\n✗ User not found.")
        return

    new_status = get_admin_status()

    conn = None
    cursor = None

    try:
        conn = get_connection()

        if conn is None:
            print("\n✗ Unable to connect to database.")
            return

        cursor = conn.cursor()

        cursor.execute(
            """
            UPDATE Users
            SET account_status = %s
            WHERE user_id = %s
            """,
            (new_status, user_id)
        )

        if cursor.rowcount == 0:
            conn.commit()
            print("\n⚠ User account status is already set to this status.")
            return

        conn.commit()

        print("\n✓ User account status updated successfully.")

        add_audit_record(
            admin_id,
            "USER_STATUS_UPDATED",
            "User ID: " + user_id + ", New Status: " + new_status
        )

    except Exception as e:
        if conn:
            conn.rollback()

        print("\n✗ Unable to update user:", e)

    finally:
        if cursor:
            cursor.close()

        if conn:
            conn.close()


def display_vehicles():
    conn = None
    cursor = None

    try:
        conn = get_connection()

        if conn is None:
            print("\n✗ Unable to connect to database.")
            return None

        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT v.vehicle_id, v.owner_id,
                   u.full_name, v.vehicle_name,
                   v.registration_number,
                   v.seating_capacity, v.vehicle_status
            FROM Vehicles v
            LEFT JOIN Users u
            ON v.owner_id = u.user_id
            ORDER BY v.vehicle_id
            """
        )

        vehicles = cursor.fetchall()

        print("\n" + "=" * 60)
        print("🚘 REGISTERED VEHICLES".center(60))
        print("=" * 60)

        if not vehicles:
            print("\n⚠ No vehicles found.")
            return []

        for vehicle in vehicles:
            print("\n" + "-" * 60)

            print("  Vehicle ID          :", vehicle[0])
            print("  Owner ID            :", vehicle[1])
            print("  Owner Name          :", vehicle[2])
            print("  Vehicle Name        :", vehicle[3])
            print("  Registration Number :", vehicle[4])
            print("  Seating Capacity    :", vehicle[5])
            print("  Vehicle Status      :", vehicle[6])

        print("\n" + "=" * 60)

        return vehicles

    except Exception as e:
        print("\n✗ Unable to display vehicles:", e)
        return None

    finally:
        if cursor:
            cursor.close()

        if conn:
            conn.close()


def manage_vehicles(admin_id):
    print("\n" + "=" * 60)
    print("🚘 MANAGE VEHICLES".center(60))
    print("=" * 60)

    vehicles = display_vehicles()

    if not vehicles:
        print("\n⚠ No vehicles available to manage.")
        return

    show_guidelines(
        "VEHICLE ID",
        [
            "Enter the Vehicle ID shown in the registered vehicles list.",
            "Enter only the numeric Vehicle ID."
        ]
    )
    vehicle_id = get_non_empty_input("\n➜ Enter Vehicle ID to manage: ")

    vehicle_found = False

    for vehicle in vehicles:
        if str(vehicle[0]) == vehicle_id:
            vehicle_found = True
            break

    if not vehicle_found:
        print("\n✗ Vehicle not found.")
        return

    new_status = get_vehicle_status()

    conn = None
    cursor = None

    try:
        conn = get_connection()

        if conn is None:
            print("\n✗ Unable to connect to database.")
            return

        cursor = conn.cursor()

        cursor.execute(
            """
            UPDATE Vehicles
            SET vehicle_status = %s
            WHERE vehicle_id = %s
            """,
            (new_status, vehicle_id)
        )

        if cursor.rowcount == 0:
            conn.commit()
            print("\n⚠ Vehicle status is already set to this status.")
            return

        conn.commit()

        print("\n✓ Vehicle status updated successfully.")

        add_audit_record(
            admin_id,
            "VEHICLE_STATUS_UPDATED",
            "Vehicle ID: " + vehicle_id +
            ", New Status: " + new_status
        )

    except Exception as e:
        if conn:
            conn.rollback()

        print("\n✗ Unable to update vehicle:", e)

    finally:
        if cursor:
            cursor.close()

        if conn:
            conn.close()


def display_reports():
    conn = None
    cursor = None

    try:
        conn = get_connection()

        if conn is None:
            print("\n✗ Unable to connect to database.")
            return None

        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT report_id, reported_by, related_user_id,
                   ride_id, description, report_status,
                   admin_action, created_at
            FROM Reports
            ORDER BY created_at DESC
            """
        )

        reports = cursor.fetchall()

        print("\n" + "=" * 60)
        print("📋 REPORTS / COMPLAINTS".center(60))
        print("=" * 60)

        if not reports:
            print("\n⚠ No reports found.")
            return []

        for report in reports:
            print("\n" + "-" * 60)

            print("  Report ID       :", report[0])
            print("  Reported By     :", report[1])
            print("  Related User ID :", report[2])
            print("  Ride ID         :", report[3])
            print("  Description     :", report[4])
            print("  Report Status   :", report[5])
            print("  Admin Action    :", report[6])
            print("  Created At      :", report[7])

        print("\n" + "=" * 60)

        return reports

    except Exception as e:
        print("\n✗ Unable to display reports:", e)
        return None

    finally:
        if cursor:
            cursor.close()

        if conn:
            conn.close()


def manage_reports(admin_id):
    print("\n" + "=" * 60)
    print("📋 MANAGE REPORTS".center(60))
    print("=" * 60)

    reports = display_reports()

    if not reports:
        print("\n⚠ No reports available to manage.")
        return

    show_guidelines(
        "REPORT ID",
        [
            "Enter the Report ID shown in the reports list.",
            "Enter only the numeric Report ID."
        ]
    )
    report_id = get_non_empty_input("\n➜ Enter Report ID to manage: ")

    report_found = False

    for report in reports:
        if str(report[0]) == report_id:
            report_found = True
            break

    if not report_found:
        print("\n✗ Report not found.")
        return

    print("\n" + "=" * 60)
    print("SELECT REPORT STATUS".center(60))
    print("=" * 60)

    print("  1. PENDING")
    print("  2. UNDER_REVIEW")
    print("  3. RESOLVED")
    print("  4. REJECTED")

    show_guidelines(
        "REPORT STATUS SELECTION",
        [
            "Enter 1 for a pending report.",
            "Enter 2 if the report is under review.",
            "Enter 3 if the report has been resolved.",
            "Enter 4 if the report is rejected."
        ]
    )

    while True:
        choice = input("\n➜ Enter your choice (1-4): ").strip()

        if choice == "1":
            new_status = "PENDING"
            break
        elif choice == "2":
            new_status = "UNDER_REVIEW"
            break
        elif choice == "3":
            new_status = "RESOLVED"
            break
        elif choice == "4":
            new_status = "REJECTED"
            break
        else:
            print("\n⚠ Invalid choice. Try again.")

    show_guidelines(
        "ADMIN ACTION / REMARKS",
        [
            "Enter the action taken or remarks about this report.",
            "You may leave this field empty if there are no remarks."
        ]
    )
    admin_action = input("\n➜ Enter Admin Action / Remarks: ").strip()

    conn = None
    cursor = None

    try:
        conn = get_connection()

        if conn is None:
            print("\n✗ Unable to connect to database.")
            return

        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT report_id
            FROM Reports
            WHERE report_id = %s
            """,
            (report_id,)
        )

        if cursor.fetchone() is None:
            print("\n✗ Report not found.")
            return

        if new_status in ("RESOLVED", "REJECTED"):
            cursor.execute(
                """
                UPDATE Reports
                SET report_status = %s,
                    admin_action = %s,
                    resolved_at = NOW()
                WHERE report_id = %s
                """,
                (new_status, admin_action, report_id)
            )
        else:
            cursor.execute(
                """
                UPDATE Reports
                SET report_status = %s,
                    admin_action = %s,
                    resolved_at = NULL
                WHERE report_id = %s
                """,
                (new_status, admin_action, report_id)
            )

        conn.commit()

        print("\n✓ Report updated successfully.")

        add_audit_record(
            admin_id,
            "REPORT_UPDATED",
            "Report ID: " + report_id +
            ", New Status: " + new_status
        )

    except Exception as e:
        if conn:
            conn.rollback()

        print("\n✗ Unable to update report:", e)

    finally:
        if cursor:
            cursor.close()

        if conn:
            conn.close()


def view_driver_feedback():
    conn = None
    cursor = None

    try:
        conn = get_connection()

        if conn is None:
            print("\n✗ Unable to connect to database.")
            return

        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT rf.feedback_id,
                   rf.booking_id,
                   rf.ride_id,
                   rf.driver_id,
                   u.full_name,
                   rf.seeker_id,
                   rf.rating,
                   rf.comment,
                   rf.created_at
            FROM Ratings_Feedback rf
            LEFT JOIN Users u
            ON rf.driver_id = u.user_id
            ORDER BY rf.created_at DESC
            """
        )

        feedbacks = cursor.fetchall()

        print("\n" + "=" * 60)
        print("⭐ DRIVER FEEDBACK".center(60))
        print("=" * 60)

        if not feedbacks:
            print("\n⚠ No feedback available.")
            return

        for feedback in feedbacks:
            print("\n" + "-" * 60)

            print("  Feedback ID :", feedback[0])
            print("  Booking ID  :", feedback[1])
            print("  Ride ID     :", feedback[2])
            print("  Driver ID   :", feedback[3])
            print("  Driver Name :", feedback[4])
            print("  Seeker ID   :", feedback[5])
            print("  Rating      :", feedback[6], "/ 5")
            print("  Comment     :", feedback[7])
            print("  Date        :", feedback[8])

        print("\n" + "=" * 60)

    except Exception as e:
        print("\n✗ Unable to display feedback:", e)

    finally:
        if cursor:
            cursor.close()

        if conn:
            conn.close()


def monitor_ongoing_rides():
    conn = None
    cursor = None

    try:
        conn = get_connection()

        if conn is None:
            print("\n✗ Unable to connect to database.")
            return

        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT r.ride_id,
                   r.driver_id,
                   u.full_name,
                   r.vehicle_id,
                   lp.city,
                   lp.region,
                   lp.area,
                   lp.point_name,
                   ld.city,
                   ld.region,
                   ld.area,
                   ld.point_name,
                   r.ride_date,
                   r.ride_time,
                   r.total_seats,
                   r.available_seats,
                   r.price_per_seat,
                   r.ride_status
            FROM Rides r
            LEFT JOIN Users u
            ON r.driver_id = u.user_id
            LEFT JOIN Locations lp
            ON r.pickup_location_id = lp.location_id
            LEFT JOIN Locations ld
            ON r.destination_location_id = ld.location_id
            WHERE r.ride_status = 'ACTIVE'
            ORDER BY r.ride_date, r.ride_time
            """
        )

        rides = cursor.fetchall()

        print("\n" + "=" * 60)
        print("🚘 ACTIVE RIDES".center(60))
        print("=" * 60)

        if not rides:
            print("\n⚠ No active rides found.")
            return

        for ride in rides:
            print("\n" + "-" * 60)

            print("  Ride ID         :", ride[0])
            print("  Driver ID       :", ride[1])
            print("  Driver Name     :", ride[2])
            print("  Vehicle ID      :", ride[3])
            print("  Pickup          :", ride[4], ride[5], ride[6], ride[7])
            print("  Destination     :", ride[8], ride[9], ride[10], ride[11])
            print("  Ride Date       :", ride[12])
            print("  Ride Time       :", ride[13])
            print("  Total Seats     :", ride[14])
            print("  Available Seats :", ride[15])
            print("  Price Per Seat  : Rs.", ride[16])
            print("  Ride Status     :", ride[17])

        print("\n" + "=" * 60)

    except Exception as e:
        print("\n✗ Unable to monitor rides:", e)

    finally:
        if cursor:
            cursor.close()

        if conn:
            conn.close()


def admin_dashboard(admin_id):
    print("\n" + "=" * 60)
    print("✓ WELCOME TO THE ADMIN DASHBOARD".center(60))
    print("=" * 60)

    while True:
        print("\n")
        print("+" + "=" * 58 + "+")
        print("|" + "🛡 RIDESYNC - ADMIN DASHBOARD".center(58) + "|")
        print("+" + "=" * 58 + "+")
        print("|" + "  1. Manage Users".ljust(58) + "|")
        print("|" + "  2. Manage Vehicles".ljust(58) + "|")
        print("|" + "  3. Manage Reports / Complaints".ljust(58) + "|")
        print("|" + "  4. View Driver Feedback".ljust(58) + "|")
        print("|" + "  5. Monitor Active Rides".ljust(58) + "|")
        print("|" + "  6. Add New Admin".ljust(58) + "|")
        print("|" + "  7. Logout".ljust(58) + "|")
        print("+" + "=" * 58 + "+")

        show_guidelines(
            "ADMIN DASHBOARD MENU",
            [
                "Enter 1 to manage registered users.",
                "Enter 2 to manage registered vehicles.",
                "Enter 3 to manage reports and complaints.",
                "Enter 4 to view driver feedback.",
                "Enter 5 to monitor active rides.",
                "Enter 6 to register a new admin.",
                "Enter 7 to log out."
            ]
        )

        choice = input("\n➜ Enter your choice (1-7): ").strip()

        if choice == "1":
            manage_users(admin_id)

        elif choice == "2":
            manage_vehicles(admin_id)

        elif choice == "3":
            manage_reports(admin_id)

        elif choice == "4":
            view_driver_feedback()

        elif choice == "5":
            monitor_ongoing_rides()

        elif choice == "6":
            new_admin_id = admin_registration()

            if new_admin_id is not None:
                add_audit_record(
                    admin_id,
                    "NEW_ADMIN_REGISTERED",
                    "New Admin ID: " + str(new_admin_id)
                )

        elif choice == "7":
            add_audit_record(
                admin_id,
                "ADMIN_LOGOUT",
                "Admin logged out."
            )

            print("\n" + "=" * 60)
            print("✓ ADMIN LOGGED OUT SUCCESSFULLY".center(60))
            print("=" * 60)

            break

        else:
            print("\n✗ Invalid choice. Please try again.")


def admin_menu():
    if not portal_access():
        return

    while True:
        print("\n")
        print("+" + "=" * 58 + "+")
        print("|" + "🛡 RIDESYNC - ADMIN PORTAL".center(58) + "|")
        print("+" + "=" * 58 + "+")
        print("|" + "  1. Admin Registration".ljust(58) + "|")
        print("|" + "  2. Admin Login".ljust(58) + "|")
        print("|" + "  3. Back".ljust(58) + "|")
        print("+" + "=" * 58 + "+")

        show_guidelines(
            "ADMIN PORTAL MENU",
            [
                "Enter 1 to register a new admin.",
                "Enter 2 to log in to an existing admin account.",
                "Enter 3 to return to the Main Menu."
            ]
        )

        choice = input("\n➜ Enter your choice (1-3): ").strip()

        if choice == "1":
            admin_registration()

        elif choice == "2":
            admin_id = admin_login()

            if admin_id is not None:
                admin_dashboard(admin_id)

        elif choice == "3":
            print("\n➜ Returning to Main Menu.")
            break

        else:
            print("\n✗ Invalid choice. Please try again.")


if __name__ == "__main__":
    if ensure_database_ready():
        admin_menu()
    else:
        print("\n" + "=" * 60)
        print("✗ RIDESYNC DATABASE COULD NOT BE INITIALIZED".center(60))
        print("=" * 60)