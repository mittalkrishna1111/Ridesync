import mysql.connector as c
from datetime import datetime, date, time, timedelta
from decimal import Decimal
from database import get_connection, ensure_database_ready

def show_guidelines(title, guidelines):
    print("\n" + "=" * 60)
    print("📌 INPUT GUIDELINES".center(60))
    print("-" * 60)
    print(title.center(60))
    print("-" * 60)

    for guideline in guidelines:
        print("  •", guideline)

    print("=" * 60)

def get_positive_integer(label, minimum=1, maximum=255):
    while True:
        show_guidelines(
            "NUMBER INPUT GUIDELINES",
            [
                "Enter numbers using digits only.",
                "Do not enter letters or special characters.",
                "Enter a value between " + str(minimum) + " and " + str(maximum) + "."
            ]
        )

        value = input("\n➜ " + label).strip()

        if value.isdigit():
            value = int(value)

            if minimum <= value <= maximum:
                return value

        print(
            "\n⚠ Please enter a number between",
            minimum,
            "and",
            maximum,
            ".\n"
        )


def get_confirmation(label):
    while True:
        show_guidelines(
            "CONFIRMATION GUIDELINES",
            [
                "Enter Y or YES to confirm.",
                "Enter N or NO to cancel.",
                "Do not enter any other value."
            ]
        )

        answer = input("\n➜ " + label + " (Y/N): ").strip().lower()

        if answer in ("y", "yes"):
            return True
        elif answer in ("n", "no"):
            return False

        print("\n⚠ Invalid input. Please enter Y or N.\n")


def get_non_empty_input(label, maximum_length):
    while True:
        show_guidelines(
            "TEXT INPUT GUIDELINES",
            [
                "This field cannot be left empty.",
                "Maximum " + str(maximum_length) + " characters are allowed.",
                "Remove unnecessary spaces before and after the input."
            ]
        )

        value = input("\n➜ " + label).strip()

        if not value:
            print("\n⚠ Input cannot be empty.\n")
            continue

        if len(value) > maximum_length:
            print("\n⚠ Maximum", maximum_length, "characters allowed.\n")
            continue

        return value


def calculate_total_fare(price_per_seat, seats):
    return (
        Decimal(str(price_per_seat)) * Decimal(str(seats))
    ).quantize(Decimal("0.01"))


def display_fare(price_per_seat, seats):
    total_fare = calculate_total_fare(
        price_per_seat,
        seats
    )

    print("\n  Price Per Seat       : Rs.", price_per_seat)
    print("  Number of Seats      :", seats)
    print("  Estimated Total Fare : Rs.", total_fare)

    return total_fare


def convert_mysql_time(value):
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


def get_time_difference_seconds(time1, time2):
    time1 = convert_mysql_time(time1)
    time2 = convert_mysql_time(time2)

    seconds1 = (
        time1.hour * 3600 +
        time1.minute * 60 +
        time1.second
    )

    seconds2 = (
        time2.hour * 3600 +
        time2.minute * 60 +
        time2.second
    )

    return abs(seconds1 - seconds2)


def get_search_date():
    while True:
        show_guidelines(
            "RIDE DATE GUIDELINES",
            [
                "Enter the date in YYYY-MM-DD format.",
                "Use a four-digit year, two-digit month and two-digit day.",
                "Past dates are not allowed.",
                "Example: 2026-12-05"
            ]
        )

        value = input(
            "\n➜ Enter Ride Date (YYYY-MM-DD): "
        ).strip()

        try:
            selected_date = datetime.strptime(
                value, "%Y-%m-%d"
            ).date()

            if selected_date.strftime("%Y-%m-%d") != value:
                print("\n⚠ Use the exact YYYY-MM-DD format.\n")
                continue

            if selected_date < date.today():
                print("\n⚠ Past dates are not allowed.\n")
                continue

            return selected_date

        except ValueError:
            print("\n✗ Invalid date. Use YYYY-MM-DD.\n")


def get_search_time(selected_date):
    while True:
        show_guidelines(
            "RIDE TIME GUIDELINES",
            [
                "Enter time in 24-hour HH:MM format.",
                "Use two digits for hours and two digits for minutes.",
                "The selected date and time must be in the future.",
                "Example: 14:30"
            ]
        )

        value = input(
            "\n➜ Enter Preferred Ride Time (HH:MM): "
        ).strip()

        try:
            selected_time = datetime.strptime(
                value, "%H:%M"
            ).time()

            if selected_time.strftime("%H:%M") != value:
                print("\n⚠ Use the exact HH:MM format.\n")
                continue

            selected_datetime = datetime.combine(
                selected_date,
                selected_time
            )

            if selected_datetime <= datetime.now():
                print("\n⚠ Please enter a future date and time.\n")
                continue

            return selected_time

        except ValueError:
            print("\n✗ Invalid time. Use 24-hour HH:MM format.\n")


def select_location(cursor, location_type):
    cursor.execute("""
        SELECT
            location_id,
            city,
            region,
            area,
            point_name
        FROM Locations
        WHERE is_active = TRUE
        ORDER BY city, area, point_name
    """)

    locations = cursor.fetchall()

    if not locations:
        print("\n⚠ No active locations are available.")
        return None

    print("\n" + "=" * 60)
    print(("📍 " + location_type + " LOCATION").center(60))
    print("=" * 60)

    for i, location in enumerate(locations, start=1):
        print("\n  " + str(i) + ". " + str(location["city"]))

        if location["region"]:
            print("     Region :", location["region"])

        print("     Area   :", location["area"])
        print("     Point  :", location["point_name"])

    choice = get_positive_integer(
        "Select Location Number: ",
        1,
        len(locations)
    )

    return locations[choice - 1]


def display_location(location):
    if location is None:
        return "Unknown"

    return (
        str(location["city"]) + ", " +
        str(location["area"]) + ", " +
        str(location["point_name"])
    )


def display_available_posted_rides(user_id):
    connection = get_connection()

    if connection is None:
        print("\n✗ Unable to connect to database.")
        return None

    cursor = None

    try:
        cursor = connection.cursor(dictionary=True)

        cursor.execute("""
            SELECT
                r.ride_id,
                r.driver_id,
                r.ride_date,
                r.ride_time,
                r.total_seats,
                r.available_seats,
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
            JOIN Users u
                ON r.driver_id = u.user_id
            JOIN Vehicles v
                ON r.vehicle_id = v.vehicle_id
            JOIN Locations lp
                ON r.pickup_location_id = lp.location_id
            JOIN Locations ld
                ON r.destination_location_id = ld.location_id
            LEFT JOIN (
                SELECT
                    driver_id,
                    AVG(rating) AS average_rating,
                    COUNT(*) AS total_ratings
                FROM Ratings_Feedback
                GROUP BY driver_id
            ) rating
                ON rating.driver_id = r.driver_id
            WHERE r.ride_status = 'ACTIVE'
            AND r.available_seats > 0
            AND r.driver_id <> %s
            AND (
                r.ride_date > CURDATE()
                OR (
                    r.ride_date = CURDATE()
                    AND r.ride_time > CURTIME()
                )
            )
            ORDER BY r.ride_date, r.ride_time
        """, (user_id,))

        rides = cursor.fetchall()

        if not rides:
            print("\n⚠ No upcoming posted rides are currently available.")
            return []

        print("\n" + "=" * 70)
        print("🚘 CURRENTLY AVAILABLE POSTED RIDES".center(70))
        print("=" * 70)

        for i, ride in enumerate(rides, start=1):
            print("\n" + "=" * 70)

            print("  RIDE NUMBER :", i)
            print("  Ride ID     :", ride["ride_id"])
            print("  Driver      :", ride["driver_name"])

            print(
                "  Pickup      :",
                ride["pickup_city"],
                ride["pickup_area"],
                ride["pickup_point"]
            )

            print(
                "  Destination :",
                ride["destination_city"],
                ride["destination_area"],
                ride["destination_point"]
            )

            print("  Ride Date   :", ride["ride_date"])
            print(
                "  Ride Time   :",
                convert_mysql_time(ride["ride_time"])
            )

            print("  Available Seats :", ride["available_seats"])
            print("  Price Per Seat  : Rs.", ride["price_per_seat"])
            print("  Vehicle         :", ride["vehicle_name"])
            print("  Registration    :", ride["registration_number"])

            if ride["total_ratings"] > 0:
                print(
                    "  Driver Rating   :",
                    round(float(ride["average_rating"]), 2),
                    "/ 5"
                )
            else:
                print("  Driver Rating   : No ratings yet")

        print("\n" + "=" * 70)

        return rides

    except c.Error as e:
        print("\n✗ Unable to display available rides:", e)
        return None

    finally:
        if cursor is not None:
            cursor.close()

        connection.close()


def search_rides(user_id):
    print("\n" + "=" * 60)
    print("🔍 SEARCH AVAILABLE RIDES".center(60))
    print("=" * 60)

    rides = display_available_posted_rides(user_id)

    if rides is None:
        return

    if rides:
        print("\n  1. Select a Ride from the Available Rides")
        print("  2. Search Rides Using Pickup and Destination")
        print("  0. Back")

        show_guidelines(
            "SEARCH OPTION GUIDELINES",
            [
                "Enter 1 to select a ride from the available list.",
                "Enter 2 to search using pickup and destination.",
                "Enter 0 to go back."
            ]
        )

        choice = input("\n➜ Enter your choice (0-2): ").strip()

        if choice == "1":
            ride_choice = get_positive_integer(
                "Select Ride Number (0 to go back): ",
                0,
                len(rides)
            )

            if ride_choice == 0:
                return

            selected_ride = rides[ride_choice - 1]

            required_seats = get_positive_integer(
                "Enter Number of Passenger Seats Required: ",
                1,
                selected_ride["available_seats"]
            )

            print("\n" + "=" * 50)
            print("💰 FARE DETAILS".center(50))
            print("=" * 50)

            display_fare(
                selected_ride["price_per_seat"],
                required_seats
            )

            request_ride(
                user_id,
                selected_ride["ride_id"],
                required_seats
            )

            return

        elif choice == "0":
            return

        elif choice != "2":
            print("\n✗ Invalid choice.")
            return

    else:
        print("\nYou can still search for rides using locations.")

        if not get_confirmation(
            "Do you want to search using pickup and destination?"
        ):
            return

    connection = get_connection()

    if connection is None:
        print("\n✗ Unable to connect to database.")
        return

    cursor = None

    try:
        cursor = connection.cursor(dictionary=True)

        pickup = select_location(cursor, "PICKUP")

        if pickup is None:
            return

        destination = select_location(cursor, "DESTINATION")

        if destination is None:
            return

        if pickup["location_id"] == destination["location_id"]:
            print("\n⚠ Pickup and destination cannot be the same.")
            return

        selected_date = get_search_date()
        selected_time = get_search_time(selected_date)

        required_seats = get_positive_integer(
            "Enter Number of Passenger Seats Required: ",
            1,
            255
        )

        cursor.execute("""
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
                COALESCE(rating.average_rating, 0) AS average_rating,
                COALESCE(rating.total_ratings, 0) AS total_ratings
            FROM Rides r
            JOIN Users u
                ON r.driver_id = u.user_id
            JOIN Vehicles v
                ON r.vehicle_id = v.vehicle_id
            JOIN Locations lp
                ON r.pickup_location_id = lp.location_id
            JOIN Locations ld
                ON r.destination_location_id = ld.location_id
            LEFT JOIN (
                SELECT
                    driver_id,
                    AVG(rating) AS average_rating,
                    COUNT(*) AS total_ratings
                FROM Ratings_Feedback
                GROUP BY driver_id
            ) rating
                ON rating.driver_id = r.driver_id
            WHERE r.pickup_location_id = %s
            AND r.destination_location_id = %s
            AND r.ride_date = %s
            AND r.available_seats >= %s
            AND r.ride_status = 'ACTIVE'
            AND r.driver_id <> %s
            AND (
                r.ride_date > CURDATE()
                OR (
                    r.ride_date = CURDATE()
                    AND r.ride_time > CURTIME()
                )
            )
            ORDER BY r.ride_time
        """, (
            pickup["location_id"],
            destination["location_id"],
            selected_date,
            required_seats,
            user_id
        ))

        rides = cursor.fetchall()
        matching_rides = []

        for ride in rides:
            difference = get_time_difference_seconds(
                ride["ride_time"],
                selected_time
            )

            if difference <= 1800:
                time_score = (
                    (1800 - difference) / 1800
                ) * 60

                rating_score = (
                    float(ride["average_rating"]) / 5
                ) * 40

                final_score = time_score + rating_score

                ride["time_difference"] = difference
                ride["time_score"] = time_score
                ride["rating_score"] = rating_score
                ride["final_score"] = final_score

                matching_rides.append(ride)

        matching_rides.sort(
            key=lambda item: item["final_score"],
            reverse=True
        )

        if not matching_rides:
            print("\n⚠ No matching rides found.")
            print("➜ Try another time or date.")
            return

        print("\n" + "=" * 60)
        print("⭐ MATCHING RIDES".center(60))
        print("=" * 60)

        print("\n  Pickup         :", display_location(pickup))
        print("  Destination    :", display_location(destination))
        print("  Date           :", selected_date)
        print("  Preferred Time :", selected_time)
        print("  Required Seats :", required_seats)

        for i, ride in enumerate(matching_rides, start=1):
            print("\n" + "=" * 60)

            print("  MATCH NUMBER :", i)
            print("  Ride ID      :", ride["ride_id"])
            print("  Driver       :", ride["driver_name"])

            print(
                "  Pickup       :",
                ride["pickup_city"],
                ride["pickup_area"],
                ride["pickup_point"]
            )

            print(
                "  Destination  :",
                ride["destination_city"],
                ride["destination_area"],
                ride["destination_point"]
            )

            print("  Ride Date    :", ride["ride_date"])
            print(
                "  Ride Time    :",
                convert_mysql_time(ride["ride_time"])
            )

            print("  Available Seats :", ride["available_seats"])
            print("  Vehicle         :", ride["vehicle_name"])
            print("  Registration    :", ride["registration_number"])

            print(
                "  Price Per Seat  : Rs.",
                ride["price_per_seat"]
            )

            print(
                "  Estimated Total Fare : Rs.",
                calculate_total_fare(
                    ride["price_per_seat"],
                    required_seats
                )
            )

            if ride["total_ratings"] > 0:
                print(
                    "  Driver Rating   :",
                    round(float(ride["average_rating"]), 2),
                    "/ 5"
                )
            else:
                print("  Driver Rating   : No ratings yet")

            print(
                "  Time Difference :",
                round(ride["time_difference"] / 60, 1),
                "minutes"
            )

            print(
                "  Matching Score  :",
                round(ride["final_score"], 2),
                "/ 100"
            )

        print("\n" + "=" * 60)
        print("  0. Back")

        choice = get_positive_integer(
            "Select Match Number to Request (0 to go back): ",
            0,
            len(matching_rides)
        )

        if choice == 0:
            return

        selected_ride = matching_rides[choice - 1]

        request_ride(
            user_id,
            selected_ride["ride_id"],
            required_seats
        )

    except c.Error as e:
        connection.rollback()
        print("\n✗ Ride Search Error:", e)

    finally:
        if cursor is not None:
            cursor.close()

        connection.close()


def request_ride(user_id, ride_id, seats_requested):
    connection = get_connection()

    if connection is None:
        print("\n✗ Unable to connect to database.")
        return

    cursor = None

    try:
        cursor = connection.cursor(dictionary=True)

        cursor.execute("""
            SELECT price_per_seat
            FROM Rides
            WHERE ride_id = %s
        """, (ride_id,))

        price_result = cursor.fetchone()

        if price_result is None:
            print("\n✗ Selected ride does not exist.")
            return

        displayed_price = price_result["price_per_seat"]

        connection.commit()

        print("\n" + "=" * 60)
        print("💰 RIDE FARE DETAILS".center(60))
        print("=" * 60)

        display_fare(
            displayed_price,
            seats_requested
        )

        if not get_confirmation(
            "Do you want to send this ride request?"
        ):
            print("\n⚠ Ride request cancelled.")
            return

        connection.start_transaction()

        cursor.execute("""
            SELECT
                driver_id,
                available_seats,
                ride_status,
                ride_date,
                ride_time,
                price_per_seat
            FROM Rides
            WHERE ride_id = %s
            FOR UPDATE
        """, (ride_id,))

        ride = cursor.fetchone()

        if ride is None:
            connection.rollback()
            print("\n✗ Selected ride does not exist.")
            return

        driver_id = ride["driver_id"]
        available_seats = ride["available_seats"]
        ride_status = ride["ride_status"]
        ride_date = ride["ride_date"]
        ride_time = convert_mysql_time(ride["ride_time"])
        current_price = ride["price_per_seat"]

        if Decimal(str(current_price)) != Decimal(str(displayed_price)):
            connection.rollback()

            print("\n⚠ The ride price has changed.")
            print("  Previous Price Per Seat: Rs.", displayed_price)
            print("  Current Price Per Seat :", current_price)

            print("\n➜ Please search for the ride again.")
            return

        if driver_id == user_id:
            connection.rollback()
            print("\n✗ You cannot request your own ride.")
            return

        if ride_status != "ACTIVE":
            connection.rollback()
            print("\n⚠ This ride is not accepting requests.")
            return

        if available_seats < seats_requested:
            connection.rollback()
            print("\n⚠ Not enough seats are available.")
            return

        ride_datetime = datetime.combine(
            ride_date,
            ride_time
        )

        if ride_datetime <= datetime.now():
            connection.rollback()
            print("\n⚠ This ride is no longer available.")
            return

        cursor.execute("""
            SELECT request_id
            FROM Ride_Requests
            WHERE ride_id = %s
            AND seeker_id = %s
            AND request_status IN ('PENDING', 'ACCEPTED')
            FOR UPDATE
        """, (ride_id, user_id))

        existing_request = cursor.fetchone()

        if existing_request is not None:
            connection.rollback()
            print("\n⚠ You already have an active request for this ride.")
            return

        cursor.execute("""
            INSERT INTO Ride_Requests
            (
                ride_id,
                seeker_id,
                seats_requested,
                request_status
            )
            VALUES (%s, %s, %s, 'PENDING')
        """, (
            ride_id,
            user_id,
            seats_requested
        ))

        request_id = cursor.lastrowid

        connection.commit()

        print("\n" + "=" * 60)
        print("✓ RIDE REQUEST SENT SUCCESSFULLY!".center(60))
        print("=" * 60)

        print("\n  Request ID     :", request_id)
        print("  Ride ID        :", ride_id)
        print("  Seats Requested:", seats_requested)

        display_fare(
            current_price,
            seats_requested
        )

        print("\n  Request Status : PENDING")
        print("\n✓ Please wait for the driver to respond.")

    except c.Error as e:
        connection.rollback()
        print("\n✗ Ride Request Error:", e)

    finally:
        if cursor is not None:
            cursor.close()

        connection.close()


def view_my_ride_requests(user_id):
    print("\n" + "=" * 60)
    print("📋 MY RIDE REQUESTS".center(60))
    print("=" * 60)

    connection = get_connection()

    if connection is None:
        print("\n✗ Unable to connect to database.")
        return

    cursor = None

    try:
        cursor = connection.cursor()

        cursor.execute("""
            SELECT
                rr.request_id,
                rr.ride_id,
                u.full_name,
                rr.seats_requested,
                rr.request_status,
                rr.requested_at,
                rr.responded_at,
                r.ride_date,
                r.ride_time,
                r.price_per_seat
            FROM Ride_Requests rr
            JOIN Rides r
                ON rr.ride_id = r.ride_id
            JOIN Users u
                ON r.driver_id = u.user_id
            WHERE rr.seeker_id = %s
            ORDER BY rr.requested_at DESC
        """, (user_id,))

        requests = cursor.fetchall()

        if not requests:
            print("\n⚠ You have not sent any ride requests.")
            return

        for request in requests:
            print("\n" + "=" * 60)

            print("  Request ID     :", request[0])
            print("  Ride ID        :", request[1])
            print("  Driver         :", request[2])
            print("  Seats Requested:", request[3])
            print("  Request Status :", request[4])
            print("  Requested At   :", request[5])
            print("  Responded At   :", request[6])
            print("  Ride Date      :", request[7])
            print("  Ride Time      :", convert_mysql_time(request[8]))

            display_fare(
                request[9],
                request[3]
            )

        print("\n" + "=" * 60)

    except c.Error as e:
        print("\n✗ Unable to display ride requests:", e)

    finally:
        if cursor is not None:
            cursor.close()

        connection.close()


def get_user_bookings(cursor, user_id):
    cursor.execute("""
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
        JOIN Rides r
            ON b.ride_id = r.ride_id
        JOIN Users u
            ON r.driver_id = u.user_id
        JOIN Vehicles v
            ON r.vehicle_id = v.vehicle_id
        JOIN Locations lp
            ON r.pickup_location_id = lp.location_id
        JOIN Locations ld
            ON r.destination_location_id = ld.location_id
        WHERE b.seeker_id = %s
        ORDER BY b.booked_at DESC
    """, (user_id,))

    return cursor.fetchall()


def view_booked_rides(user_id):
    print("\n" + "=" * 60)
    print("📖 MY BOOKINGS AND HISTORY".center(60))
    print("=" * 60)

    connection = get_connection()

    if connection is None:
        print("\n✗ Unable to connect to database.")
        return

    cursor = None

    try:
        cursor = connection.cursor(dictionary=True)

        bookings = get_user_bookings(cursor, user_id)

        if not bookings:
            print("\n⚠ You have no bookings yet.")
            return

        for booking in bookings:
            print("\n" + "=" * 60)

            print("  Booking ID :", booking["booking_id"])
            print("  Ride ID    :", booking["ride_id"])
            print("  Driver     :", booking["driver_name"])

            print(
                "  Pickup     :",
                booking["pickup_city"],
                booking["pickup_area"],
                booking["pickup_point"]
            )

            print(
                "  Destination:",
                booking["destination_city"],
                booking["destination_area"],
                booking["destination_point"]
            )

            print("  Ride Date  :", booking["ride_date"])

            print(
                "  Ride Time  :",
                convert_mysql_time(booking["ride_time"])
            )

            print("  Seats Booked:", booking["seats_booked"])

            display_fare(
                booking["price_per_seat"],
                booking["seats_booked"]
            )

            print("  Booking Status:", booking["booking_status"])
            print("  Ride Status   :", booking["ride_status"])
            print("  Booked At     :", booking["booked_at"])

            if booking["cancelled_at"] is not None:
                print("  Cancelled At  :", booking["cancelled_at"])

        print("\n" + "=" * 60)

    except c.Error as e:
        print("\n✗ Unable to display bookings:", e)

    finally:
        if cursor is not None:
            cursor.close()

        connection.close()


def cancel_booking(user_id):
    print("\n" + "=" * 60)
    print("✖ CANCEL BOOKING".center(60))
    print("=" * 60)

    connection = get_connection()

    if connection is None:
        print("\n✗ Unable to connect to database.")
        return

    cursor = None

    try:
        cursor = connection.cursor(dictionary=True)

        cursor.execute("""
            SELECT
                b.booking_id,
                b.ride_id,
                b.seats_booked,
                b.booking_status,
                r.ride_date,
                r.ride_time,
                r.ride_status,
                r.price_per_seat,
                u.full_name AS driver_name
            FROM Bookings b
            JOIN Rides r
                ON b.ride_id = r.ride_id
            JOIN Users u
                ON r.driver_id = u.user_id
            WHERE b.seeker_id = %s
            AND b.booking_status = 'CONFIRMED'
            ORDER BY r.ride_date, r.ride_time
        """, (user_id,))

        bookings = cursor.fetchall()

        connection.commit()

        if not bookings:
            print("\n⚠ You have no confirmed bookings to cancel.")
            return

        print("\n  YOUR CONFIRMED BOOKINGS")

        for i, booking in enumerate(bookings, start=1):
            print("\n" + "=" * 50)
            print("  " + str(i) + ". Booking ID:", booking["booking_id"])
            print("     Ride ID   :", booking["ride_id"])
            print("     Driver    :", booking["driver_name"])
            print("     Ride Date :", booking["ride_date"])
            print(
                "     Ride Time :",
                convert_mysql_time(booking["ride_time"])
            )
            print("     Seats Booked:", booking["seats_booked"])

            display_fare(
                booking["price_per_seat"],
                booking["seats_booked"]
            )

        print("\n  0. Back")

        choice = get_positive_integer(
            "Select Booking Number (0 to go back): ",
            0,
            len(bookings)
        )

        if choice == 0:
            return

        selected_booking = bookings[choice - 1]
        booking_id = selected_booking["booking_id"]

        if not get_confirmation(
            "Are you sure you want to cancel this booking?"
        ):
            print("\n⚠ Booking cancellation cancelled.")
            return

        connection.start_transaction()

        cursor.execute("""
            SELECT
                ride_id,
                seats_booked,
                booking_status
            FROM Bookings
            WHERE booking_id = %s
            AND seeker_id = %s
            FOR UPDATE
        """, (booking_id, user_id))

        current_booking = cursor.fetchone()

        if (
            current_booking is None or
            current_booking["booking_status"] != "CONFIRMED"
        ):
            connection.rollback()
            print("\n⚠ This booking is no longer available for cancellation.")
            return

        ride_id = current_booking["ride_id"]
        seats_booked = current_booking["seats_booked"]

        cursor.execute("""
            SELECT
                total_seats,
                available_seats,
                ride_status,
                ride_date,
                ride_time
            FROM Rides
            WHERE ride_id = %s
            FOR UPDATE
        """, (ride_id,))

        ride = cursor.fetchone()

        if ride is None:
            connection.rollback()
            print("\n✗ Related ride was not found.")
            return

        ride_datetime = datetime.combine(
            ride["ride_date"],
            convert_mysql_time(ride["ride_time"])
        )

        if (
            ride["ride_status"] in ("COMPLETED", "CANCELLED") or
            ride_datetime <= datetime.now()
        ):
            connection.rollback()
            print("\n⚠ This ride can no longer be cancelled.")
            return

        cursor.execute("""
            UPDATE Bookings
            SET booking_status = 'CANCELLED',
                cancelled_at = NOW()
            WHERE booking_id = %s
            AND seeker_id = %s
            AND booking_status = 'CONFIRMED'
        """, (booking_id, user_id))

        if cursor.rowcount != 1:
            connection.rollback()
            print("\n✗ Booking cancellation failed.")
            return

        new_available_seats = min(
            ride["total_seats"],
            ride["available_seats"] + seats_booked
        )

        new_status = (
            "ACTIVE" if new_available_seats > 0 else "FULL"
        )

        cursor.execute("""
            UPDATE Rides
            SET available_seats = %s,
                ride_status = %s
            WHERE ride_id = %s
            AND ride_status IN ('ACTIVE', 'FULL')
        """, (
            new_available_seats,
            new_status,
            ride_id
        ))

        connection.commit()

        print("\n" + "=" * 60)
        print("✓ BOOKING CANCELLED SUCCESSFULLY!".center(60))
        print("=" * 60)

        print("\n  Booking ID      :", booking_id)
        print("  Seats Restored  :", seats_booked)
        print("  Available Seats :", new_available_seats)
        print("\n✓ No cancellation fee has been charged.")
        print("✓ Your booking history has been preserved.")

    except c.Error as e:
        connection.rollback()
        print("\n✗ Booking Cancellation Error:", e)

    finally:
        if cursor is not None:
            cursor.close()

        connection.close()


def view_driver_details(user_id):
    print("\n" + "=" * 60)
    print("👤 VIEW DRIVER DETAILS".center(60))
    print("=" * 60)

    connection = get_connection()

    if connection is None:
        print("\n✗ Unable to connect to database.")
        return

    cursor = None

    try:
        cursor = connection.cursor(dictionary=True)

        cursor.execute("""
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
            JOIN Rides r
                ON b.ride_id = r.ride_id
            JOIN Users u
                ON r.driver_id = u.user_id
            JOIN Vehicles v
                ON r.vehicle_id = v.vehicle_id
            WHERE b.seeker_id = %s
            ORDER BY b.booked_at DESC
        """, (user_id,))

        bookings = cursor.fetchall()

        if not bookings:
            print("\n⚠ No driver details are available.")
            return

        for i, booking in enumerate(bookings, start=1):
            print("\n" + "=" * 50)
            print("  " + str(i) + ". Booking ID:", booking["booking_id"])
            print("     Ride ID       :", booking["ride_id"])
            print("     Driver        :", booking["full_name"])
            print("     Booking Status:", booking["booking_status"])

        print("\n  0. Back")

        choice = get_positive_integer(
            "Select Booking Number (0 to go back): ",
            0,
            len(bookings)
        )

        if choice == 0:
            return

        selected = bookings[choice - 1]

        print("\n" + "=" * 60)
        print("👤 DRIVER INFORMATION".center(60))
        print("=" * 60)

        print("\n  Driver Name :", selected["full_name"])
        print("  Email       :", selected["email"])
        print("  Phone       :", selected["phone"])

        print("\n" + "=" * 60)
        print("🚘 VEHICLE INFORMATION".center(60))
        print("=" * 60)

        print("\n  Vehicle      :", selected["vehicle_name"])
        print("  Registration :", selected["registration_number"])

        print("\n" + "=" * 60)

    except c.Error as e:
        print("\n✗ Unable to display driver details:", e)

    finally:
        if cursor is not None:
            cursor.close()

        connection.close()


def give_ride_feedback(user_id):
    print("\n" + "=" * 60)
    print("⭐ GIVE RIDE FEEDBACK".center(60))
    print("=" * 60)

    connection = get_connection()

    if connection is None:
        print("\n✗ Unable to connect to database.")
        return

    cursor = None

    try:
        cursor = connection.cursor(dictionary=True)

        cursor.execute("""
            SELECT
                b.booking_id,
                b.ride_id,
                u.full_name AS driver_name,
                r.ride_date,
                r.ride_status
            FROM Bookings b
            JOIN Rides r
                ON b.ride_id = r.ride_id
            JOIN Users u
                ON r.driver_id = u.user_id
            LEFT JOIN Ratings_Feedback rf
                ON rf.booking_id = b.booking_id
            WHERE b.seeker_id = %s
            AND b.booking_status = 'COMPLETED'
            AND r.ride_status = 'COMPLETED'
            AND rf.feedback_id IS NULL
            ORDER BY r.ride_date DESC
        """, (user_id,))

        bookings = cursor.fetchall()

        if not bookings:
            print("\n⚠ No completed rides are waiting for feedback.")
            return

        print("\n  COMPLETED RIDES")

        for i, booking in enumerate(bookings, start=1):
            print("\n" + "=" * 50)
            print("  " + str(i) + ". Booking ID:", booking["booking_id"])
            print("     Ride ID   :", booking["ride_id"])
            print("     Driver    :", booking["driver_name"])
            print("     Ride Date :", booking["ride_date"])

        choice = get_positive_integer(
            "Select Booking Number: ",
            1,
            len(bookings)
        )

        selected = bookings[choice - 1]

        rating = get_positive_integer(
            "Enter Rating (1-5): ",
            1,
            5
        )

        show_guidelines(
            "FEEDBACK COMMENT GUIDELINES",
            [
                "Enter your experience with the ride or driver.",
                "You may press Enter to skip the comment.",
                "Maximum 1000 characters are allowed."
            ]
        )

        comment = input(
            "\n➜ Enter Feedback Comment (Press Enter to skip): "
        ).strip()

        if len(comment) > 1000:
            print("\n⚠ Feedback cannot exceed 1000 characters.")
            return

        if not get_confirmation("Submit this feedback?"):
            print("\n⚠ Feedback submission cancelled.")
            return

        connection.start_transaction()

        cursor.execute("""
            SELECT
                b.ride_id,
                b.booking_status,
                r.driver_id,
                r.ride_status
            FROM Bookings b
            JOIN Rides r
                ON b.ride_id = r.ride_id
            WHERE b.booking_id = %s
            AND b.seeker_id = %s
            FOR UPDATE
        """, (
            selected["booking_id"],
            user_id
        ))

        current_booking = cursor.fetchone()

        if (
            current_booking is None or
            current_booking["booking_status"] != "COMPLETED" or
            current_booking["ride_status"] != "COMPLETED"
        ):
            connection.rollback()
            print("\n⚠ This booking is not eligible for feedback.")
            return

        cursor.execute("""
            INSERT INTO Ratings_Feedback
            (
                booking_id,
                ride_id,
                driver_id,
                seeker_id,
                rating,
                comment
            )
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (
            selected["booking_id"],
            current_booking["ride_id"],
            current_booking["driver_id"],
            user_id,
            rating,
            comment if comment else None
        ))

        connection.commit()

        print("\n" + "=" * 60)
        print("✓ FEEDBACK SUBMITTED SUCCESSFULLY!".center(60))
        print("=" * 60)

        print("\n✓ Thank you for sharing your experience.")

    except c.Error as e:
        connection.rollback()

        if e.errno == 1062:
            print("\n⚠ Feedback has already been submitted for this booking.")
        else:
            print("\n✗ Feedback Submission Error:", e)

    finally:
        if cursor is not None:
            cursor.close()

        connection.close()


def ride_seeker_menu(user_id):
    while True:
        print("\n" + "=" * 60)
        print("🚘 RIDESYNC - RIDE SEEKER".center(60))
        print("SHARE SEATS, SHARE SAFETY".center(60))
        print("=" * 60)

        print("1.  🔍 Search Rides and Send Request")
        print("2.  📋 View My Ride Requests")
        print("3.  📖 View My Bookings and History")
        print("4.  ✖ Cancel Booking")
        print("5.  👤 View Driver Details")
        print("6.  ⭐ Give Ride Feedback")
        print("7.  ↩ Logout")

        print("=" * 60)

        show_guidelines(
            "RIDE SEEKER MENU GUIDELINES",
            [
                "Enter 1 to search for available rides.",
                "Enter 2 to view your ride requests.",
                "Enter 3 to view your bookings and history.",
                "Enter 4 to cancel a confirmed booking.",
                "Enter 5 to view driver and vehicle details.",
                "Enter 6 to give feedback for a completed ride.",
                "Enter 7 to logout."
            ]
        )

        choice = input("\n➜ Enter your choice (1-7): ").strip()

        if choice == "1":
            search_rides(user_id)
        elif choice == "2":
            view_my_ride_requests(user_id)
        elif choice == "3":
            view_booked_rides(user_id)
        elif choice == "4":
            cancel_booking(user_id)
        elif choice == "5":
            view_driver_details(user_id)
        elif choice == "6":
            give_ride_feedback(user_id)
        elif choice == "7":
            print("\n" + "=" * 60)
            print("✓ LOGGED OUT SUCCESSFULLY".center(60))
            print("RIDE TOGETHER, REACH TOGETHER".center(60))
            print("=" * 60)
            break
        else:
            print("\n✗ Invalid choice. Please enter a number from 1 to 7.")


if __name__ == "__main__":
    if ensure_database_ready():
        print("\n" + "=" * 60)
        print("✓ RIDESYNC DATABASE IS READY".center(60))
        print("=" * 60)

        print("\nFor standalone testing, enter your registered User ID.")

        user_id = get_positive_integer(
            "Enter your User ID: ",
            1,
            2147483647
        )

        ride_seeker_menu(user_id)

    else:
        print("\n" + "=" * 60)
        print("✗ RIDE SEEKER CANNOT START".center(60))
        print("Database is not ready.".center(60))
        print("=" * 60)
