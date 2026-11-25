
import mysql.connector as c

HOST = "localhost"
USER = "root"
DATABASE = "RideSync_db"
MYSQL_PASSWORD = None


def show_guidelines(title, guidelines):
    print("\n" + "=" * 60)
    print("📌 INPUT GUIDELINES".center(60))
    print("-" * 60)
    print(title.center(60))
    print("-" * 60)

    for guideline in guidelines:
        print("  •", guideline)

    print("=" * 60)


def ask_mysql_password():
    global MYSQL_PASSWORD

    if MYSQL_PASSWORD is None:
        show_guidelines(
            "MYSQL PASSWORD",
            [
                "Enter the password of your local MySQL root account.",
                "The password is required to connect to the MySQL server.",
                "If the password is incorrect, you will be asked to try again."
            ]
        )

        MYSQL_PASSWORD = input("\n➜ Enter MySQL Password: ")

    return MYSQL_PASSWORD


def get_server_connection():
    global MYSQL_PASSWORD

    while True:
        try:
            server_con = c.connect(
                host=HOST,
                user=USER,
                password=ask_mysql_password()
            )

            return server_con

        except c.Error as e:
            if e.errno == 1045:
                print("\n✗ Incorrect MySQL password. Please try again.")
                MYSQL_PASSWORD = None

            else:
                print("\n✗ MySQL server connection error:", e)
                return None


def get_connection():
    global MYSQL_PASSWORD

    while True:
        try:
            con = c.connect(
                host=HOST,
                user=USER,
                password=ask_mysql_password(),
                database=DATABASE
            )

            return con

        except c.Error as e:
            if e.errno == 1045:
                print("\n✗ Incorrect MySQL password. Please try again.")
                MYSQL_PASSWORD = None

            else:
                print("\n✗ Database connection error:", e)
                return None


def initialize_database():
    server_con = None
    server_cursor = None
    con = None
    cursor = None

    try:
        server_con = get_server_connection()

        if server_con is None:
            return False

        server_cursor = server_con.cursor()

        server_cursor.execute(
            "CREATE DATABASE IF NOT EXISTS RideSync_db"
        )

        server_con.commit()

        print("\n✓ Database checked successfully.")

        server_cursor.close()
        server_cursor = None

        server_con.close()
        server_con = None

        con = get_connection()

        if con is None:
            return False

        cursor = con.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS Users (
                user_id INT AUTO_INCREMENT PRIMARY KEY,
                full_name VARCHAR(100) NOT NULL,
                college_id VARCHAR(30) UNIQUE,
                email VARCHAR(150) NOT NULL UNIQUE,
                phone VARCHAR(15) NOT NULL UNIQUE,
                password VARCHAR(255) NOT NULL,
                account_status ENUM(
                    'ACTIVE',
                    'BLOCKED',
                    'INACTIVE'
                ) DEFAULT 'ACTIVE',
                failed_login_attempts INT DEFAULT 0,
                locked_until DATETIME NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS Vehicles (
                vehicle_id INT AUTO_INCREMENT PRIMARY KEY,
                owner_id INT NOT NULL,
                vehicle_name VARCHAR(80) NOT NULL,
                registration_number VARCHAR(20) NOT NULL UNIQUE,
                seating_capacity TINYINT UNSIGNED NOT NULL,
                vehicle_status ENUM(
                    'ACTIVE',
                    'INACTIVE'
                ) DEFAULT 'ACTIVE',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (owner_id)
                    REFERENCES Users(user_id),
                CHECK (seating_capacity > 0)
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS Locations (
                location_id INT AUTO_INCREMENT PRIMARY KEY,
                city VARCHAR(80) NOT NULL,
                region VARCHAR(80),
                area VARCHAR(100) NOT NULL,
                point_name VARCHAR(150) NOT NULL,
                is_active BOOLEAN DEFAULT TRUE
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS Rides (
                ride_id INT AUTO_INCREMENT PRIMARY KEY,
                driver_id INT NOT NULL,
                vehicle_id INT NOT NULL,
                pickup_location_id INT NOT NULL,
                destination_location_id INT NOT NULL,
                ride_date DATE NOT NULL,
                ride_time TIME NOT NULL,
                total_seats TINYINT UNSIGNED NOT NULL,
                available_seats TINYINT UNSIGNED NOT NULL,
                price_per_seat DECIMAL(10,2) NOT NULL DEFAULT 0.00,
                ride_status ENUM(
                    'ACTIVE',
                    'FULL',
                    'COMPLETED',
                    'CANCELLED'
                ) DEFAULT 'ACTIVE',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (driver_id)
                    REFERENCES Users(user_id),
                FOREIGN KEY (vehicle_id)
                    REFERENCES Vehicles(vehicle_id),
                FOREIGN KEY (pickup_location_id)
                    REFERENCES Locations(location_id),
                FOREIGN KEY (destination_location_id)
                    REFERENCES Locations(location_id),
                CHECK (total_seats > 0),
                CHECK (available_seats <= total_seats),
                CHECK (
                    pickup_location_id <> destination_location_id
                )
            )
        """)

        cursor.execute("""
            SHOW COLUMNS FROM Rides
            LIKE 'price_per_seat'
        """)

        price_column = cursor.fetchone()

        if price_column is None:
            cursor.execute("""
                ALTER TABLE Rides
                ADD COLUMN price_per_seat
                DECIMAL(10,2) NOT NULL DEFAULT 0.00
            """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS Ride_Requests (
                request_id INT AUTO_INCREMENT PRIMARY KEY,
                ride_id INT NOT NULL,
                seeker_id INT NOT NULL,
                seats_requested TINYINT UNSIGNED NOT NULL,
                request_status ENUM(
                    'PENDING',
                    'ACCEPTED',
                    'REJECTED',
                    'CANCELLED',
                    'EXPIRED'
                ) DEFAULT 'PENDING',
                requested_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                responded_at DATETIME NULL,
                FOREIGN KEY (ride_id)
                    REFERENCES Rides(ride_id),
                FOREIGN KEY (seeker_id)
                    REFERENCES Users(user_id),
                CHECK (seats_requested > 0)
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS Bookings (
                booking_id INT AUTO_INCREMENT PRIMARY KEY,
                request_id INT NOT NULL UNIQUE,
                ride_id INT NOT NULL,
                seeker_id INT NOT NULL,
                seats_booked TINYINT UNSIGNED NOT NULL,
                booking_status ENUM(
                    'CONFIRMED',
                    'CANCELLED',
                    'COMPLETED'
                ) DEFAULT 'CONFIRMED',
                booked_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                cancelled_at DATETIME NULL,
                FOREIGN KEY (request_id)
                    REFERENCES Ride_Requests(request_id),
                FOREIGN KEY (ride_id)
                    REFERENCES Rides(ride_id),
                FOREIGN KEY (seeker_id)
                    REFERENCES Users(user_id),
                CHECK (seats_booked > 0)
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS Ratings_Feedback (
                feedback_id INT AUTO_INCREMENT PRIMARY KEY,
                booking_id INT NOT NULL UNIQUE,
                ride_id INT NOT NULL,
                driver_id INT NOT NULL,
                seeker_id INT NOT NULL,
                rating TINYINT UNSIGNED NOT NULL,
                comment VARCHAR(1000),
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (booking_id)
                    REFERENCES Bookings(booking_id),
                FOREIGN KEY (ride_id)
                    REFERENCES Rides(ride_id),
                FOREIGN KEY (driver_id)
                    REFERENCES Users(user_id),
                FOREIGN KEY (seeker_id)
                    REFERENCES Users(user_id),
                CHECK (rating BETWEEN 1 AND 5)
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS Reports (
                report_id INT AUTO_INCREMENT PRIMARY KEY,
                reported_by INT NOT NULL,
                related_user_id INT NULL,
                ride_id INT NULL,
                description TEXT NOT NULL,
                report_status ENUM(
                    'PENDING',
                    'UNDER_REVIEW',
                    'RESOLVED',
                    'REJECTED'
                ) DEFAULT 'PENDING',
                admin_action TEXT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                resolved_at DATETIME NULL,
                FOREIGN KEY (reported_by)
                    REFERENCES Users(user_id),
                FOREIGN KEY (related_user_id)
                    REFERENCES Users(user_id),
                FOREIGN KEY (ride_id)
                    REFERENCES Rides(ride_id)
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS Audit_Records (
                audit_id BIGINT AUTO_INCREMENT PRIMARY KEY,
                user_id INT NULL,
                action VARCHAR(100) NOT NULL,
                details TEXT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id)
                    REFERENCES Users(user_id)
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS Admin (
                admin_id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
                full_name VARCHAR(100) NOT NULL,
                email VARCHAR(150) NOT NULL UNIQUE,
                phone VARCHAR(15) NOT NULL UNIQUE,
                password VARCHAR(255) NOT NULL,
                admin_status ENUM(
                    'ACTIVE',
                    'BLOCKED',
                    'INACTIVE'
                ) DEFAULT 'ACTIVE',
                failed_login_attempts INT DEFAULT 0,
                locked_until DATETIME NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)

        con.commit()

        print("\n✓ All 10 tables checked/created successfully.")
        print("✓ RideSync database is ready!")

        return True

    except c.Error as e:
        if con is not None:
            con.rollback()

        print("\n✗ Database initialization error:", e)
        return False

    finally:
        if cursor is not None:
            cursor.close()

        if con is not None and con.is_connected():
            con.close()

        if server_cursor is not None:
            server_cursor.close()

        if server_con is not None and server_con.is_connected():
            server_con.close()


def ensure_database_ready():
    print("\n" + "=" * 60)
    print("RIDESYNC DATABASE".center(60))
    print("=" * 60)

    print("\n➜ Checking database connection and tables...")

    return initialize_database()


if __name__ == "__main__":
    if ensure_database_ready():
        print("\n" + "=" * 60)
        print("✓ DATABASE INITIALIZATION SUCCESSFUL".center(60))
        print("=" * 60)

    else:
        print("\n" + "=" * 60)
        print("✗ DATABASE INITIALIZATION FAILED".center(60))
        print("=" * 60)
