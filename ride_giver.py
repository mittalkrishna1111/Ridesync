import mysql.connector as c
from datetime import datetime
from decimal import Decimal, InvalidOperation

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

def get_positive_integer(label, minimum, maximum):
    while True:
        show_guidelines("NUMBER INPUT GUIDELINES", [
            "Enter digits only",
            "Minimum allowed: " + str(minimum),
            "Maximum allowed: " + str(maximum)
        ])

        value = input("\n➜ " + label).strip()

        if value.isdigit():
            value = int(value)

            if minimum <= value <= maximum:
                return value

            print("\n⚠ Enter a number between", minimum, "and", maximum, ".\n")
        else:
            print("\n✗ Please enter digits only.\n")


def get_confirmation(label):
    while True:
        show_guidelines("CONFIRMATION GUIDELINES", [
            "Enter Y or YES to confirm",
            "Enter N or NO to cancel"
        ])

        answer = input("\n➜ " + label + " (Y/N): ").strip().lower()

        if answer in ("y", "yes"):
            return True
        elif answer in ("n", "no"):
            return False

        print("\n⚠ Please enter Y or N.\n")


def get_price_per_seat():
    while True:
        show_guidelines("PRICE GUIDELINES", [
            "Price must be greater than zero",
            "Decimal values are allowed",
            "Maximum price: Rs. 99999999.99"
        ])

        price = input("\n➜ Enter Price Per Seat (Rs.): ").strip()

        try:
            price = Decimal(price)

            if not price.is_finite():
                print("\n✗ Invalid price. Please enter a valid amount.\n")
                continue

            if Decimal("0") < price <= Decimal("99999999.99"):
                return price.quantize(Decimal("0.01"))

            print("\n⚠ Price must be greater than zero and within the allowed limit.\n")

        except InvalidOperation:
            print("\n✗ Invalid price. Enter a valid number.\n")


def get_vehicle_name():
    while True:
        show_guidelines("VEHICLE NAME GUIDELINES", [
            "Cannot be empty",
            "Maximum 80 characters",
            "Must contain letters or numbers"
        ])

        name = input("\n➜ Enter Vehicle Name: ").strip()

        if 0 < len(name) <= 80 and any(ch.isalnum() for ch in name):
            return name

        print("\n✗ Invalid Vehicle Name. Please try again.\n")


def get_registration_number():
    while True:
        show_guidelines("REGISTRATION NUMBER GUIDELINES", [
            "Maximum 20 characters",
            "Only letters and numbers",
            "No spaces or special characters"
        ])

        number = input("\n➜ Enter Vehicle Registration Number: ").strip().upper()

        if 0 < len(number) <= 20 and number.isalnum():
            return number

        print("\n✗ Invalid Registration Number.\n")


def get_seating_capacity(maximum=255):
    while True:
        show_guidelines("SEATING CAPACITY GUIDELINES", [
            "Driver seat is not included",
            "Must be a positive number",
            "Maximum allowed: " + str(maximum),
            "Enter digits only"
        ])

        capacity = input("\n➜ Enter Passenger Seating Capacity: ").strip()

        if capacity.isdigit():
            capacity = int(capacity)

            if 1 <= capacity <= maximum:
                return capacity

            print("\n⚠ Enter a number between 1 and", maximum, ".\n")
        else:
            print("\n✗ Invalid Capacity. Enter digits only.\n")


def register_vehicle(user_id):
    print("\n" + "=" * 60)
    print("🚗 REGISTER NEW VEHICLE".center(60))
    print("=" * 60)

    vehicle_name = get_vehicle_name()
    registration_number = get_registration_number()
    seating_capacity = get_seating_capacity()

    connection = get_connection()

    if connection is None:
        print("\n✗ Unable to connect to database.")
        return

    cursor = None

    try:
        cursor = connection.cursor()

        cursor.execute("""
            INSERT INTO Vehicles
            (owner_id, vehicle_name, registration_number, seating_capacity)
            VALUES (%s, %s, %s, %s)
        """, (
            user_id,
            vehicle_name,
            registration_number,
            seating_capacity
        ))

        connection.commit()

        print("\n" + "=" * 60)
        print("✓ VEHICLE REGISTERED SUCCESSFULLY!".center(60))
        print("=" * 60)

        print("\nVehicle Details:")
        print("-" * 60)
        print("Vehicle Name                 :", vehicle_name)
        print("Registration Number          :", registration_number)
        print("Passenger Seating Capacity   :", seating_capacity)
        print("-" * 60)

    except c.Error as e:
        connection.rollback()

        if e.errno == 1062:
            print("\n✗ This vehicle registration number is already registered.")
        else:
            print("\n✗ Vehicle Registration Error:", e)

    finally:
        if cursor is not None:
            cursor.close()

        connection.close()


def get_location_details(cursor, location_type):
    print("\n" + "=" * 60)
    print(("📍 " + location_type + " LOCATION").center(60))
    print("=" * 60)

    cursor.execute("""
        SELECT location_id, city, region, area, point_name
        FROM Locations
        WHERE is_active = TRUE
        ORDER BY city, area, point_name
    """)

    locations = cursor.fetchall()

    if locations:
        print("\nAvailable Locations:")
        print("-" * 60)

        for i, location in enumerate(locations, start=1):
            print("\n" + str(i) + ". " + location[1])

            if location[2]:
                print("   Region :", location[2])

            print("   Area   :", location[3])
            print("   Point  :", location[4])

        print("\n0. ➜ Enter a New Location")

        while True:
            show_guidelines("LOCATION SELECTION GUIDELINES", [
                "Enter the number of your preferred location",
                "Enter 0 to add a new location",
                "Enter digits only"
            ])

            choice = input(
                "\n➜ Select Location Number (0 for new location): "
            ).strip()

            if choice.isdigit():
                choice = int(choice)

                if choice == 0:
                    break

                if 1 <= choice <= len(locations):
                    selected = locations[choice - 1]

                    print("\n✓ Existing Location Selected Successfully!")

                    return (
                        selected[1],
                        selected[2],
                        selected[3],
                        selected[4]
                    )

                print("\n✗ Invalid Location Number.\n")
            else:
                print("\n⚠ Enter digits only.\n")

    else:
        print("\n⚠ No existing active locations found.")
        print("➜ Please enter a new location.")

    while True:
        show_guidelines("CITY GUIDELINES", [
            "City name cannot be empty",
            "Maximum 80 characters",
            "Must contain at least one letter"
        ])

        city = input("\n➜ Enter City: ").strip()

        if 0 < len(city) <= 80 and any(ch.isalpha() for ch in city):
            break

        print("\n✗ Invalid City. Maximum 80 characters allowed.\n")

    while True:
        show_guidelines("REGION / STATE GUIDELINES", [
            "Maximum 80 characters",
            "This field is optional",
            "Press Enter to skip"
        ])

        region = input("\n➜ Enter Region/State: ").strip()

        if len(region) <= 80:
            break

        print("\n✗ Region cannot exceed 80 characters.\n")

    if region == "":
        region = None

    while True:
        show_guidelines("AREA GUIDELINES", [
            "Area cannot be empty",
            "Maximum 100 characters",
            "Must contain letters or numbers"
        ])

        area = input("\n➜ Enter Area: ").strip()

        if 0 < len(area) <= 100 and any(ch.isalnum() for ch in area):
            break

        print("\n✗ Invalid Area. Maximum 100 characters allowed.\n")

    while True:
        show_guidelines("PICKUP / DROP POINT GUIDELINES", [
            "Point name cannot be empty",
            "Maximum 150 characters",
            "Must contain letters or numbers"
        ])

        point_name = input("\n➜ Enter Pickup/Drop Point Name: ").strip()

        if 0 < len(point_name) <= 150 and any(ch.isalnum() for ch in point_name):
            break

        print("\n✗ Invalid Point Name. Maximum 150 characters allowed.\n")

    return city, region, area, point_name


def locations_are_same(location1, location2):
    for i in range(4):
        value1 = location1[i] or ""
        value2 = location2[i] or ""

        if value1.strip().lower() != value2.strip().lower():
            return False

    return True


def get_or_create_location(cursor, location):
    city, region, area, point_name = location

    cursor.execute("""
        SELECT location_id, is_active
        FROM Locations
        WHERE LOWER(city) = LOWER(%s)
        AND region <=> %s
        AND LOWER(area) = LOWER(%s)
        AND LOWER(point_name) = LOWER(%s)
    """, (
        city,
        region,
        area,
        point_name
    ))

    result = cursor.fetchone()

    if result is not None:
        location_id = result[0]

        if not result[1]:
            cursor.execute("""
                UPDATE Locations
                SET is_active = TRUE
                WHERE location_id = %s
            """, (location_id,))

        return location_id

    cursor.execute("""
        INSERT INTO Locations
        (city, region, area, point_name)
        VALUES (%s, %s, %s, %s)
    """, (
        city,
        region,
        area,
        point_name
    ))

    return cursor.lastrowid


def get_ride_date():
    while True:
        show_guidelines("RIDE DATE GUIDELINES", [
            "Date format: YYYY-MM-DD",
            "Past dates are not allowed",
            "Enter a valid calendar date"
        ])

        ride_date = input("\n➜ Enter Ride Date: ").strip()

        try:
            selected_date = datetime.strptime(
                ride_date, "%Y-%m-%d"
            ).date()

            if selected_date.strftime("%Y-%m-%d") != ride_date:
                print("\n✗ Use the exact YYYY-MM-DD format.\n")
                continue

            if selected_date < datetime.now().date():
                print("\n⚠ Past dates are not allowed.\n")
                continue

            return selected_date

        except ValueError:
            print("\n✗ Invalid Date. Please use YYYY-MM-DD.\n")


def get_ride_time(ride_date):
    while True:
        show_guidelines("RIDE TIME GUIDELINES", [
            "Time format: HH:MM",
            "Use the 24-hour format",
            "Enter a future date and time"
        ])

        ride_time = input("\n➜ Enter Ride Time: ").strip()

        try:
            selected_time = datetime.strptime(
                ride_time, "%H:%M"
            ).time()

            if selected_time.strftime("%H:%M") != ride_time:
                print("\n✗ Use the exact HH:MM format.\n")
                continue

            selected_datetime = datetime.combine(
                ride_date, selected_time
            )

            if selected_datetime <= datetime.now():
                print("\n⚠ Please enter a future date and time.\n")
                continue

            return selected_time

        except ValueError:
            print("\n✗ Invalid Time. Please use HH:MM.\n")


def post_ride(user_id):
    print("\n" + "=" * 60)
    print("🚘 POST A NEW RIDE".center(60))
    print("=" * 60)

    connection = get_connection()

    if connection is None:
        print("\n✗ Unable to connect to database.")
        return

    cursor = None

    try:
        cursor = connection.cursor()

        cursor.execute("""
            SELECT vehicle_id, vehicle_name,
                   registration_number, seating_capacity
            FROM Vehicles
            WHERE owner_id = %s
            AND vehicle_status = 'ACTIVE'
            ORDER BY vehicle_id
        """, (user_id,))

        vehicles = cursor.fetchall()

        if not vehicles:
            print("\n⚠ You have no active registered vehicles.")
            print("➜ Please register a vehicle first.")
            return

        print("\nYour Registered Vehicles:")
        print("-" * 60)

        for i, vehicle in enumerate(vehicles, start=1):
            print("\nVehicle Number              :", i)
            print("Vehicle Name                :", vehicle[1])
            print("Registration Number         :", vehicle[2])
            print("Passenger Seating Capacity  :", vehicle[3])

        print("-" * 60)

        choice = get_positive_integer(
            "Select Vehicle Number: ",
            1,
            len(vehicles)
        )

        selected_vehicle = vehicles[choice - 1]

        vehicle_id = selected_vehicle[0]
        seating_capacity = selected_vehicle[3]

        pickup_location = get_location_details(cursor, "PICKUP")

        while True:
            destination_location = get_location_details(
                cursor, "DESTINATION"
            )

            if not locations_are_same(
                pickup_location,
                destination_location
            ):
                break

            print("\n⚠ Pickup and destination cannot be the same.")

        ride_date = get_ride_date()
        ride_time = get_ride_time(ride_date)

        available_seats = get_seating_capacity(seating_capacity)
        price_per_seat = get_price_per_seat()

        connection.commit()
        connection.start_transaction()

        pickup_location_id = get_or_create_location(
            cursor, pickup_location
        )

        destination_location_id = get_or_create_location(
            cursor, destination_location
        )

        cursor.execute("""
            INSERT INTO Rides
            (
                driver_id,
                vehicle_id,
                pickup_location_id,
                destination_location_id,
                ride_date,
                ride_time,
                total_seats,
                available_seats,
                price_per_seat,
                ride_status
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, 'ACTIVE')
        """, (
            user_id,
            vehicle_id,
            pickup_location_id,
            destination_location_id,
            ride_date,
            ride_time,
            available_seats,
            available_seats,
            price_per_seat
        ))

        ride_id = cursor.lastrowid
        connection.commit()

        print("\n" + "=" * 60)
        print("✓ RIDE POSTED SUCCESSFULLY!".center(60))
        print("=" * 60)

        print("\nRIDE DETAILS")
        print("-" * 60)
        print("Ride ID                    :", ride_id)
        print("Vehicle                    :", selected_vehicle[1])
        print("Registration Number        :", selected_vehicle[2])
        print("Pickup                     :", pickup_location)
        print("Destination                :", destination_location)
        print("Ride Date                  :", ride_date)
        print("Ride Time                  :", ride_time)
        print("Total Passenger Seats      :", available_seats)
        print("Available Seats            :", available_seats)
        print("Price Per Seat             : Rs.", price_per_seat)
        print("Ride Status                : ACTIVE")
        print("-" * 60)

    except c.Error as e:
        connection.rollback()
        print("\n✗ Ride Posting Error:", e)

    finally:
        if cursor is not None:
            cursor.close()

        connection.close()


def manage_ride_requests(user_id):
    print("\n" + "=" * 60)
    print("📩 MANAGE RIDE REQUESTS".center(60))
    print("=" * 60)

    connection = get_connection()

    if connection is None:
        print("\n✗ Unable to connect to database.")
        return

    cursor = None

    try:
        cursor = connection.cursor()

        while True:
            cursor.execute("""
                SELECT
                    rr.request_id,
                    rr.ride_id,
                    u.full_name,
                    u.email,
                    rr.seats_requested,
                    r.available_seats,
                    r.ride_date,
                    r.ride_time,
                    r.price_per_seat
                FROM Ride_Requests rr
                JOIN Rides r
                    ON rr.ride_id = r.ride_id
                JOIN Users u
                    ON rr.seeker_id = u.user_id
                WHERE r.driver_id = %s
                AND rr.request_status = 'PENDING'
                AND r.ride_status = 'ACTIVE'
                ORDER BY r.ride_date, r.ride_time
            """, (user_id,))

            requests = cursor.fetchall()
            connection.commit()

            if not requests:
                print("\n✓ No pending ride requests found.")
                return

            print("\nPENDING RIDE REQUESTS")
            print("-" * 60)

            for i, request in enumerate(requests, start=1):
                print("\nRequest Number       :", i)
                print("Request ID           :", request[0])
                print("Ride ID              :", request[1])
                print("Passenger            :", request[2])
                print("Passenger Email      :", request[3])
                print("Seats Requested      :", request[4])
                print("Available Seats      :", request[5])
                print("Ride Date             :", request[6])
                print("Ride Time             :", request[7])
                print("Price Per Seat       : Rs.", request[8])
                print("-" * 60)

            print("\n0. ➜ Back")

            choice = get_positive_integer(
                "Select Request Number (0 to go back): ",
                0,
                len(requests)
            )

            if choice == 0:
                return

            request_id = requests[choice - 1][0]

            print("\n" + "=" * 60)
            print("REQUEST ACTIONS".center(60))
            print("=" * 60)
            print("1. ✓ Accept Request")
            print("2. ✗ Reject Request")
            print("3. ➜ Back")

            show_guidelines("REQUEST ACTION GUIDELINES", [
                "Enter 1 to accept the request",
                "Enter 2 to reject the request",
                "Enter 3 to go back"
            ])

            action = input("\n➜ Enter your choice (1-3): ").strip()

            if action == "3":
                continue

            if action not in ("1", "2"):
                print("\n✗ Invalid choice.\n")
                continue

            connection.start_transaction()

            cursor.execute("""
                SELECT ride_id, seeker_id, seats_requested, request_status
                FROM Ride_Requests
                WHERE request_id = %s
                FOR UPDATE
            """, (request_id,))

            request = cursor.fetchone()

            if request is None or request[3] != "PENDING":
                connection.rollback()
                print("\n⚠ This request is no longer pending.")
                continue

            ride_id = request[0]
            seeker_id = request[1]
            seats_requested = request[2]

            cursor.execute("""
                SELECT driver_id, available_seats, ride_status
                FROM Rides
                WHERE ride_id = %s
                FOR UPDATE
            """, (ride_id,))

            ride = cursor.fetchone()

            if ride is None or ride[0] != user_id:
                connection.rollback()
                print("\n✗ You cannot manage this ride request.")
                continue

            if action == "1":
                if ride[2] != "ACTIVE":
                    connection.rollback()
                    print("\n⚠ This ride is not accepting requests.")
                    continue

                if ride[1] < seats_requested:
                    connection.rollback()
                    print("\n⚠ Not enough available seats.")
                    continue

                cursor.execute("""
                    INSERT INTO Bookings
                    (
                        request_id,
                        ride_id,
                        seeker_id,
                        seats_booked,
                        booking_status
                    )
                    VALUES (%s, %s, %s, %s, 'CONFIRMED')
                """, (
                    request_id,
                    ride_id,
                    seeker_id,
                    seats_requested
                ))

                cursor.execute("""
                    UPDATE Ride_Requests
                    SET request_status = 'ACCEPTED',
                        responded_at = NOW()
                    WHERE request_id = %s
                """, (request_id,))

                new_available_seats = ride[1] - seats_requested

                new_status = (
                    "FULL" if new_available_seats == 0 else "ACTIVE"
                )

                cursor.execute("""
                    UPDATE Rides
                    SET available_seats = %s,
                        ride_status = %s
                    WHERE ride_id = %s
                """, (
                    new_available_seats,
                    new_status,
                    ride_id
                ))

                connection.commit()

                print("\n" + "=" * 60)
                print("✓ RIDE REQUEST ACCEPTED!".center(60))
                print("=" * 60)
                print("➜ Booking has been confirmed.")
                print("➜ Remaining Seats:", new_available_seats)

            else:
                cursor.execute("""
                    UPDATE Ride_Requests
                    SET request_status = 'REJECTED',
                        responded_at = NOW()
                    WHERE request_id = %s
                """, (request_id,))

                connection.commit()

                print("\n✓ Ride Request Rejected Successfully!")

    except c.Error as e:
        connection.rollback()
        print("\n✗ Ride Request Error:", e)

    finally:
        if cursor is not None:
            cursor.close()

        connection.close()


def remove_registered_vehicle(user_id):
    print("\n" + "=" * 60)
    print("🚗 REMOVE REGISTERED VEHICLE".center(60))
    print("=" * 60)

    connection = get_connection()

    if connection is None:
        print("\n✗ Unable to connect to database.")
        return

    cursor = None

    try:
        cursor = connection.cursor()

        cursor.execute("""
            SELECT vehicle_id, vehicle_name,
                   registration_number, seating_capacity
            FROM Vehicles
            WHERE owner_id = %s
            AND vehicle_status = 'ACTIVE'
            ORDER BY vehicle_id
        """, (user_id,))

        vehicles = cursor.fetchall()

        if not vehicles:
            print("\n⚠ You have no active registered vehicles.")
            return

        print("\nYOUR ACTIVE VEHICLES")
        print("-" * 60)

        for i, vehicle in enumerate(vehicles, start=1):
            print("\n" + str(i) + ". " + vehicle[1])
            print("   Registration Number :", vehicle[2])
            print("   Seating Capacity     :", vehicle[3])

        print("-" * 60)

        choice = get_positive_integer(
            "Select Vehicle Number: ",
            1,
            len(vehicles)
        )

        selected = vehicles[choice - 1]

        print("\nSELECTED VEHICLE")
        print("-" * 60)
        print("Vehicle Name        :", selected[1])
        print("Registration Number :", selected[2])
        print("-" * 60)

        if not get_confirmation(
            "Are you sure you want to remove this vehicle?"
        ):
            print("\n➜ Vehicle removal cancelled.")
            return

        cursor.execute("""
            UPDATE Vehicles
            SET vehicle_status = 'INACTIVE'
            WHERE vehicle_id = %s
            AND owner_id = %s
            AND vehicle_status = 'ACTIVE'
        """, (
            selected[0],
            user_id
        ))

        connection.commit()

        if cursor.rowcount == 1:
            print("\n✓ Vehicle marked as INACTIVE successfully.")
            print("➜ Existing posted rides are not deleted.")
        else:
            print("\n✗ Vehicle could not be removed.")

    except c.Error as e:
        connection.rollback()
        print("\n✗ Vehicle Removal Error:", e)

    finally:
        if cursor is not None:
            cursor.close()

        connection.close()


def view_my_posted_rides(user_id):
    print("\n" + "=" * 60)
    print("🚘 MY ACTIVE POSTED RIDES".center(60))
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
                r.ride_id,
                v.vehicle_name,
                v.registration_number,
                lp.city,
                lp.area,
                lp.point_name,
                ld.city,
                ld.area,
                ld.point_name,
                r.ride_date,
                r.ride_time,
                r.total_seats,
                r.available_seats,
                r.ride_status,
                r.price_per_seat
            FROM Rides r
            JOIN Vehicles v
                ON r.vehicle_id = v.vehicle_id
            JOIN Locations lp
                ON r.pickup_location_id = lp.location_id
            JOIN Locations ld
                ON r.destination_location_id = ld.location_id
            WHERE r.driver_id = %s
            AND r.ride_status IN ('ACTIVE', 'FULL')
            ORDER BY r.ride_date, r.ride_time
        """, (user_id,))

        rides = cursor.fetchall()

        if not rides:
            print("\n⚠ You have no active or full posted rides.")
            return

        for ride in rides:
            print("\n" + "=" * 60)
            print("RIDE ID: " + str(ride[0]))
            print("-" * 60)

            print("Vehicle                  :", ride[1])
            print("Registration Number      :", ride[2])
            print("Pickup                   :", ride[3], ride[4], ride[5])
            print("Destination              :", ride[6], ride[7], ride[8])
            print("Date                     :", ride[9])
            print("Time                     :", ride[10])
            print("Total Passenger Seats    :", ride[11])
            print("Available Seats          :", ride[12])
            print("Status                   :", ride[13])
            print("Price Per Seat           : Rs.", ride[14])

        print("\n" + "=" * 60)

    except c.Error as e:
        print("\n✗ Unable to display rides:", e)

    finally:
        if cursor is not None:
            cursor.close()

        connection.close()


def update_ride_details(user_id):
    print("\n" + "=" * 60)
    print("📝 UPDATE RIDE DETAILS".center(60))
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
                r.ride_id,
                r.pickup_location_id,
                r.destination_location_id,
                r.ride_date,
                r.ride_time,
                r.total_seats,
                r.available_seats,
                r.ride_status,
                v.seating_capacity,
                r.price_per_seat
            FROM Rides r
            JOIN Vehicles v
                ON r.vehicle_id = v.vehicle_id
            WHERE r.driver_id = %s
            AND r.ride_status IN ('ACTIVE', 'FULL')
            AND r.ride_date >= CURDATE()
            ORDER BY r.ride_date, r.ride_time
        """, (user_id,))

        rides = cursor.fetchall()
        connection.commit()

        if not rides:
            print("\n⚠ No eligible rides available for updating.")
            return

        print("\nYOUR RIDES")
        print("-" * 60)

        for i, ride in enumerate(rides, start=1):
            print("\n" + str(i) + ". Ride ID:", ride[0])
            print("   Date             :", ride[3])
            print("   Time             :", ride[4])
            print("   Total Seats      :", ride[5])
            print("   Available Seats  :", ride[6])
            print("   Status           :", ride[7])
            print("   Price Per Seat   : Rs.", ride[9])

        print("-" * 60)

        choice = get_positive_integer(
            "Select Ride Number: ",
            1,
            len(rides)
        )

        selected_ride = rides[choice - 1]
        ride_id = selected_ride[0]

        while True:
            print("\n" + "=" * 60)
            print("UPDATE RIDE MENU".center(60))
            print("=" * 60)

            print("1. 📍 Update Pickup Location")
            print("2. 📍 Update Destination Location")
            print("3. 📅 Update Ride Date and Time")
            print("4. 💺 Update Passenger Seats")
            print("5. 💰 Update Price Per Seat")
            print("6. ➜ Back")

            show_guidelines("UPDATE RIDE GUIDELINES", [
                "Enter 1 to update pickup location",
                "Enter 2 to update destination location",
                "Enter 3 to update ride date and time",
                "Enter 4 to update passenger seats",
                "Enter 5 to update price per seat",
                "Enter 6 to go back"
            ])

            option = input("\n➜ Enter your choice (1-6): ").strip()

            if option == "6":
                break

            if option not in ("1", "2", "3", "4", "5"):
                print("\n✗ Invalid Choice.")
                continue

            cursor.execute("""
                SELECT COUNT(*)
                FROM Bookings
                WHERE ride_id = %s
                AND booking_status = 'CONFIRMED'
            """, (ride_id,))

            confirmed_bookings = cursor.fetchone()[0]
            connection.commit()

            if option in ("1", "2", "3") and confirmed_bookings > 0:
                print("\n⚠ This ride has confirmed bookings.")
                print("➜ Route, date and time cannot be changed.")
                continue

            if option in ("1", "2"):
                location_type = (
                    "NEW PICKUP" if option == "1"
                    else "NEW DESTINATION"
                )

                new_location = get_location_details(
                    cursor, location_type
                )

                connection.commit()
                connection.start_transaction()

                cursor.execute("""
                    SELECT pickup_location_id,
                           destination_location_id,
                           ride_status
                    FROM Rides
                    WHERE ride_id = %s
                    AND driver_id = %s
                    FOR UPDATE
                """, (ride_id, user_id))

                current_ride = cursor.fetchone()

                if current_ride is None or current_ride[2] not in ("ACTIVE", "FULL"):
                    connection.rollback()
                    print("\n⚠ This ride can no longer be updated.")
                    break

                new_location_id = get_or_create_location(
                    cursor, new_location
                )

                if option == "1":
                    if new_location_id == current_ride[1]:
                        connection.rollback()
                        print("\n⚠ Pickup and destination cannot be the same.")
                        continue

                    cursor.execute("""
                        UPDATE Rides
                        SET pickup_location_id = %s
                        WHERE ride_id = %s
                        AND driver_id = %s
                    """, (new_location_id, ride_id, user_id))

                else:
                    if new_location_id == current_ride[0]:
                        connection.rollback()
                        print("\n⚠ Pickup and destination cannot be the same.")
                        continue

                    cursor.execute("""
                        UPDATE Rides
                        SET destination_location_id = %s
                        WHERE ride_id = %s
                        AND driver_id = %s
                    """, (new_location_id, ride_id, user_id))

                connection.commit()
                print("\n✓ Location updated successfully.")

            elif option == "3":
                new_date = get_ride_date()
                new_time = get_ride_time(new_date)

                connection.commit()
                connection.start_transaction()

                cursor.execute("""
                    SELECT ride_status
                    FROM Rides
                    WHERE ride_id = %s
                    AND driver_id = %s
                    FOR UPDATE
                """, (ride_id, user_id))

                current_ride = cursor.fetchone()

                if current_ride is None or current_ride[0] not in ("ACTIVE", "FULL"):
                    connection.rollback()
                    print("\n⚠ This ride can no longer be updated.")
                    break

                cursor.execute("""
                    UPDATE Rides
                    SET ride_date = %s,
                        ride_time = %s
                    WHERE ride_id = %s
                    AND driver_id = %s
                """, (
                    new_date,
                    new_time,
                    ride_id,
                    user_id
                ))

                connection.commit()
                print("\n✓ Ride Date and Time updated successfully.")

            elif option == "4":
                vehicle_capacity = selected_ride[8]

                connection.commit()
                connection.start_transaction()

                cursor.execute("""
                    SELECT total_seats,
                           available_seats,
                           ride_status
                    FROM Rides
                    WHERE ride_id = %s
                    AND driver_id = %s
                    FOR UPDATE
                """, (ride_id, user_id))

                current_ride = cursor.fetchone()

                if current_ride is None or current_ride[2] not in ("ACTIVE", "FULL"):
                    connection.rollback()
                    print("\n⚠ This ride can no longer be updated.")
                    break

                old_total_seats = current_ride[0]
                old_available_seats = current_ride[1]

                booked_seats = old_total_seats - old_available_seats

                print("\n➜ Already Booked Seats:", booked_seats)

                new_total_seats = get_seating_capacity(
                    vehicle_capacity
                )

                if new_total_seats < booked_seats:
                    connection.rollback()
                    print("\n✗ New seat capacity cannot be less than")
                    print("  the number of already booked seats.")
                    continue

                new_available_seats = new_total_seats - booked_seats

                new_status = (
                    "FULL" if new_available_seats == 0 else "ACTIVE"
                )

                cursor.execute("""
                    UPDATE Rides
                    SET total_seats = %s,
                        available_seats = %s,
                        ride_status = %s
                    WHERE ride_id = %s
                    AND driver_id = %s
                """, (
                    new_total_seats,
                    new_available_seats,
                    new_status,
                    ride_id,
                    user_id
                ))

                connection.commit()

                print("\n✓ PASSENGER SEAT DETAILS UPDATED")
                print("-" * 60)
                print("Total Seats       :", new_total_seats)
                print("Available Seats   :", new_available_seats)

            elif option == "5":
                print(
                    "\n➜ Current Price Per Seat: Rs.",
                    selected_ride[9]
                )

                new_price = get_price_per_seat()

                connection.commit()
                connection.start_transaction()

                cursor.execute("""
                    SELECT ride_status
                    FROM Rides
                    WHERE ride_id = %s
                    AND driver_id = %s
                    FOR UPDATE
                """, (ride_id, user_id))

                current_ride = cursor.fetchone()

                if current_ride is None or current_ride[0] not in ("ACTIVE", "FULL"):
                    connection.rollback()
                    print("\n⚠ This ride can no longer be updated.")
                    break

                cursor.execute("""
                    UPDATE Rides
                    SET price_per_seat = %s
                    WHERE ride_id = %s
                    AND driver_id = %s
                """, (
                    new_price,
                    ride_id,
                    user_id
                ))

                connection.commit()

                print("\n✓ Price Per Seat Updated Successfully!")
                print("➜ New Price Per Seat: Rs.", new_price)

    except c.Error as e:
        connection.rollback()
        print("\n✗ Ride Update Error:", e)

    finally:
        if cursor is not None:
            cursor.close()

        connection.close()


def view_ride_feedback(user_id):
    print("\n" + "=" * 60)
    print("⭐ RIDE FEEDBACK".center(60))
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
                rf.feedback_id,
                rf.booking_id,
                rf.ride_id,
                u.full_name,
                rf.rating,
                rf.comment,
                rf.created_at
            FROM Ratings_Feedback rf
            JOIN Users u
                ON rf.seeker_id = u.user_id
            WHERE rf.driver_id = %s
            ORDER BY rf.created_at DESC
        """, (user_id,))

        feedbacks = cursor.fetchall()

        if not feedbacks:
            print("\n⚠ No feedback received yet.")
            return

        for feedback in feedbacks:
            print("\n" + "=" * 60)
            print("FEEDBACK ID: " + str(feedback[0]))
            print("-" * 60)

            print("Booking ID       :", feedback[1])
            print("Ride ID          :", feedback[2])
            print("Passenger Name   :", feedback[3])
            print("Rating           :", feedback[4], "/ 5")

            if feedback[5]:
                print("Comment          :", feedback[5])
            else:
                print("Comment          : No comment provided")

            print("Date             :", feedback[6])

        print("\n" + "=" * 60)

    except c.Error as e:
        print("\n✗ Unable to display feedback:", e)

    finally:
        if cursor is not None:
            cursor.close()

        connection.close()


def view_all_rides_history(user_id):
    print("\n" + "=" * 60)
    print("📋 ALL RIDES HISTORY".center(60))
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
                r.ride_id,
                v.vehicle_name,
                v.registration_number,
                lp.city,
                lp.area,
                lp.point_name,
                ld.city,
                ld.area,
                ld.point_name,
                r.ride_date,
                r.ride_time,
                r.total_seats,
                r.available_seats,
                r.ride_status,
                r.price_per_seat
            FROM Rides r
            JOIN Vehicles v
                ON r.vehicle_id = v.vehicle_id
            JOIN Locations lp
                ON r.pickup_location_id = lp.location_id
            JOIN Locations ld
                ON r.destination_location_id = ld.location_id
            WHERE r.driver_id = %s
            ORDER BY r.ride_date DESC, r.ride_time DESC
        """, (user_id,))

        rides = cursor.fetchall()

        if not rides:
            print("\n⚠ You have not posted any rides yet.")
            return

        for ride in rides:
            print("\n" + "=" * 60)
            print("RIDE ID: " + str(ride[0]))
            print("-" * 60)

            print("Vehicle                  :", ride[1])
            print("Registration Number      :", ride[2])
            print("Pickup                   :", ride[3], ride[4], ride[5])
            print("Destination              :", ride[6], ride[7], ride[8])
            print("Date                     :", ride[9])
            print("Time                     :", ride[10])
            print("Total Passenger Seats    :", ride[11])
            print("Available Seats          :", ride[12])
            print("Ride Status              :", ride[13])
            print("Price Per Seat           : Rs.", ride[14])

        print("\n" + "=" * 60)

    except c.Error as e:
        print("\n✗ Unable to display ride history:", e)

    finally:
        if cursor is not None:
            cursor.close()

        connection.close()


def ride_giver_menu(user_id):
    while True:
        print("\n" + "=" * 60)
        print("🚗 RIDESYNC - RIDE GIVER".center(60))
        print("SHARE SEATS, SHARE SAFETY".center(60))
        print("=" * 60)

        print("1.  🚘 Register Vehicle")
        print("2.  ➜ Post a Ride")
        print("3.  📩 Manage Ride Requests")
        print("4.  ✗ Remove Registered Vehicle")
        print("5.  📋 View My Posted Rides")
        print("6.  📝 Update Ride Details")
        print("7.  ⭐ View Ride Feedback")
        print("8.  📜 View All Rides History")
        print("9.  ↩ Logout")

        print("=" * 60)

        show_guidelines("RIDE GIVER MENU GUIDELINES", [
            "Enter 1 to register a vehicle",
            "Enter 2 to post a new ride",
            "Enter 3 to manage ride requests",
            "Enter 4 to remove a registered vehicle",
            "Enter 5 to view your posted rides",
            "Enter 6 to update ride details",
            "Enter 7 to view ride feedback",
            "Enter 8 to view all rides history",
            "Enter 9 to logout"
        ])

        choice = input("\n➜ Enter your choice (1-9): ").strip()

        if choice == "1":
            register_vehicle(user_id)
        elif choice == "2":
            post_ride(user_id)
        elif choice == "3":
            manage_ride_requests(user_id)
        elif choice == "4":
            remove_registered_vehicle(user_id)
        elif choice == "5":
            view_my_posted_rides(user_id)
        elif choice == "6":
            update_ride_details(user_id)
        elif choice == "7":
            view_ride_feedback(user_id)
        elif choice == "8":
            view_all_rides_history(user_id)
        elif choice == "9":
            print("\n" + "=" * 60)
            print("✓ LOGGED OUT SUCCESSFULLY".center(60))
            print("RIDE TOGETHER, REACH TOGETHER".center(60))
            print("=" * 60)
            break
        else:
            print("\n✗ Invalid Choice. Please enter a number from 1 to 9.")


if __name__ == "__main__":
    if ensure_database_ready():
        print("\n" + "=" * 60)
        print("✓ RIDE GIVER MODULE IS READY".center(60))
        print("=" * 60)
        print("➜ Please run main.py to log in and access Ride Giver.")
    else:
        print("\n" + "=" * 60)
        print("✗ RIDE GIVER MODULE COULD NOT START".center(60))
        print("=" * 60)
        print("⚠ The database is not ready.")
