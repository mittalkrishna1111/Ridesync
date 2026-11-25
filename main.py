import time
import sys
import builtins

def slow_print(*args, sep=' ', end='\n'):
    text = sep.join(map(str, args)) + end

    for char in text:
        sys.stdout.write(char)
        sys.stdout.flush()
        time.sleep(0.015)

builtins.print = slow_print

import mysql.connector as c
from datetime import datetime, timedelta

from database import get_connection, ensure_database_ready
from ride_giver import ride_giver_menu
from ride_seeker import ride_seeker_menu
from admin import admin_menu


def show_guidelines(title, guidelines):
    print("\n" + "=" * 60)
    print("📌 INPUT GUIDELINES".center(60))
    print("-" * 60)
    print(title.center(60))
    print("-" * 60)

    for guideline in guidelines:
        print("  •", guideline)

    print("=" * 60)


def get_full_name():
    while True:
        show_guidelines(
            "FULL NAME GUIDELINES",
            [
                "Only alphabets and spaces are allowed.",
                "Name cannot be empty."
            ]
        )

        name = input("\n➜ Enter your Full Name: ").strip()

        if name and name.replace(" ", "").isalpha():
            return name

        print("\n✗ Invalid Name. Please enter alphabets only.\n")


def get_college_id():
    while True:
        show_guidelines(
            "COLLEGE ID GUIDELINES",
            [
                "College ID cannot be empty.",
                "Maximum 30 characters are allowed."
            ]
        )

        college_id = input("\n➜ Enter your College ID: ").strip()

        if 0 < len(college_id) <= 30:
            return college_id

        print("\n✗ Invalid College ID. Please follow the instructions.\n")


def get_email():
    while True:
        show_guidelines(
            "EMAIL GUIDELINES",
            [
                "Must end with '@gmail.com' or '@bennett.edu.in'.",
                "Username must have at least 8 characters.",
                "Username can contain alphabets and digits only.",
                "Special characters are not allowed."
            ]
        )

        email = input("\n➜ Enter your Email ID: ").strip().lower()

        if email.count("@") != 1:
            print("\n✗ Invalid Email ID. Please follow the guidelines.\n")
            continue

        if email.endswith("@gmail.com"):
            username = email[:-10]
        elif email.endswith("@bennett.edu.in"):
            username = email[:-15]
        else:
            print("\n✗ Invalid Email ID. Use Gmail or Bennett University email.\n")
            continue

        if len(username) >= 8 and username.isalnum():
            return email

        print("\n✗ Invalid Email ID. Please follow the guidelines.\n")


def get_phone():
    while True:
        show_guidelines(
            "PHONE NUMBER GUIDELINES",
            [
                "Must contain exactly 10 digits.",
                "Alphabets are not allowed.",
                "Special characters are not allowed.",
                "Phone number is compulsory."
            ]
        )

        phone = input("\n➜ Enter your Phone Number: ").strip()

        if len(phone) == 10 and phone.isdigit():
            return phone

        print("\n✗ Invalid Phone Number. Enter exactly 10 digits.\n")


def get_password():
    while True:
        show_guidelines(
            "PASSWORD GUIDELINES",
            [
                "Must have at least 8 characters.",
                "Must include at least one alphabet.",
                "Only alphabets and digits are allowed."
            ]
        )

        password = input("\n➜ Enter your Password: ")

        if len(password) >= 8:
            if (password.isalnum() and
                    password.isascii() and
                    any(ch.isalpha() for ch in password)):
                return password

            print("\n✗ Invalid Password. Please follow the guidelines.\n")
        else:
            print("\n✗ Password must have at least 8 characters.\n")


def register_user():
    print("\n" + "=" * 60)
    print("📝 USER REGISTRATION PORTAL".center(60))
    print("=" * 60)

    full_name = get_full_name()
    college_id = get_college_id()
    email = get_email()
    phone = get_phone()
    password = get_password()

    connection = get_connection()

    if connection is None:
        print("\n" + "=" * 60)
        print("✗ DATABASE CONNECTION FAILED".center(60))
        print("=" * 60 + "\n")
        return None

    cursor = None

    try:
        cursor = connection.cursor()
        connection.start_transaction()

        cursor.execute("""
            INSERT INTO Users
            (full_name, college_id, email, phone, password)
            VALUES (%s, %s, %s, %s, %s)
        """, (
            full_name,
            college_id,
            email,
            phone,
            password
        ))

        user_id = cursor.lastrowid
        connection.commit()

        print("\n" + "=" * 60)
        print("✓ REGISTRATION SUCCESSFUL!".center(60))
        print("=" * 60)
        print(f"🆔 Your User ID: {user_id}")
        print("➜ You can now log in using your registered email and password.")
        print("=" * 60 + "\n")

        return user_id

    except c.Error as e:
        connection.rollback()

        print("\n" + "=" * 60)
        print("✗ REGISTRATION FAILED".center(60))
        print("=" * 60)

        if e.errno == 1062:
            print("⚠ College ID, Email ID or Phone Number already exists.")
        else:
            print("⚠ Registration Error:", e)

        print("=" * 60 + "\n")
        return None

    finally:
        if cursor is not None:
            cursor.close()

        connection.close()


def login_user():
    print("\n" + "=" * 60)
    print("🔐 USER LOGIN PORTAL".center(60))
    print("=" * 60)

    show_guidelines(
        "EMAIL GUIDELINES",
        [
            "Enter the email registered with RideSync.",
            "Use your complete email address.",
            "Do not leave this field empty."
        ]
    )

    email = input("\n➜ Enter your Email ID: ").strip().lower()

    connection = get_connection()

    if connection is None:
        print("\n✗ Unable to connect to database.\n")
        return None

    cursor = None

    try:
        cursor = connection.cursor(dictionary=True)

        while True:
            connection.start_transaction()

            cursor.execute("""
                SELECT
                    user_id,
                    password,
                    account_status,
                    failed_login_attempts,
                    locked_until
                FROM Users
                WHERE email = %s
                FOR UPDATE
            """, (email,))

            user = cursor.fetchone()

            if user is None:
                connection.rollback()
                print("\n✗ Invalid Email ID.\n")
                return None

            if user["account_status"] != "ACTIVE":
                connection.rollback()
                print("\n" + "=" * 60)
                print("⚠ ACCOUNT INACTIVE".center(60))
                print("=" * 60)
                print("➜ Please contact the administrator.")
                print("=" * 60 + "\n")
                return None

            current_time = datetime.now()
            locked_until = user["locked_until"]

            if locked_until is not None and locked_until > current_time:
                connection.rollback()

                remaining_time = locked_until - current_time

                remaining_minutes = int(
                    (remaining_time.total_seconds() + 59) // 60
                )

                print("\n" + "=" * 60)
                print("🔒 ACCOUNT TEMPORARILY LOCKED".center(60))
                print("=" * 60)
                print("➜ Please try again after", remaining_minutes, "minutes.")
                print("=" * 60 + "\n")

                return None

            if locked_until is not None and locked_until <= current_time:
                cursor.execute("""
                    UPDATE Users
                    SET failed_login_attempts = 0,
                        locked_until = NULL
                    WHERE user_id = %s
                """, (user["user_id"],))

                connection.commit()
                user["failed_login_attempts"] = 0

            show_guidelines(
                "PASSWORD GUIDELINES",
                [
                    "Enter the password used during registration.",
                    "Password is case-sensitive.",
                    "You have a maximum of 5 failed attempts."
                ]
            )

            password = input("\n➜ Enter your Password: ")

            if password == user["password"]:
                cursor.execute("""
                    UPDATE Users
                    SET failed_login_attempts = 0,
                        locked_until = NULL
                    WHERE user_id = %s
                """, (user["user_id"],))

                connection.commit()

                print("\n" + "=" * 60)
                print("✓ LOGIN SUCCESSFUL!".center(60))
                print("=" * 60)
                print("🚗 Welcome to RideSync!")
                print("=" * 60 + "\n")

                return user["user_id"]

            else:
                attempts = (user["failed_login_attempts"] or 0) + 1

                if attempts >= 5:
                    lock_time = current_time + timedelta(minutes=15)

                    cursor.execute("""
                        UPDATE Users
                        SET failed_login_attempts = 5,
                            locked_until = %s
                        WHERE user_id = %s
                    """, (
                        lock_time,
                        user["user_id"]
                    ))

                    connection.commit()

                    print("\n" + "=" * 60)
                    print("🔒 TOO MANY INCORRECT ATTEMPTS".center(60))
                    print("=" * 60)
                    print("⚠ Your account is locked for 15 minutes.")
                    print("=" * 60 + "\n")

                    return None

                else:
                    cursor.execute("""
                        UPDATE Users
                        SET failed_login_attempts = %s
                        WHERE user_id = %s
                    """, (
                        attempts,
                        user["user_id"]
                    ))

                    connection.commit()

                    print("\n✗ Incorrect Password.")
                    print(f"⚠ Attempts remaining: {5 - attempts}")
                    print("➜ Please try again.\n")

    except c.Error as e:
        connection.rollback()
        print("\n✗ Login Error:", e)
        return None

    finally:
        if cursor is not None:
            cursor.close()

        connection.close()


def user_portal():
    while True:
        print("\n" + "=" * 60)
        print("👤 USER PORTAL".center(60))
        print("=" * 60)
        print("1. 📝 Register")
        print("2. 🔐 Login")
        print("3. ↩️ Back")
        print("=" * 60)

        show_guidelines(
            "USER PORTAL MENU",
            [
                "Enter 1 to create a new RideSync account.",
                "Enter 2 to log in to your existing account.",
                "Enter 3 to return to the main menu."
            ]
        )

        choice = input("\n➜ Enter your choice (1-3): ").strip()

        if choice == "1":
            register_user()

        elif choice == "2":
            user_id = login_user()

            if user_id is not None:
                user_role_menu(user_id)

        elif choice == "3":
            break

        else:
            print("\n⚠ Invalid Choice. Please enter 1, 2 or 3.\n")


def user_role_menu(user_id):
    while True:
        print("\n" + "=" * 60)
        print("🚗 USER DASHBOARD".center(60))
        print("=" * 60)
        print("1. 🚘 Ride Giver")
        print("2. 🧍 Ride Seeker")
        print("3. 🔒 Logout")
        print("=" * 60)

        show_guidelines(
            "USER DASHBOARD MENU",
            [
                "Enter 1 if you want to offer rides to others.",
                "Enter 2 if you want to search and book rides.",
                "Enter 3 to log out of your account."
            ]
        )

        choice = input("\n➜ Enter your choice (1-3): ").strip()

        if choice == "1":
            ride_giver_menu(user_id)

        elif choice == "2":
            ride_seeker_menu(user_id)

        elif choice == "3":
            print("\n" + "=" * 60)
            print("✓ LOGGED OUT SUCCESSFULLY".center(60))
            print("=" * 60 + "\n")
            break

        else:
            print("\n⚠ Invalid choice. Please try again.\n")


def main_menu():
    while True:
        print("\n" + "=" * 60)
        print("🚗 RIDESYNC".center(60))
        print("SHARE SEATS, SHARE SAFETY".center(60))
        print("=" * 60)
        print("1. 🛡️ Admin Portal")
        print("2. 👤 User Portal")
        print("3. 🚪 Exit")
        print("=" * 60)

        show_guidelines(
            "MAIN MENU",
            [
                "Enter 1 to access the Admin Portal.",
                "Enter 2 to register or log in as a user.",
                "Enter 3 to exit RideSync."
            ]
        )

        choice = input("\n➜ Enter your choice (1-3): ").strip()

        if choice == "1":
            admin_menu()

        elif choice == "2":
            user_portal()

        elif choice == "3":
            print("\n" + "=" * 60)
            print("🚗 THANK YOU FOR USING RIDESYNC!".center(60))
            print("🤝 Ride Together, Reach Together".center(60))
            print("=" * 60 + "\n")
            break

        else:
            print("\n⚠ Invalid choice. Please try again.\n")


def run():
    print("\n" + "=" * 60)
    print("🚗 RIDESYNC INITIALIZATION".center(60))
    print("=" * 60)

    if ensure_database_ready():
        print("\n✓ Database initialized successfully.")
        main_menu()
    else:
        print("\n" + "=" * 60)
        print("✗ DATABASE INITIALIZATION FAILED".center(60))
        print("=" * 60)
        print("⚠ RideSync could not be started.")
        print("=" * 60 + "\n")


if __name__ == "__main__":
    run()