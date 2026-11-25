"""Web-compatible business services preserving original RideSync backend logic."""

from datetime import date, datetime, time, timedelta
from decimal import Decimal, InvalidOperation

from web_database import db_cursor, is_mysql_error

PORTAL_ACCESS_PASSWORD = "1234"


def convert_mysql_time(value):
    """Convert MySQL TIME/timedelta/str into a Python datetime.time object."""
    if isinstance(value, timedelta):
        total_seconds = int(value.total_seconds()) % 86400
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        seconds = total_seconds % 60
        return time(hours, minutes, seconds)
    if isinstance(value, time):
        return value
    if isinstance(value, str):
        try:
            return datetime.strptime(value, "%H:%M:%S").time()
        except ValueError:
            return datetime.strptime(value, "%H:%M").time()
    return value


def format_time_hhmm(value):
    """Format a MySQL time/timedelta as HH:MM."""
    t = convert_mysql_time(value)
    return t.strftime("%H:%M") if isinstance(t, time) else str(value)


def calculate_total_fare(price_per_seat, seats):
    """Calculate total fare using Decimal precision."""
    return (Decimal(str(price_per_seat)) * Decimal(str(seats))).quantize(Decimal("0.01"))


def _get_time_difference_seconds(time1, time2):
    t1 = convert_mysql_time(time1)
    t2 = convert_mysql_time(time2)
    s1 = t1.hour * 3600 + t1.minute * 60 + t1.second
    s2 = t2.hour * 3600 + t2.minute * 60 + t2.second
    return abs(s1 - s2)


# ==============================================================================
# USER AUTHENTICATION & PROFILE (mirrors main.py)
# ==============================================================================

def register_user_service(full_name, college_id, email, phone, password, confirm_password):
    full_name = (full_name or "").strip()
    college_id = (college_id or "").strip()
    email = (email or "").strip().lower()
    phone = (phone or "").strip()
    password = password or ""
    confirm_password = confirm_password or ""

    if not full_name or not full_name.replace(" ", "").isalpha():
        return False, "Invalid Full Name. Only alphabets and spaces are allowed.", None

    if not (0 < len(college_id) <= 30):
        return False, "Invalid College ID. Must be 1 to 30 characters.", None

    if email.count("@") != 1:
        return False, "Invalid Email ID.", None

    if email.endswith("@gmail.com"):
        username = email[:-10]
    elif email.endswith("@bennett.edu.in"):
        username = email[:-15]
    else:
        return False, "Invalid Email ID. Use '@gmail.com' or '@bennett.edu.in'.", None

    if len(username) < 8 or not username.isalnum():
        return False, "Email username must have at least 8 alphanumeric characters.", None

    if len(phone) != 10 or not phone.isdigit():
        return False, "Invalid Phone Number. Enter exactly 10 digits.", None

    if len(password) < 8 or not (password.isalnum() and password.isascii() and any(ch.isalpha() for ch in password)):
        return False, "Password must be at least 8 ASCII alphanumeric characters with at least one letter.", None

    if password != confirm_password:
        return False, "Passwords do not match.", None

    try:
        with db_cursor() as (conn, cursor):
            conn.start_transaction()
            try:
                cursor.execute(
                    """
                    INSERT INTO Users (full_name, college_id, email, phone, password)
                    VALUES (%s, %s, %s, %s, %s)
                    """,
                    (full_name, college_id, email, phone, password),
                )
                user_id = cursor.lastrowid
                conn.commit()
                return True, f"Registration successful! Your User ID is {user_id}. You can now log in.", user_id
            except Exception as exc:
                conn.rollback()
                if is_mysql_error(exc) and exc.errno == 1062:
                    return False, "College ID, Email ID or Phone Number already exists.", None
                raise
    except ConnectionError as exc:
        return False, str(exc), None
    except Exception:
        return False, "Registration failed due to a database error.", None


def login_user_service(email, password):
    email = (email or "").strip().lower()
    password = password or ""

    if not email or not password:
        return False, "Email and password are required.", None

    try:
        with db_cursor(dictionary=True) as (conn, cursor):
            conn.start_transaction()
            try:
                cursor.execute(
                    """
                    SELECT user_id, full_name, password, account_status,
                           failed_login_attempts, locked_until
                    FROM Users
                    WHERE email = %s
                    FOR UPDATE
                    """,
                    (email,),
                )
                user = cursor.fetchone()

                if user is None:
                    conn.rollback()
                    return False, "Invalid Email ID.", None

                if user["account_status"] != "ACTIVE":
                    conn.rollback()
                    return False, "Your account is not ACTIVE. Please contact the administrator.", None

                current_time = datetime.now()
                locked_until = user["locked_until"]

                if locked_until is not None and locked_until > current_time:
                    conn.rollback()
                    remaining_minutes = int((locked_until - current_time).total_seconds() + 59) // 60
                    return False, f"Account temporarily locked. Please try again after {remaining_minutes} minutes.", None

                if locked_until is not None and locked_until <= current_time:
                    cursor.execute(
                        """
                        UPDATE Users
                        SET failed_login_attempts = 0,
                            locked_until = NULL
                        WHERE user_id = %s
                        """,
                        (user["user_id"],),
                    )
                    user["failed_login_attempts"] = 0

                if password == user["password"]:
                    cursor.execute(
                        """
                        UPDATE Users
                        SET failed_login_attempts = 0,
                            locked_until = NULL
                        WHERE user_id = %s
                        """,
                        (user["user_id"],),
                    )
                    conn.commit()
                    return True, "Login successful! Welcome to RideSync.", {
                        "user_id": user["user_id"],
                        "full_name": user["full_name"],
                    }

                attempts = (user["failed_login_attempts"] or 0) + 1
                if attempts >= 5:
                    lock_time = current_time + timedelta(minutes=15)
                    cursor.execute(
                        """
                        UPDATE Users
                        SET failed_login_attempts = 5,
                            locked_until = %s
                        WHERE user_id = %s
                        """,
                        (lock_time, user["user_id"]),
                    )
                    conn.commit()
                    return False, "Too many incorrect attempts. Your account is locked for 15 minutes.", None

                cursor.execute(
                    """
                    UPDATE Users
                    SET failed_login_attempts = %s
                    WHERE user_id = %s
                    """,
                    (attempts, user["user_id"]),
                )
                conn.commit()
                return False, f"Incorrect Password. Attempts remaining: {5 - attempts}.", None

            except Exception as exc:
                conn.rollback()
                if is_mysql_error(exc) and exc.errno == 1062:
                    return False, "Email or Phone number already exists."
                raise
    except ConnectionError as exc:
        return False, str(exc), None
    except Exception:
        return False, "Unable to process login due to a database error.", None


def get_user_profile(user_id):
    with db_cursor(dictionary=True) as (_conn, cursor):
        cursor.execute(
            """
            SELECT user_id, full_name, college_id, email, phone, account_status, created_at
            FROM Users
            WHERE user_id = %s
            """,
            (user_id,),
        )
        return cursor.fetchone()


def get_user_dashboard_stats(user_id):
    with db_cursor(dictionary=True) as (_conn, cursor):
        cursor.execute(
            """
            SELECT
                (SELECT COUNT(*) FROM Bookings WHERE seeker_id = %s AND booking_status = 'CONFIRMED') AS confirmed_bookings,
                (SELECT COUNT(*) FROM Ride_Requests WHERE seeker_id = %s AND request_status = 'PENDING') AS pending_sent_requests,
                (SELECT COUNT(*) FROM Rides WHERE driver_id = %s AND ride_status IN ('ACTIVE', 'FULL')) AS active_posted_rides,
                (
                    SELECT COUNT(*)
                    FROM Ride_Requests rr
                    JOIN Rides r ON rr.ride_id = r.ride_id
                    WHERE r.driver_id = %s AND rr.request_status = 'PENDING' AND r.ride_status = 'ACTIVE'
                ) AS incoming_requests,
                (SELECT COUNT(*) FROM Vehicles WHERE owner_id = %s AND vehicle_status = 'ACTIVE') AS active_vehicles
            """,
            (user_id, user_id, user_id, user_id, user_id),
        )
        return cursor.fetchone()


# ==============================================================================
# RIDE SEEKER SERVICES (mirrors ride_seeker.py)
# ==============================================================================

def get_active_locations():
    with db_cursor(dictionary=True) as (_conn, cursor):
        cursor.execute(
            """
            SELECT location_id, city, region, area, point_name
            FROM Locations
            WHERE is_active = TRUE
            ORDER BY city, area, point_name
            """
        )
        return cursor.fetchall()


def list_available_rides(user_id):
    with db_cursor(dictionary=True) as (_conn, cursor):
        cursor.execute(
            """
            SELECT
                r.ride_id,
                r.driver_id,
                r.ride_date,
                r.ride_time,
                r.total_seats,
                r.available_seats,
                r.price_per_seat,
                r.ride_status,
                u.full_name AS driver_name,
                v.vehicle_name,
                v.registration_number,
                lp.city AS pickup_city,
                lp.area AS pickup_area,
                lp.point_name AS pickup_point,
                ld.city AS destination_city,
                ld.area AS destination_area,
                ld.point_name AS destination_point,
                COALESCE(rating.average_rating, 0) AS average_rating,
                COALESCE(rating.total_ratings, 0) AS total_ratings
            FROM Rides r
            JOIN Users u ON r.driver_id = u.user_id
            JOIN Vehicles v ON r.vehicle_id = v.vehicle_id
            JOIN Locations lp ON r.pickup_location_id = lp.location_id
            JOIN Locations ld ON r.destination_location_id = ld.location_id
            LEFT JOIN (
                SELECT driver_id, AVG(rating) AS average_rating, COUNT(*) AS total_ratings
                FROM Ratings_Feedback
                GROUP BY driver_id
            ) rating ON rating.driver_id = r.driver_id
            WHERE r.ride_status = 'ACTIVE'
            AND r.available_seats > 0
            AND r.driver_id <> %s
            AND (
                r.ride_date > CURDATE()
                OR (r.ride_date = CURDATE() AND r.ride_time > CURTIME())
            )
            ORDER BY r.ride_date, r.ride_time
            """,
            (user_id,),
        )
        rides = cursor.fetchall()
        for r in rides:
            r["ride_time_fmt"] = format_time_hhmm(r["ride_time"])
        return rides


def search_matching_rides(user_id, pickup_id_str, dest_id_str, ride_date_str, ride_time_str, seats_str):
    if not (pickup_id_str or "").isdigit() or not (dest_id_str or "").isdigit():
        return False, "Please select valid pickup and destination locations.", []

    pickup_id = int(pickup_id_str)
    dest_id = int(dest_id_str)

    if pickup_id == dest_id:
        return False, "Pickup and destination cannot be the same.", []

    try:
        selected_date = datetime.strptime((ride_date_str or "").strip(), "%Y-%m-%d").date()
    except ValueError:
        return False, "Invalid date. Use YYYY-MM-DD.", []

    if selected_date < date.today():
        return False, "Past dates are not allowed.", []

    try:
        selected_time = datetime.strptime((ride_time_str or "").strip(), "%H:%M").time()
    except ValueError:
        return False, "Invalid time. Use 24-hour HH:MM format.", []

    if datetime.combine(selected_date, selected_time) <= datetime.now():
        return False, "Please enter a future date and time.", []

    if not (seats_str or "").isdigit():
        return False, "Required seats must be a positive integer.", []
    required_seats = int(seats_str)
    if not (1 <= required_seats <= 255):
        return False, "Required seats must be between 1 and 255.", []

    with db_cursor(dictionary=True) as (_conn, cursor):
        cursor.execute(
            """
            SELECT
                r.ride_id,
                r.driver_id,
                r.ride_date,
                r.ride_time,
                r.total_seats,
                r.available_seats,
                r.ride_status,
                r.price_per_seat,
                u.full_name AS driver_name,
                v.vehicle_name,
                v.registration_number,
                lp.city AS pickup_city,
                lp.area AS pickup_area,
                lp.point_name AS pickup_point,
                ld.city AS destination_city,
                ld.area AS destination_area,
                ld.point_name AS destination_point,
                COALESCE(rating.average_rating, 0) AS average_rating,
                COALESCE(rating.total_ratings, 0) AS total_ratings
            FROM Rides r
            JOIN Users u ON r.driver_id = u.user_id
            JOIN Vehicles v ON r.vehicle_id = v.vehicle_id
            JOIN Locations lp ON r.pickup_location_id = lp.location_id
            JOIN Locations ld ON r.destination_location_id = ld.location_id
            LEFT JOIN (
                SELECT driver_id, AVG(rating) AS average_rating, COUNT(*) AS total_ratings
                FROM Ratings_Feedback
                GROUP BY driver_id
            ) rating ON rating.driver_id = r.driver_id
            WHERE r.pickup_location_id = %s
            AND r.destination_location_id = %s
            AND r.ride_date = %s
            AND r.available_seats >= %s
            AND r.ride_status = 'ACTIVE'
            AND r.driver_id <> %s
            AND (
                r.ride_date > CURDATE()
                OR (r.ride_date = CURDATE() AND r.ride_time > CURTIME())
            )
            ORDER BY r.ride_time
            """,
            (pickup_id, dest_id, selected_date, required_seats, user_id),
        )
        rides = cursor.fetchall()

    matching = []
    for ride in rides:
        diff = _get_time_difference_seconds(ride["ride_time"], selected_time)
        if diff <= 1800:
            time_score = ((1800 - diff) / 1800) * 60
            rating_score = (float(ride["average_rating"]) / 5) * 40
            ride["time_difference_min"] = round(diff / 60, 1)
            ride["final_score"] = round(time_score + rating_score, 2)
            ride["estimated_total_fare"] = calculate_total_fare(ride["price_per_seat"], required_seats)
            ride["ride_time_fmt"] = format_time_hhmm(ride["ride_time"])
            matching.append(ride)

    matching.sort(key=lambda item: item["final_score"], reverse=True)
    return True, None, matching


def get_ride_details(ride_id):
    with db_cursor(dictionary=True) as (_conn, cursor):
        cursor.execute(
            """
            SELECT
                r.ride_id,
                r.driver_id,
                r.vehicle_id,
                r.ride_date,
                r.ride_time,
                r.total_seats,
                r.available_seats,
                r.price_per_seat,
                r.ride_status,
                u.full_name AS driver_name,
                v.vehicle_name,
                v.registration_number,
                v.seating_capacity,
                lp.city AS pickup_city,
                lp.region AS pickup_region,
                lp.area AS pickup_area,
                lp.point_name AS pickup_point,
                ld.city AS destination_city,
                ld.region AS destination_region,
                ld.area AS destination_area,
                ld.point_name AS destination_point,
                COALESCE(rating.average_rating, 0) AS average_rating,
                COALESCE(rating.total_ratings, 0) AS total_ratings
            FROM Rides r
            JOIN Users u ON r.driver_id = u.user_id
            JOIN Vehicles v ON r.vehicle_id = v.vehicle_id
            JOIN Locations lp ON r.pickup_location_id = lp.location_id
            JOIN Locations ld ON r.destination_location_id = ld.location_id
            LEFT JOIN (
                SELECT driver_id, AVG(rating) AS average_rating, COUNT(*) AS total_ratings
                FROM Ratings_Feedback
                GROUP BY driver_id
            ) rating ON rating.driver_id = r.driver_id
            WHERE r.ride_id = %s
            """,
            (ride_id,),
        )
        ride = cursor.fetchone()
        if ride:
            ride["ride_time_fmt"] = format_time_hhmm(ride["ride_time"])
        return ride


def request_ride_service(user_id, ride_id, seats_str, expected_price_str=None):
    if not (seats_str or "").isdigit():
        return False, "Seats requested must be a positive integer."
    seats_requested = int(seats_str)
    if seats_requested <= 0 or seats_requested > 255:
        return False, "Seats requested must be between 1 and 255."

    try:
        with db_cursor(dictionary=True) as (conn, cursor):
            conn.start_transaction()
            try:
                cursor.execute(
                    """
                    SELECT driver_id, available_seats, ride_status,
                           ride_date, ride_time, price_per_seat
                    FROM Rides
                    WHERE ride_id = %s
                    FOR UPDATE
                    """,
                    (ride_id,),
                )
                ride = cursor.fetchone()
                if ride is None:
                    conn.rollback()
                    return False, "Selected ride does not exist."

                if expected_price_str is not None and expected_price_str != "":
                    try:
                        if Decimal(str(ride["price_per_seat"])) != Decimal(str(expected_price_str)):
                            conn.rollback()
                            return False, "The ride price has changed. Please review the updated ride details and try again."
                    except InvalidOperation:
                        pass

                if ride["driver_id"] == user_id:
                    conn.rollback()
                    return False, "You cannot request your own ride."

                if ride["ride_status"] != "ACTIVE":
                    conn.rollback()
                    return False, "This ride is not accepting requests."

                if ride["available_seats"] < seats_requested:
                    conn.rollback()
                    return False, "Not enough seats are available."

                ride_dt = datetime.combine(ride["ride_date"], convert_mysql_time(ride["ride_time"]))
                if ride_dt <= datetime.now():
                    conn.rollback()
                    return False, "This ride is no longer available."

                cursor.execute(
                    """
                    SELECT request_id
                    FROM Ride_Requests
                    WHERE ride_id = %s
                    AND seeker_id = %s
                    AND request_status IN ('PENDING', 'ACCEPTED')
                    FOR UPDATE
                    """,
                    (ride_id, user_id),
                )
                if cursor.fetchone() is not None:
                    conn.rollback()
                    return False, "You already have an active request for this ride."

                cursor.execute(
                    """
                    INSERT INTO Ride_Requests (ride_id, seeker_id, seats_requested, request_status)
                    VALUES (%s, %s, %s, 'PENDING')
                    """,
                    (ride_id, user_id, seats_requested),
                )
                request_id = cursor.lastrowid
                conn.commit()
                return True, f"Ride request #{request_id} sent successfully! Waiting for driver response."
            except Exception as exc:
                conn.rollback()
                if is_mysql_error(exc) and exc.errno == 1062:
                    return False, "Email or Phone number already exists."
                raise
    except ConnectionError as exc:
        return False, str(exc)
    except Exception:
        return False, "Unable to submit ride request due to a database error."


def get_my_ride_requests(user_id):
    with db_cursor(dictionary=True) as (_conn, cursor):
        cursor.execute(
            """
            SELECT
                rr.request_id,
                rr.ride_id,
                u.full_name AS driver_name,
                rr.seats_requested,
                rr.request_status,
                rr.requested_at,
                rr.responded_at,
                r.ride_date,
                r.ride_time,
                r.price_per_seat,
                lp.city AS pickup_city,
                lp.area AS pickup_area,
                lp.point_name AS pickup_point,
                ld.city AS destination_city,
                ld.area AS destination_area,
                ld.point_name AS destination_point
            FROM Ride_Requests rr
            JOIN Rides r ON rr.ride_id = r.ride_id
            JOIN Users u ON r.driver_id = u.user_id
            JOIN Locations lp ON r.pickup_location_id = lp.location_id
            JOIN Locations ld ON r.destination_location_id = ld.location_id
            WHERE rr.seeker_id = %s
            ORDER BY rr.requested_at DESC
            """,
            (user_id,),
        )
        rows = cursor.fetchall()
        for r in rows:
            r["ride_time_fmt"] = format_time_hhmm(r["ride_time"])
            r["total_fare"] = calculate_total_fare(r["price_per_seat"], r["seats_requested"])
        return rows


def get_my_bookings(user_id):
    with db_cursor(dictionary=True) as (_conn, cursor):
        cursor.execute(
            """
            SELECT
                b.booking_id,
                b.ride_id,
                b.seats_booked,
                b.booking_status,
                b.booked_at,
                b.cancelled_at,
                r.ride_date,
                r.ride_time,
                r.ride_status,
                r.price_per_seat,
                u.full_name AS driver_name,
                u.email AS driver_email,
                u.phone AS driver_phone,
                v.vehicle_name,
                v.registration_number,
                lp.city AS pickup_city,
                lp.area AS pickup_area,
                lp.point_name AS pickup_point,
                ld.city AS destination_city,
                ld.area AS destination_area,
                ld.point_name AS destination_point,
                r.driver_id
            FROM Bookings b
            JOIN Rides r ON b.ride_id = r.ride_id
            JOIN Users u ON r.driver_id = u.user_id
            JOIN Vehicles v ON r.vehicle_id = v.vehicle_id
            JOIN Locations lp ON r.pickup_location_id = lp.location_id
            JOIN Locations ld ON r.destination_location_id = ld.location_id
            WHERE b.seeker_id = %s
            ORDER BY b.booked_at DESC
            """,
            (user_id,),
        )
        rows = cursor.fetchall()
        now = datetime.now()
        for b in rows:
            b["ride_time_fmt"] = format_time_hhmm(b["ride_time"])
            b["total_fare"] = calculate_total_fare(b["price_per_seat"], b["seats_booked"])
            ride_dt = datetime.combine(b["ride_date"], convert_mysql_time(b["ride_time"]))
            b["can_cancel"] = (
                b["booking_status"] == "CONFIRMED"
                and b["ride_status"] not in ("COMPLETED", "CANCELLED")
                and ride_dt > now
            )
        return rows


def cancel_booking_service(user_id, booking_id):
    try:
        with db_cursor(dictionary=True) as (conn, cursor):
            conn.start_transaction()
            try:
                cursor.execute(
                    """
                    SELECT ride_id, seats_booked, booking_status
                    FROM Bookings
                    WHERE booking_id = %s AND seeker_id = %s
                    FOR UPDATE
                    """,
                    (booking_id, user_id),
                )
                current_booking = cursor.fetchone()
                if current_booking is None or current_booking["booking_status"] != "CONFIRMED":
                    conn.rollback()
                    return False, "This booking is no longer available for cancellation."

                ride_id = current_booking["ride_id"]
                seats_booked = current_booking["seats_booked"]

                cursor.execute(
                    """
                    SELECT total_seats, available_seats, ride_status, ride_date, ride_time
                    FROM Rides
                    WHERE ride_id = %s
                    FOR UPDATE
                    """,
                    (ride_id,),
                )
                ride = cursor.fetchone()
                if ride is None:
                    conn.rollback()
                    return False, "Related ride was not found."

                ride_dt = datetime.combine(ride["ride_date"], convert_mysql_time(ride["ride_time"]))
                if ride["ride_status"] in ("COMPLETED", "CANCELLED") or ride_dt <= datetime.now():
                    conn.rollback()
                    return False, "This ride can no longer be cancelled."

                cursor.execute(
                    """
                    UPDATE Bookings
                    SET booking_status = 'CANCELLED',
                        cancelled_at = NOW()
                    WHERE booking_id = %s
                    AND seeker_id = %s
                    AND booking_status = 'CONFIRMED'
                    """,
                    (booking_id, user_id),
                )
                if cursor.rowcount != 1:
                    conn.rollback()
                    return False, "Booking cancellation failed."

                new_available = min(ride["total_seats"], ride["available_seats"] + seats_booked)
                new_status = "ACTIVE" if new_available > 0 else "FULL"

                cursor.execute(
                    """
                    UPDATE Rides
                    SET available_seats = %s,
                        ride_status = %s
                    WHERE ride_id = %s
                    AND ride_status IN ('ACTIVE', 'FULL')
                    """,
                    (new_available, new_status, ride_id),
                )
                conn.commit()
                return True, f"Booking #{booking_id} cancelled successfully. {seats_booked} seat(s) restored."
            except Exception as exc:
                conn.rollback()
                if is_mysql_error(exc) and exc.errno == 1062:
                    return False, "Email or Phone number already exists."
                raise
    except ConnectionError as exc:
        return False, str(exc)
    except Exception:
        return False, "Unable to cancel booking due to a database error."


def get_driver_details_for_booking(user_id, booking_id):
    with db_cursor(dictionary=True) as (_conn, cursor):
        cursor.execute(
            """
            SELECT
                b.booking_id,
                b.ride_id,
                b.booking_status,
                u.full_name,
                u.email,
                u.phone,
                v.vehicle_name,
                v.registration_number
            FROM Bookings b
            JOIN Rides r ON b.ride_id = r.ride_id
            JOIN Users u ON r.driver_id = u.user_id
            JOIN Vehicles v ON r.vehicle_id = v.vehicle_id
            WHERE b.booking_id = %s AND b.seeker_id = %s
            """,
            (booking_id, user_id),
        )
        return cursor.fetchone()


def get_eligible_feedback_bookings(user_id):
    with db_cursor(dictionary=True) as (_conn, cursor):
        cursor.execute(
            """
            SELECT
                b.booking_id,
                b.ride_id,
                u.full_name AS driver_name,
                r.ride_date,
                r.ride_status
            FROM Bookings b
            JOIN Rides r ON b.ride_id = r.ride_id
            JOIN Users u ON r.driver_id = u.user_id
            LEFT JOIN Ratings_Feedback rf ON rf.booking_id = b.booking_id
            WHERE b.seeker_id = %s
            AND b.booking_status = 'COMPLETED'
            AND r.ride_status = 'COMPLETED'
            AND rf.feedback_id IS NULL
            ORDER BY r.ride_date DESC
            """,
            (user_id,),
        )
        return cursor.fetchall()


def submit_feedback_service(user_id, booking_id_str, rating_str, comment):
    if not (booking_id_str or "").isdigit():
        return False, "Please select a valid booking."
    booking_id = int(booking_id_str)

    if not (rating_str or "").isdigit():
        return False, "Rating must be a number between 1 and 5."
    rating = int(rating_str)
    if not (1 <= rating <= 5):
        return False, "Rating must be between 1 and 5."

    comment = (comment or "").strip()
    if len(comment) > 1000:
        return False, "Feedback cannot exceed 1000 characters."

    try:
        with db_cursor(dictionary=True) as (conn, cursor):
            conn.start_transaction()
            try:
                cursor.execute(
                    """
                    SELECT b.ride_id, b.booking_status, r.driver_id, r.ride_status
                    FROM Bookings b
                    JOIN Rides r ON b.ride_id = r.ride_id
                    WHERE b.booking_id = %s AND b.seeker_id = %s
                    FOR UPDATE
                    """,
                    (booking_id, user_id),
                )
                current_booking = cursor.fetchone()
                if (
                    current_booking is None
                    or current_booking["booking_status"] != "COMPLETED"
                    or current_booking["ride_status"] != "COMPLETED"
                ):
                    conn.rollback()
                    return False, "This booking is not eligible for feedback."

                cursor.execute(
                    """
                    INSERT INTO Ratings_Feedback (booking_id, ride_id, driver_id, seeker_id, rating, comment)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    """,
                    (
                        booking_id,
                        current_booking["ride_id"],
                        current_booking["driver_id"],
                        user_id,
                        rating,
                        comment if comment else None,
                    ),
                )
                conn.commit()
                return True, "Feedback submitted successfully! Thank you for sharing your experience."
            except Exception as exc:
                conn.rollback()
                if is_mysql_error(exc) and exc.errno == 1062:
                    return False, "Feedback has already been submitted for this booking."
                raise
    except ConnectionError as exc:
        return False, str(exc)
    except Exception:
        return False, "Unable to submit feedback due to a database error."


# ==============================================================================
# RIDE GIVER SERVICES (mirrors ride_giver.py)
# ==============================================================================

def get_user_vehicles(user_id):
    with db_cursor(dictionary=True) as (_conn, cursor):
        cursor.execute(
            """
            SELECT vehicle_id, vehicle_name, registration_number, seating_capacity, vehicle_status, created_at
            FROM Vehicles
            WHERE owner_id = %s
            ORDER BY vehicle_status ASC, vehicle_id ASC
            """,
            (user_id,),
        )
        return cursor.fetchall()


def register_vehicle_service(user_id, vehicle_name, registration_number, seating_capacity_str):
    vehicle_name = (vehicle_name or "").strip()
    registration_number = (registration_number or "").strip().upper()
    seating_capacity_str = (seating_capacity_str or "").strip()

    if not (0 < len(vehicle_name) <= 80 and any(ch.isalnum() for ch in vehicle_name)):
        return False, "Invalid Vehicle Name. Must be 1 to 80 characters and contain letters or numbers."

    if not (0 < len(registration_number) <= 20 and registration_number.isalnum()):
        return False, "Invalid Registration Number. Up to 20 alphanumeric characters, no spaces or symbols."

    if not seating_capacity_str.isdigit():
        return False, "Seating capacity must be a positive integer."
    seating_capacity = int(seating_capacity_str)
    if not (1 <= seating_capacity <= 255):
        return False, "Seating capacity must be between 1 and 255."

    try:
        with db_cursor() as (conn, cursor):
            conn.start_transaction()
            try:
                cursor.execute(
                    """
                    INSERT INTO Vehicles (owner_id, vehicle_name, registration_number, seating_capacity)
                    VALUES (%s, %s, %s, %s)
                    """,
                    (user_id, vehicle_name, registration_number, seating_capacity),
                )
                conn.commit()
                return True, f"Vehicle '{vehicle_name}' ({registration_number}) registered successfully!"
            except Exception as exc:
                conn.rollback()
                if is_mysql_error(exc) and exc.errno == 1062:
                    return False, "This vehicle registration number is already registered."
                raise
    except ConnectionError as exc:
        return False, str(exc)
    except Exception:
        return False, "Unable to register vehicle due to a database error."


def remove_vehicle_service(user_id, vehicle_id):
    try:
        with db_cursor() as (conn, cursor):
            conn.start_transaction()
            try:
                cursor.execute(
                    """
                    UPDATE Vehicles
                    SET vehicle_status = 'INACTIVE'
                    WHERE vehicle_id = %s AND owner_id = %s AND vehicle_status = 'ACTIVE'
                    """,
                    (vehicle_id, user_id),
                )
                if cursor.rowcount == 1:
                    conn.commit()
                    return True, "Vehicle marked as INACTIVE successfully. Existing posted rides are preserved."
                conn.rollback()
                return False, "Vehicle could not be removed or is already inactive."
            except Exception as exc:
                conn.rollback()
                if is_mysql_error(exc) and exc.errno == 1062:
                    return False, "Email or Phone number already exists."
                raise
    except ConnectionError as exc:
        return False, str(exc)
    except Exception:
        return False, "Unable to remove vehicle due to a database error."


def _validate_new_location_tuple(city, region, area, point_name):
    city = (city or "").strip()
    region = (region or "").strip()
    area = (area or "").strip()
    point_name = (point_name or "").strip()

    if not (0 < len(city) <= 80 and any(ch.isalpha() for ch in city)):
        return False, "Invalid City. Must be 1 to 80 characters with at least one letter.", None
    if len(region) > 80:
        return False, "Region cannot exceed 80 characters.", None
    if region == "":
        region = None
    if not (0 < len(area) <= 100 and any(ch.isalnum() for ch in area)):
        return False, "Invalid Area. Must be 1 to 100 characters.", None
    if not (0 < len(point_name) <= 150 and any(ch.isalnum() for ch in point_name)):
        return False, "Invalid Pickup/Drop Point Name. Must be 1 to 150 characters.", None

    return True, None, (city, region, area, point_name)


def _get_or_create_location(cursor, location_tuple):
    city, region, area, point_name = location_tuple
    cursor.execute(
        """
        SELECT location_id, is_active
        FROM Locations
        WHERE LOWER(city) = LOWER(%s)
        AND region <=> %s
        AND LOWER(area) = LOWER(%s)
        AND LOWER(point_name) = LOWER(%s)
        """,
        (city, region, area, point_name),
    )
    result = cursor.fetchone()
    if result is not None:
        loc_id = result[0]
        if not result[1]:
            cursor.execute("UPDATE Locations SET is_active = TRUE WHERE location_id = %s", (loc_id,))
        return loc_id

    cursor.execute(
        "INSERT INTO Locations (city, region, area, point_name) VALUES (%s, %s, %s, %s)",
        (city, region, area, point_name),
    )
    return cursor.lastrowid


def post_ride_service(
    user_id,
    vehicle_id_str,
    pickup_choice,
    new_pickup_data,
    dest_choice,
    new_dest_data,
    ride_date_str,
    ride_time_str,
    seats_str,
    price_str,
):
    if not (vehicle_id_str or "").isdigit():
        return False, "Please select a valid active vehicle."
    vehicle_id = int(vehicle_id_str)

    try:
        selected_date = datetime.strptime((ride_date_str or "").strip(), "%Y-%m-%d").date()
    except ValueError:
        return False, "Invalid Ride Date. Use YYYY-MM-DD."
    if selected_date < date.today():
        return False, "Past dates are not allowed."

    try:
        selected_time = datetime.strptime((ride_time_str or "").strip(), "%H:%M").time()
    except ValueError:
        return False, "Invalid Ride Time. Use 24-hour HH:MM format."
    if datetime.combine(selected_date, selected_time) <= datetime.now():
        return False, "Please enter a future date and time."

    if not (seats_str or "").isdigit():
        return False, "Available passenger seats must be a positive integer."
    available_seats = int(seats_str)

    try:
        price = Decimal((price_str or "").strip())
        if not price.is_finite() or not (Decimal("0") < price <= Decimal("99999999.99")):
            return False, "Price per seat must be greater than zero and at most Rs. 99999999.99."
        price = price.quantize(Decimal("0.01"))
    except InvalidOperation:
        return False, "Invalid price. Enter a valid number."

    pickup_tuple = None
    if pickup_choice == "__new__":
        ok, err, pickup_tuple = _validate_new_location_tuple(**new_pickup_data)
        if not ok:
            return False, f"Pickup location: {err}"
    elif not (pickup_choice or "").isdigit():
        return False, "Please select a valid pickup location."

    dest_tuple = None
    if dest_choice == "__new__":
        ok, err, dest_tuple = _validate_new_location_tuple(**new_dest_data)
        if not ok:
            return False, f"Destination location: {err}"
    elif not (dest_choice or "").isdigit():
        return False, "Please select a valid destination location."

    try:
        with db_cursor() as (conn, cursor):
            conn.start_transaction()
            try:
                cursor.execute(
                    """
                    SELECT seating_capacity
                    FROM Vehicles
                    WHERE vehicle_id = %s AND owner_id = %s AND vehicle_status = 'ACTIVE'
                    FOR UPDATE
                    """,
                    (vehicle_id, user_id),
                )
                vehicle = cursor.fetchone()
                if vehicle is None:
                    conn.rollback()
                    return False, "Selected vehicle is not active or does not belong to you."

                if not (1 <= available_seats <= vehicle[0]):
                    conn.rollback()
                    return False, f"Passenger seats must be between 1 and {vehicle[0]}."

                pickup_id = _get_or_create_location(cursor, pickup_tuple) if pickup_tuple else int(pickup_choice)
                dest_id = _get_or_create_location(cursor, dest_tuple) if dest_tuple else int(dest_choice)

                if pickup_id == dest_id:
                    conn.rollback()
                    return False, "Pickup and destination cannot be the same."

                cursor.execute(
                    """
                    INSERT INTO Rides (
                        driver_id, vehicle_id, pickup_location_id, destination_location_id,
                        ride_date, ride_time, total_seats, available_seats, price_per_seat, ride_status
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, 'ACTIVE')
                    """,
                    (
                        user_id,
                        vehicle_id,
                        pickup_id,
                        dest_id,
                        selected_date,
                        selected_time,
                        available_seats,
                        available_seats,
                        price,
                    ),
                )
                ride_id = cursor.lastrowid
                conn.commit()
                return True, f"Ride #{ride_id} posted successfully!"
            except Exception as exc:
                conn.rollback()
                if is_mysql_error(exc) and exc.errno == 1062:
                    return False, "Email or Phone number already exists."
                raise
    except ConnectionError as exc:
        return False, str(exc)
    except Exception:
        return False, "Unable to post ride due to a database error."


def get_my_posted_rides(user_id):
    with db_cursor(dictionary=True) as (_conn, cursor):
        cursor.execute(
            """
            SELECT
                r.ride_id,
                v.vehicle_name,
                v.registration_number,
                lp.city AS pickup_city,
                lp.area AS pickup_area,
                lp.point_name AS pickup_point,
                ld.city AS destination_city,
                ld.area AS destination_area,
                ld.point_name AS destination_point,
                r.ride_date,
                r.ride_time,
                r.total_seats,
                r.available_seats,
                r.ride_status,
                r.price_per_seat
            FROM Rides r
            JOIN Vehicles v ON r.vehicle_id = v.vehicle_id
            JOIN Locations lp ON r.pickup_location_id = lp.location_id
            JOIN Locations ld ON r.destination_location_id = ld.location_id
            WHERE r.driver_id = %s
            AND r.ride_status IN ('ACTIVE', 'FULL')
            ORDER BY r.ride_date, r.ride_time
            """,
            (user_id,),
        )
        rows = cursor.fetchall()
        for r in rows:
            r["ride_time_fmt"] = format_time_hhmm(r["ride_time"])
            r["can_update"] = r["ride_date"] >= date.today()
        return rows


def get_giver_ride_history(user_id):
    with db_cursor(dictionary=True) as (_conn, cursor):
        cursor.execute(
            """
            SELECT
                r.ride_id,
                v.vehicle_name,
                v.registration_number,
                lp.city AS pickup_city,
                lp.area AS pickup_area,
                lp.point_name AS pickup_point,
                ld.city AS destination_city,
                ld.area AS destination_area,
                ld.point_name AS destination_point,
                r.ride_date,
                r.ride_time,
                r.total_seats,
                r.available_seats,
                r.ride_status,
                r.price_per_seat
            FROM Rides r
            JOIN Vehicles v ON r.vehicle_id = v.vehicle_id
            JOIN Locations lp ON r.pickup_location_id = lp.location_id
            JOIN Locations ld ON r.destination_location_id = ld.location_id
            WHERE r.driver_id = %s
            ORDER BY r.ride_date DESC, r.ride_time DESC
            """,
            (user_id,),
        )
        rows = cursor.fetchall()
        for r in rows:
            r["ride_time_fmt"] = format_time_hhmm(r["ride_time"])
        return rows


def get_incoming_ride_requests(user_id):
    with db_cursor(dictionary=True) as (_conn, cursor):
        cursor.execute(
            """
            SELECT
                rr.request_id,
                rr.ride_id,
                u.full_name AS passenger_name,
                u.email AS passenger_email,
                rr.seats_requested,
                r.available_seats,
                r.ride_date,
                r.ride_time,
                r.price_per_seat,
                lp.city AS pickup_city,
                lp.point_name AS pickup_point,
                ld.city AS destination_city,
                ld.point_name AS destination_point
            FROM Ride_Requests rr
            JOIN Rides r ON rr.ride_id = r.ride_id
            JOIN Users u ON rr.seeker_id = u.user_id
            JOIN Locations lp ON r.pickup_location_id = lp.location_id
            JOIN Locations ld ON r.destination_location_id = ld.location_id
            WHERE r.driver_id = %s
            AND rr.request_status = 'PENDING'
            AND r.ride_status = 'ACTIVE'
            ORDER BY r.ride_date, r.ride_time
            """,
            (user_id,),
        )
        rows = cursor.fetchall()
        for r in rows:
            r["ride_time_fmt"] = format_time_hhmm(r["ride_time"])
        return rows


def respond_to_ride_request_service(user_id, request_id, action):
    if action not in ("accept", "reject"):
        return False, "Invalid request action."

    try:
        with db_cursor() as (conn, cursor):
            conn.start_transaction()
            try:
                cursor.execute(
                    """
                    SELECT ride_id, seeker_id, seats_requested, request_status
                    FROM Ride_Requests
                    WHERE request_id = %s
                    FOR UPDATE
                    """,
                    (request_id,),
                )
                req_row = cursor.fetchone()
                if req_row is None or req_row[3] != "PENDING":
                    conn.rollback()
                    return False, "This request is no longer pending."

                ride_id, seeker_id, seats_requested, _ = req_row

                cursor.execute(
                    """
                    SELECT driver_id, available_seats, ride_status
                    FROM Rides
                    WHERE ride_id = %s
                    FOR UPDATE
                    """,
                    (ride_id,),
                )
                ride = cursor.fetchone()
                if ride is None or ride[0] != user_id:
                    conn.rollback()
                    return False, "You cannot manage this ride request."

                if action == "accept":
                    if ride[2] != "ACTIVE":
                        conn.rollback()
                        return False, "This ride is not accepting requests."
                    if ride[1] < seats_requested:
                        conn.rollback()
                        return False, "Not enough available seats."

                    cursor.execute(
                        """
                        INSERT INTO Bookings (request_id, ride_id, seeker_id, seats_booked, booking_status)
                        VALUES (%s, %s, %s, %s, 'CONFIRMED')
                        """,
                        (request_id, ride_id, seeker_id, seats_requested),
                    )
                    cursor.execute(
                        """
                        UPDATE Ride_Requests
                        SET request_status = 'ACCEPTED',
                            responded_at = NOW()
                        WHERE request_id = %s
                        """,
                        (request_id,),
                    )
                    new_available = ride[1] - seats_requested
                    new_status = "FULL" if new_available == 0 else "ACTIVE"
                    cursor.execute(
                        """
                        UPDATE Rides
                        SET available_seats = %s,
                            ride_status = %s
                        WHERE ride_id = %s
                        """,
                        (new_available, new_status, ride_id),
                    )
                    conn.commit()
                    return True, f"Ride request #{request_id} accepted! Booking confirmed. Remaining seats: {new_available}."

                cursor.execute(
                    """
                    UPDATE Ride_Requests
                    SET request_status = 'REJECTED',
                        responded_at = NOW()
                    WHERE request_id = %s
                    """,
                    (request_id,),
                )
                conn.commit()
                return True, f"Ride request #{request_id} rejected."
            except Exception as exc:
                conn.rollback()
                if is_mysql_error(exc) and exc.errno == 1062:
                    return False, "Email or Phone number already exists."
                raise
    except ConnectionError as exc:
        return False, str(exc)
    except Exception:
        return False, "Unable to process ride request due to a database error."


def get_updatable_ride(user_id, ride_id):
    with db_cursor(dictionary=True) as (_conn, cursor):
        cursor.execute(
            """
            SELECT
                r.ride_id,
                r.pickup_location_id,
                r.destination_location_id,
                r.ride_date,
                r.ride_time,
                r.total_seats,
                r.available_seats,
                r.ride_status,
                v.seating_capacity,
                v.vehicle_name,
                v.registration_number,
                r.price_per_seat
            FROM Rides r
            JOIN Vehicles v ON r.vehicle_id = v.vehicle_id
            WHERE r.ride_id = %s
            AND r.driver_id = %s
            AND r.ride_status IN ('ACTIVE', 'FULL')
            AND r.ride_date >= CURDATE()
            """,
            (ride_id, user_id),
        )
        ride = cursor.fetchone()
        if not ride:
            return None

        cursor.execute(
            "SELECT COUNT(*) AS cnt FROM Bookings WHERE ride_id = %s AND booking_status = 'CONFIRMED'",
            (ride_id,),
        )
        ride["confirmed_bookings"] = cursor.fetchone()["cnt"]
        ride["booked_seats"] = ride["total_seats"] - ride["available_seats"]
        ride["ride_time_fmt"] = format_time_hhmm(ride["ride_time"])
        return ride


def update_ride_service(user_id, ride_id, update_type, form_data):
    try:
        with db_cursor() as (conn, cursor):
            conn.start_transaction()
            try:
                cursor.execute(
                    """
                    SELECT r.pickup_location_id, r.destination_location_id, r.total_seats,
                           r.available_seats, r.ride_status, v.seating_capacity
                    FROM Rides r
                    JOIN Vehicles v ON r.vehicle_id = v.vehicle_id
                    WHERE r.ride_id = %s AND r.driver_id = %s
                    FOR UPDATE
                    """,
                    (ride_id, user_id),
                )
                ride = cursor.fetchone()
                if ride is None or ride[4] not in ("ACTIVE", "FULL"):
                    conn.rollback()
                    return False, "This ride can no longer be updated."

                pickup_id, dest_id, old_total, old_avail, _status, vehicle_cap = ride

                cursor.execute(
                    "SELECT COUNT(*) FROM Bookings WHERE ride_id = %s AND booking_status = 'CONFIRMED'",
                    (ride_id,),
                )
                confirmed_bookings = cursor.fetchone()[0]

                if update_type in ("pickup", "destination", "datetime") and confirmed_bookings > 0:
                    conn.rollback()
                    return False, "This ride has confirmed bookings. Route, date and time cannot be changed."

                if update_type in ("pickup", "destination"):
                    choice = form_data.get("location_id", "")
                    if choice == "__new__":
                        ok, err, loc_tuple = _validate_new_location_tuple(
                            form_data.get("city"),
                            form_data.get("region"),
                            form_data.get("area"),
                            form_data.get("point_name"),
                        )
                        if not ok:
                            conn.rollback()
                            return False, err
                        new_loc_id = _get_or_create_location(cursor, loc_tuple)
                    elif choice.isdigit():
                        new_loc_id = int(choice)
                    else:
                        conn.rollback()
                        return False, "Please select a valid location."

                    if update_type == "pickup":
                        if new_loc_id == dest_id:
                            conn.rollback()
                            return False, "Pickup and destination cannot be the same."
                        cursor.execute(
                            "UPDATE Rides SET pickup_location_id = %s WHERE ride_id = %s AND driver_id = %s",
                            (new_loc_id, ride_id, user_id),
                        )
                    else:
                        if new_loc_id == pickup_id:
                            conn.rollback()
                            return False, "Pickup and destination cannot be the same."
                        cursor.execute(
                            "UPDATE Rides SET destination_location_id = %s WHERE ride_id = %s AND driver_id = %s",
                            (new_loc_id, ride_id, user_id),
                        )
                    conn.commit()
                    return True, "Location updated successfully."

                if update_type == "datetime":
                    try:
                        new_date = datetime.strptime((form_data.get("ride_date") or "").strip(), "%Y-%m-%d").date()
                        new_time = datetime.strptime((form_data.get("ride_time") or "").strip(), "%H:%M").time()
                    except ValueError:
                        conn.rollback()
                        return False, "Invalid date or time format."
                    if new_date < date.today() or datetime.combine(new_date, new_time) <= datetime.now():
                        conn.rollback()
                        return False, "Please enter a future date and time."

                    cursor.execute(
                        "UPDATE Rides SET ride_date = %s, ride_time = %s WHERE ride_id = %s AND driver_id = %s",
                        (new_date, new_time, ride_id, user_id),
                    )
                    conn.commit()
                    return True, "Ride Date and Time updated successfully."

                if update_type == "seats":
                    seats_str = (form_data.get("total_seats") or "").strip()
                    if not seats_str.isdigit():
                        conn.rollback()
                        return False, "Seat capacity must be a positive integer."
                    new_total = int(seats_str)
                    if not (1 <= new_total <= vehicle_cap):
                        conn.rollback()
                        return False, f"Total seats must be between 1 and {vehicle_cap}."

                    booked_seats = old_total - old_avail
                    if new_total < booked_seats:
                        conn.rollback()
                        return False, f"New seat capacity cannot be less than already booked seats ({booked_seats})."

                    new_avail = new_total - booked_seats
                    new_status = "FULL" if new_avail == 0 else "ACTIVE"
                    cursor.execute(
                        """
                        UPDATE Rides
                        SET total_seats = %s, available_seats = %s, ride_status = %s
                        WHERE ride_id = %s AND driver_id = %s
                        """,
                        (new_total, new_avail, new_status, ride_id, user_id),
                    )
                    conn.commit()
                    return True, f"Passenger seats updated (Total: {new_total}, Available: {new_avail})."

                if update_type == "price":
                    try:
                        new_price = Decimal((form_data.get("price_per_seat") or "").strip())
                        if not new_price.is_finite() or not (Decimal("0") < new_price <= Decimal("99999999.99")):
                            conn.rollback()
                            return False, "Price must be greater than zero and at most Rs. 99999999.99."
                        new_price = new_price.quantize(Decimal("0.01"))
                    except InvalidOperation:
                        conn.rollback()
                        return False, "Invalid price."

                    cursor.execute(
                        "UPDATE Rides SET price_per_seat = %s WHERE ride_id = %s AND driver_id = %s",
                        (new_price, ride_id, user_id),
                    )
                    conn.commit()
                    return True, f"Price per seat updated to Rs. {new_price}."

                conn.rollback()
                return False, "Invalid update option."
            except Exception as exc:
                conn.rollback()
                if is_mysql_error(exc) and exc.errno == 1062:
                    return False, "Email or Phone number already exists."
                raise
    except ConnectionError as exc:
        return False, str(exc)
    except Exception:
        return False, "Unable to update ride due to a database error."


def get_received_feedback(user_id):
    with db_cursor(dictionary=True) as (_conn, cursor):
        cursor.execute(
            """
            SELECT
                rf.feedback_id,
                rf.booking_id,
                rf.ride_id,
                u.full_name AS passenger_name,
                rf.rating,
                rf.comment,
                rf.created_at
            FROM Ratings_Feedback rf
            JOIN Users u ON rf.seeker_id = u.user_id
            WHERE rf.driver_id = %s
            ORDER BY rf.created_at DESC
            """,
            (user_id,),
        )
        return cursor.fetchall()


# ==============================================================================
# ADMIN SERVICES (mirrors admin.py)
# ==============================================================================

def _add_audit_record_in_tx(cursor, admin_id, action, details):
    admin_details = f"Admin ID: {admin_id} | {details}"
    cursor.execute(
        "INSERT INTO Audit_Records (user_id, action, details) VALUES (NULL, %s, %s)",
        (action, admin_details),
    )


def admin_record_logout_audit(admin_id):
    try:
        with db_cursor() as (conn, cursor):
            conn.start_transaction()
            _add_audit_record_in_tx(cursor, admin_id, "ADMIN_LOGOUT", "Admin logged out.")
            conn.commit()
    except Exception:
        pass


def admin_login_service(portal_password, admin_id_str, password):
    if (portal_password or "").strip() != PORTAL_ACCESS_PASSWORD:
        return False, "Incorrect Admin Portal Password. Access Denied.", None

    admin_id_str = (admin_id_str or "").strip()
    if not admin_id_str.isdigit():
        return False, "Admin ID must be a number.", None
    admin_id = int(admin_id_str)
    password = (password or "").strip()
    if not password:
        return False, "Password is required.", None

    try:
        with db_cursor() as (conn, cursor):
            conn.start_transaction()
            try:
                cursor.execute(
                    """
                    SELECT password, admin_status, failed_login_attempts, locked_until, full_name
                    FROM Admin
                    WHERE admin_id = %s
                    FOR UPDATE
                    """,
                    (admin_id,),
                )
                admin = cursor.fetchone()
                if admin is None:
                    conn.rollback()
                    return False, "Admin account not found.", None

                stored_password, admin_status, failed_attempts, locked_until, full_name = admin

                if admin_status != "ACTIVE":
                    conn.rollback()
                    return False, "Your Admin account is not ACTIVE.", None

                if locked_until is not None:
                    if locked_until > datetime.now():
                        conn.rollback()
                        return False, f"Your account is temporarily locked. Try again after: {locked_until}", None

                    cursor.execute(
                        """
                        UPDATE Admin
                        SET failed_login_attempts = 0, locked_until = NULL
                        WHERE admin_id = %s
                        """,
                        (admin_id,),
                    )
                    failed_attempts = 0

                if password == stored_password:
                    cursor.execute(
                        """
                        UPDATE Admin
                        SET failed_login_attempts = 0, locked_until = NULL
                        WHERE admin_id = %s
                        """,
                        (admin_id,),
                    )
                    conn.commit()
                    return True, "Admin login successful!", {
                        "admin_id": admin_id,
                        "full_name": full_name,
                    }

                failed_attempts = (failed_attempts or 0) + 1
                if failed_attempts >= 5:
                    cursor.execute(
                        """
                        UPDATE Admin
                        SET failed_login_attempts = 0,
                            locked_until = DATE_ADD(NOW(), INTERVAL 5 MINUTE)
                        WHERE admin_id = %s
                        """,
                        (admin_id,),
                    )
                    conn.commit()
                    return False, "Too many incorrect attempts. Your account is locked for 5 minutes.", None

                cursor.execute(
                    "UPDATE Admin SET failed_login_attempts = %s WHERE admin_id = %s",
                    (failed_attempts, admin_id),
                )
                conn.commit()
                return False, f"Incorrect Password. Remaining attempts: {5 - failed_attempts}.", None
            except Exception as exc:
                conn.rollback()
                if is_mysql_error(exc) and exc.errno == 1062:
                    return False, "Email or Phone number already exists."
                raise
    except ConnectionError as exc:
        return False, str(exc), None
    except Exception:
        return False, "Admin login failed due to a database error.", None


def admin_register_service(acting_admin_id, full_name, email, phone, password, confirm_password):
    full_name = (full_name or "").strip()
    email = (email or "").strip()
    phone = (phone or "").strip()
    password = (password or "").strip()
    confirm_password = (confirm_password or "").strip()

    if not full_name:
        return False, "Full name cannot be empty."
    if not email or "@" not in email or "." not in email:
        return False, "Invalid email address."
    if not phone or len(phone) > 15:
        return False, "Phone number is required (maximum 15 characters)."
    if len(password) < 6:
        return False, "Password must contain at least 6 characters."
    if password != confirm_password:
        return False, "Passwords do not match."

    try:
        with db_cursor() as (conn, cursor):
            conn.start_transaction()
            try:
                cursor.execute("SELECT admin_id FROM Admin WHERE email = %s", (email,))
                if cursor.fetchone():
                    conn.rollback()
                    return False, "Email already exists."

                cursor.execute("SELECT admin_id FROM Admin WHERE phone = %s", (phone,))
                if cursor.fetchone():
                    conn.rollback()
                    return False, "Phone number is already registered."

                cursor.execute(
                    "INSERT INTO Admin (full_name, email, phone, password) VALUES (%s, %s, %s, %s)",
                    (full_name, email, phone, password),
                )
                new_admin_id = cursor.lastrowid
                if acting_admin_id is not None:
                    _add_audit_record_in_tx(
                        cursor,
                        acting_admin_id,
                        "NEW_ADMIN_REGISTERED",
                        f"New Admin ID: {new_admin_id}",
                    )
                conn.commit()
                return True, f"Admin registration successful! Your Admin ID is {new_admin_id}. Please remember your Admin ID for login."
            except Exception as exc:
                conn.rollback()
                if is_mysql_error(exc) and exc.errno == 1062:
                    return False, "Email or Phone number already exists."
                raise
    except ConnectionError as exc:
        return False, str(exc)
    except Exception:
        return False, "Admin registration failed due to a database error."


def admin_portal_register_service(portal_password, full_name, email, phone, password, confirm_password):
    """Validate Admin Portal Access Password on the server, then reuse admin_register_service."""
    if (portal_password or "").strip() != PORTAL_ACCESS_PASSWORD:
        return False, "Incorrect Admin Portal Password. Access Denied."
    return admin_register_service(None, full_name, email, phone, password, confirm_password)


def admin_get_dashboard_stats():
    with db_cursor(dictionary=True) as (_conn, cursor):
        cursor.execute(
            """
            SELECT
                (SELECT COUNT(*) FROM Users) AS total_users,
                (SELECT COUNT(*) FROM Vehicles) AS total_vehicles,
                (SELECT COUNT(*) FROM Rides WHERE ride_status = 'ACTIVE') AS active_rides,
                (SELECT COUNT(*) FROM Reports WHERE report_status IN ('PENDING', 'UNDER_REVIEW')) AS open_reports
            """
        )
        return cursor.fetchone()


def admin_list_users():
    with db_cursor(dictionary=True) as (_conn, cursor):
        cursor.execute(
            """
            SELECT user_id, full_name, college_id, email, phone, account_status
            FROM Users
            ORDER BY user_id
            """
        )
        return cursor.fetchall()


def admin_update_user_status(admin_id, user_id, new_status):
    if new_status not in ("ACTIVE", "BLOCKED", "INACTIVE"):
        return False, "Invalid account status."

    try:
        with db_cursor() as (conn, cursor):
            conn.start_transaction()
            try:
                cursor.execute("SELECT user_id FROM Users WHERE user_id = %s", (user_id,))
                if cursor.fetchone() is None:
                    conn.rollback()
                    return False, "User not found."

                cursor.execute(
                    "UPDATE Users SET account_status = %s WHERE user_id = %s",
                    (new_status, user_id),
                )
                if cursor.rowcount == 0:
                    conn.commit()
                    return True, "User account status is already set to this status."

                _add_audit_record_in_tx(
                    cursor,
                    admin_id,
                    "USER_STATUS_UPDATED",
                    f"User ID: {user_id}, New Status: {new_status}",
                )
                conn.commit()
                return True, f"User #{user_id} status updated to {new_status}."
            except Exception as exc:
                conn.rollback()
                if is_mysql_error(exc) and exc.errno == 1062:
                    return False, "Email or Phone number already exists."
                raise
    except ConnectionError as exc:
        return False, str(exc)
    except Exception:
        return False, "Unable to update user status."


def admin_list_vehicles():
    with db_cursor(dictionary=True) as (_conn, cursor):
        cursor.execute(
            """
            SELECT v.vehicle_id, v.owner_id, u.full_name AS owner_name,
                   v.vehicle_name, v.registration_number, v.seating_capacity, v.vehicle_status
            FROM Vehicles v
            LEFT JOIN Users u ON v.owner_id = u.user_id
            ORDER BY v.vehicle_id
            """
        )
        return cursor.fetchall()


def admin_update_vehicle_status(admin_id, vehicle_id, new_status):
    if new_status not in ("ACTIVE", "INACTIVE"):
        return False, "Invalid vehicle status."

    try:
        with db_cursor() as (conn, cursor):
            conn.start_transaction()
            try:
                cursor.execute("SELECT vehicle_id FROM Vehicles WHERE vehicle_id = %s", (vehicle_id,))
                if cursor.fetchone() is None:
                    conn.rollback()
                    return False, "Vehicle not found."

                cursor.execute(
                    "UPDATE Vehicles SET vehicle_status = %s WHERE vehicle_id = %s",
                    (new_status, vehicle_id),
                )
                if cursor.rowcount == 0:
                    conn.commit()
                    return True, "Vehicle status is already set to this status."

                _add_audit_record_in_tx(
                    cursor,
                    admin_id,
                    "VEHICLE_STATUS_UPDATED",
                    f"Vehicle ID: {vehicle_id}, New Status: {new_status}",
                )
                conn.commit()
                return True, f"Vehicle #{vehicle_id} status updated to {new_status}."
            except Exception as exc:
                conn.rollback()
                if is_mysql_error(exc) and exc.errno == 1062:
                    return False, "Email or Phone number already exists."
                raise
    except ConnectionError as exc:
        return False, str(exc)
    except Exception:
        return False, "Unable to update vehicle status."


def admin_list_reports():
    with db_cursor(dictionary=True) as (_conn, cursor):
        cursor.execute(
            """
            SELECT report_id, reported_by, related_user_id, ride_id,
                   description, report_status, admin_action, created_at, resolved_at
            FROM Reports
            ORDER BY created_at DESC
            """
        )
        return cursor.fetchall()


def admin_update_report(admin_id, report_id, new_status, admin_action):
    if new_status not in ("PENDING", "UNDER_REVIEW", "RESOLVED", "REJECTED"):
        return False, "Invalid report status."
    admin_action = (admin_action or "").strip()

    try:
        with db_cursor() as (conn, cursor):
            conn.start_transaction()
            try:
                cursor.execute("SELECT report_id FROM Reports WHERE report_id = %s", (report_id,))
                if cursor.fetchone() is None:
                    conn.rollback()
                    return False, "Report not found."

                if new_status in ("RESOLVED", "REJECTED"):
                    cursor.execute(
                        """
                        UPDATE Reports
                        SET report_status = %s, admin_action = %s, resolved_at = NOW()
                        WHERE report_id = %s
                        """,
                        (new_status, admin_action, report_id),
                    )
                else:
                    cursor.execute(
                        """
                        UPDATE Reports
                        SET report_status = %s, admin_action = %s, resolved_at = NULL
                        WHERE report_id = %s
                        """,
                        (new_status, admin_action, report_id),
                    )

                _add_audit_record_in_tx(
                    cursor,
                    admin_id,
                    "REPORT_UPDATED",
                    f"Report ID: {report_id}, New Status: {new_status}",
                )
                conn.commit()
                return True, f"Report #{report_id} updated to {new_status}."
            except Exception as exc:
                conn.rollback()
                if is_mysql_error(exc) and exc.errno == 1062:
                    return False, "Email or Phone number already exists."
                raise
    except ConnectionError as exc:
        return False, str(exc)
    except Exception:
        return False, "Unable to update report."


def admin_list_feedback():
    with db_cursor(dictionary=True) as (_conn, cursor):
        cursor.execute(
            """
            SELECT rf.feedback_id, rf.booking_id, rf.ride_id, rf.driver_id,
                   u.full_name AS driver_name, rf.seeker_id, rf.rating, rf.comment, rf.created_at
            FROM Ratings_Feedback rf
            LEFT JOIN Users u ON rf.driver_id = u.user_id
            ORDER BY rf.created_at DESC
            """
        )
        return cursor.fetchall()


def admin_list_ongoing_rides():
    with db_cursor(dictionary=True) as (_conn, cursor):
        cursor.execute(
            """
            SELECT
                r.ride_id, r.driver_id, u.full_name AS driver_name, r.vehicle_id,
                lp.city AS pickup_city, lp.region AS pickup_region, lp.area AS pickup_area, lp.point_name AS pickup_point,
                ld.city AS destination_city, ld.region AS destination_region, ld.area AS destination_area, ld.point_name AS destination_point,
                r.ride_date, r.ride_time, r.total_seats, r.available_seats, r.price_per_seat, r.ride_status
            FROM Rides r
            LEFT JOIN Users u ON r.driver_id = u.user_id
            LEFT JOIN Locations lp ON r.pickup_location_id = lp.location_id
            LEFT JOIN Locations ld ON r.destination_location_id = ld.location_id
            WHERE r.ride_status = 'ACTIVE'
            ORDER BY r.ride_date, r.ride_time
            """
        )
        rows = cursor.fetchall()
        for r in rows:
            r["ride_time_fmt"] = format_time_hhmm(r["ride_time"])
        return rows


def admin_list_audit_logs():
    with db_cursor(dictionary=True) as (_conn, cursor):
        cursor.execute(
            """
            SELECT audit_id, user_id, action, details, created_at
            FROM Audit_Records
            ORDER BY created_at DESC, audit_id DESC
            """
        )
        return cursor.fetchall()
