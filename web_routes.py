"""Flask routes connecting RideSync templates to web_services."""

from functools import wraps
from flask import flash, redirect, render_template, request, session, url_for

from web_app import rotate_user_session
from web_services import (
    admin_get_dashboard_stats,
    admin_list_audit_logs,
    admin_list_feedback,
    admin_list_ongoing_rides,
    admin_list_reports,
    admin_list_users,
    admin_list_vehicles,
    admin_login_service,
    admin_portal_register_service,
    admin_record_logout_audit,
    admin_register_service,
    admin_update_report,
    admin_update_user_status,
    admin_update_vehicle_status,
    cancel_booking_service,
    get_active_locations,
    get_driver_details_for_booking,
    get_eligible_feedback_bookings,
    get_giver_ride_history,
    get_incoming_ride_requests,
    get_my_bookings,
    get_my_posted_rides,
    get_my_ride_requests,
    get_received_feedback,
    get_ride_details,
    get_updatable_ride,
    get_user_dashboard_stats,
    get_user_profile,
    get_user_vehicles,
    list_available_rides,
    login_user_service,
    post_ride_service,
    register_user_service,
    register_vehicle_service,
    remove_vehicle_service,
    request_ride_service,
    respond_to_ride_request_service,
    search_matching_rides,
    submit_feedback_service,
    update_ride_service,
)


def user_login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("user_id") or session.get("role") != "user":
            flash("Please log in to access this page.", "warning")
            return redirect(url_for("login"))
        return view(*args, **kwargs)

    return wrapped


def admin_login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("admin_id") or session.get("role") != "admin":
            flash("Admin authentication is required.", "warning")
            return redirect(url_for("admin_login"))
        return view(*args, **kwargs)

    return wrapped


def register_routes(app):
    # --------------------------------------------------------------------------
    # PUBLIC & AUTHENTICATION
    # --------------------------------------------------------------------------
    @app.route("/")
    def home():
        return render_template("index.html")

    @app.route("/about")
    def about():
        return render_template("about.html")

    @app.route("/safety")
    def safety():
        return render_template("safety.html")

    @app.route("/register", methods=["GET", "POST"])
    def register():
        if session.get("user_id") and session.get("role") == "user":
            return redirect(url_for("dashboard"))

        form_data = {}
        if request.method == "POST":
            form_data = {
                "full_name": request.form.get("full_name", ""),
                "college_id": request.form.get("college_id", ""),
                "email": request.form.get("email", ""),
                "phone": request.form.get("phone", ""),
            }
            ok, msg, _user_id = register_user_service(
                form_data["full_name"],
                form_data["college_id"],
                form_data["email"],
                form_data["phone"],
                request.form.get("password", ""),
                request.form.get("confirm_password", ""),
            )
            if ok:
                flash(msg, "success")
                return redirect(url_for("login"))
            flash(msg, "error")

        return render_template("register.html", form_data=form_data)

    @app.route("/login", methods=["GET", "POST"])
    def login():
        if session.get("user_id") and session.get("role") == "user":
            return redirect(url_for("dashboard"))

        form_data = {}
        if request.method == "POST":
            email = request.form.get("email", "")
            form_data = {"email": email}
            ok, msg, user_info = login_user_service(email, request.form.get("password", ""))
            if ok:
                rotate_user_session(session)
                session["user_id"] = user_info["user_id"]
                session["user_name"] = user_info["full_name"]
                session["role"] = "user"
                flash(msg, "success")
                return redirect(url_for("dashboard"))
            flash(msg, "error")

        return render_template("login.html", form_data=form_data)

    @app.route("/logout", methods=["POST"])
    def logout():
        rotate_user_session(session)
        flash("Logged out successfully.", "success")
        return redirect(url_for("home"))

    @app.route("/dashboard")
    @user_login_required
    def dashboard():
        user_id = session["user_id"]
        user = get_user_profile(user_id)
        if not user:
            rotate_user_session(session)
            flash("User account not found.", "error")
            return redirect(url_for("login"))
        stats = get_user_dashboard_stats(user_id)
        return render_template("dashboard.html", user=user, stats=stats)

    @app.route("/profile")
    @user_login_required
    def profile():
        user = get_user_profile(session["user_id"])
        if not user:
            rotate_user_session(session)
            flash("User account not found.", "error")
            return redirect(url_for("login"))
        return render_template("profile.html", user=user)

    # --------------------------------------------------------------------------
    # RIDE SEEKER
    # --------------------------------------------------------------------------
    @app.route("/seeker/find-rides", methods=["GET", "POST"])
    @user_login_required
    def seeker_find_rides():
        user_id = session["user_id"]
        locations = get_active_locations()
        available_rides = list_available_rides(user_id)
        matching_rides = None
        search_params = {}

        if request.method == "POST":
            search_params = {
                "pickup_location_id": request.form.get("pickup_location_id", ""),
                "destination_location_id": request.form.get("destination_location_id", ""),
                "ride_date": request.form.get("ride_date", ""),
                "ride_time": request.form.get("ride_time", ""),
                "seats_required": request.form.get("seats_required", "1"),
            }
            ok, err, results = search_matching_rides(
                user_id,
                search_params["pickup_location_id"],
                search_params["destination_location_id"],
                search_params["ride_date"],
                search_params["ride_time"],
                search_params["seats_required"],
            )
            if not ok:
                flash(err, "error")
            else:
                matching_rides = results
                if not results:
                    flash("No matching rides found for your route and ±30 min window. Try another time or date.", "warning")

        return render_template(
            "ride_seeker/find_rides.html",
            locations=locations,
            available_rides=available_rides,
            matching_rides=matching_rides,
            search_params=search_params,
        )

    @app.route("/rides/<int:ride_id>")
    @user_login_required
    def seeker_ride_details(ride_id):
        ride = get_ride_details(ride_id)
        if not ride:
            flash("Selected ride does not exist.", "error")
            return redirect(url_for("seeker_find_rides"))
        return render_template("ride_seeker/ride_details.html", ride=ride)

    @app.route("/seeker/request-ride/<int:ride_id>", methods=["POST"])
    @user_login_required
    def seeker_request_ride(ride_id):
        ok, msg = request_ride_service(
            session["user_id"],
            ride_id,
            request.form.get("seats_requested", ""),
            request.form.get("expected_price"),
        )
        flash(msg, "success" if ok else "error")
        if ok:
            return redirect(url_for("seeker_requests"))
        return redirect(url_for("seeker_ride_details", ride_id=ride_id))

    @app.route("/seeker/requests")
    @user_login_required
    def seeker_requests():
        requests_list = get_my_ride_requests(session["user_id"])
        return render_template("ride_seeker/ride_requests.html", requests_list=requests_list)

    @app.route("/seeker/bookings")
    @user_login_required
    def seeker_bookings():
        bookings = get_my_bookings(session["user_id"])
        return render_template("ride_seeker/bookings.html", bookings=bookings)

    @app.route("/seeker/bookings/<int:booking_id>/cancel", methods=["POST"])
    @user_login_required
    def seeker_cancel_booking(booking_id):
        ok, msg = cancel_booking_service(session["user_id"], booking_id)
        flash(msg, "success" if ok else "error")
        return redirect(url_for("seeker_bookings"))

    @app.route("/seeker/history")
    @user_login_required
    def seeker_history():
        bookings = get_my_bookings(session["user_id"])
        return render_template("ride_seeker/ride_history.html", bookings=bookings)

    @app.route("/seeker/driver/<int:booking_id>")
    @user_login_required
    def seeker_driver_details(booking_id):
        driver = get_driver_details_for_booking(session["user_id"], booking_id)
        if not driver:
            flash("Driver details are not available for this booking.", "error")
            return redirect(url_for("seeker_bookings"))
        return render_template("ride_seeker/driver_details.html", driver=driver)

    @app.route("/seeker/feedback", methods=["GET", "POST"])
    @user_login_required
    def seeker_feedback():
        user_id = session["user_id"]
        if request.method == "POST":
            ok, msg = submit_feedback_service(
                user_id,
                request.form.get("booking_id", ""),
                request.form.get("rating", ""),
                request.form.get("comment", ""),
            )
            flash(msg, "success" if ok else "error")
            if ok:
                return redirect(url_for("seeker_feedback"))

        eligible_bookings = get_eligible_feedback_bookings(user_id)
        return render_template("ride_seeker/feedback.html", eligible_bookings=eligible_bookings)

    # --------------------------------------------------------------------------
    # RIDE GIVER
    # --------------------------------------------------------------------------
    @app.route("/giver/dashboard")
    @user_login_required
    def giver_dashboard():
        user_id = session["user_id"]
        stats = get_user_dashboard_stats(user_id)
        posted_rides = get_my_posted_rides(user_id)
        incoming_requests = get_incoming_ride_requests(user_id)
        return render_template(
            "ride_giver/giver_dashboard.html",
            stats=stats,
            posted_rides=posted_rides,
            incoming_requests=incoming_requests,
        )

    @app.route("/giver/register-vehicle", methods=["GET", "POST"])
    @user_login_required
    def giver_register_vehicle():
        form_data = {}
        if request.method == "POST":
            form_data = {
                "vehicle_name": request.form.get("vehicle_name", ""),
                "registration_number": request.form.get("registration_number", ""),
                "seating_capacity": request.form.get("seating_capacity", ""),
            }
            ok, msg = register_vehicle_service(
                session["user_id"],
                form_data["vehicle_name"],
                form_data["registration_number"],
                form_data["seating_capacity"],
            )
            flash(msg, "success" if ok else "error")
            if ok:
                return redirect(url_for("giver_vehicles"))

        return render_template("ride_giver/register_vehicle.html", form_data=form_data)

    @app.route("/giver/vehicles")
    @user_login_required
    def giver_vehicles():
        vehicles = get_user_vehicles(session["user_id"])
        return render_template("ride_giver/my_vehicles.html", vehicles=vehicles)

    @app.route("/giver/vehicles/<int:vehicle_id>/remove", methods=["POST"])
    @user_login_required
    def giver_remove_vehicle(vehicle_id):
        ok, msg = remove_vehicle_service(session["user_id"], vehicle_id)
        flash(msg, "success" if ok else "error")
        return redirect(url_for("giver_vehicles"))

    @app.route("/giver/offer-ride", methods=["GET", "POST"])
    @user_login_required
    def giver_offer_ride():
        user_id = session["user_id"]
        vehicles = [v for v in get_user_vehicles(user_id) if v["vehicle_status"] == "ACTIVE"]
        locations = get_active_locations()
        form_data = {}

        if request.method == "POST":
            form_data = dict(request.form)
            new_pickup = {
                "city": request.form.get("pickup_city", ""),
                "region": request.form.get("pickup_region", ""),
                "area": request.form.get("pickup_area", ""),
                "point_name": request.form.get("pickup_point_name", ""),
            }
            new_dest = {
                "city": request.form.get("dest_city", ""),
                "region": request.form.get("dest_region", ""),
                "area": request.form.get("dest_area", ""),
                "point_name": request.form.get("dest_point_name", ""),
            }
            ok, msg = post_ride_service(
                user_id,
                request.form.get("vehicle_id", ""),
                request.form.get("pickup_choice", ""),
                new_pickup,
                request.form.get("dest_choice", ""),
                new_dest,
                request.form.get("ride_date", ""),
                request.form.get("ride_time", ""),
                request.form.get("available_seats", ""),
                request.form.get("price_per_seat", ""),
            )
            flash(msg, "success" if ok else "error")
            if ok:
                return redirect(url_for("giver_rides"))

        return render_template(
            "ride_giver/offer_ride.html",
            vehicles=vehicles,
            locations=locations,
            form_data=form_data,
        )

    @app.route("/giver/rides")
    @user_login_required
    def giver_rides():
        rides = get_my_posted_rides(session["user_id"])
        return render_template("ride_giver/my_rides.html", rides=rides)

    @app.route("/giver/requests")
    @user_login_required
    def giver_requests():
        requests_list = get_incoming_ride_requests(session["user_id"])
        return render_template("ride_giver/manage_requests.html", requests_list=requests_list)

    @app.route("/giver/requests/<int:request_id>/<action>", methods=["POST"])
    @user_login_required
    def giver_respond_request(request_id, action):
        ok, msg = respond_to_ride_request_service(session["user_id"], request_id, action)
        flash(msg, "success" if ok else "error")
        return redirect(url_for("giver_requests"))

    @app.route("/giver/rides/<int:ride_id>/update", methods=["GET", "POST"])
    @user_login_required
    def giver_update_ride(ride_id):
        user_id = session["user_id"]
        if request.method == "POST":
            update_type = request.form.get("update_type", "")
            ok, msg = update_ride_service(user_id, ride_id, update_type, request.form)
            flash(msg, "success" if ok else "error")
            if ok:
                return redirect(url_for("giver_update_ride", ride_id=ride_id))

        ride = get_updatable_ride(user_id, ride_id)
        if not ride:
            flash("This ride is not eligible for updating or does not belong to you.", "error")
            return redirect(url_for("giver_rides"))

        locations = get_active_locations()
        return render_template("ride_giver/update_ride.html", ride=ride, locations=locations)

    @app.route("/giver/history")
    @user_login_required
    def giver_history():
        rides = get_giver_ride_history(session["user_id"])
        return render_template("ride_giver/ride_history.html", rides=rides)

    @app.route("/giver/feedback")
    @user_login_required
    def giver_feedback():
        feedbacks = get_received_feedback(session["user_id"])
        return render_template("ride_giver/received_feedback.html", feedbacks=feedbacks)

    # --------------------------------------------------------------------------
    # ADMIN PORTAL
    # --------------------------------------------------------------------------
    @app.route("/admin/login", methods=["GET", "POST"])
    def admin_login():
        if session.get("admin_id") and session.get("role") == "admin":
            return redirect(url_for("admin_dashboard"))

        form_data = {}
        if request.method == "POST":
            admin_id_str = request.form.get("admin_id", "")
            form_data = {"admin_id": admin_id_str}
            ok, msg, admin_info = admin_login_service(
                request.form.get("portal_password", ""),
                admin_id_str,
                request.form.get("password", ""),
            )
            if ok:
                rotate_user_session(session)
                session["admin_id"] = admin_info["admin_id"]
                session["admin_name"] = admin_info["full_name"]
                session["role"] = "admin"
                flash(msg, "success")
                return redirect(url_for("admin_dashboard"))
            flash(msg, "error")

        return render_template("admin/admin_login.html", form_data=form_data)

    @app.route("/admin/register-portal", methods=["GET", "POST"])
    def admin_register_portal():
        if session.get("admin_id") and session.get("role") == "admin":
            return redirect(url_for("admin_dashboard"))

        form_data = {}
        registration_success = False
        if request.method == "POST":
            form_data = {
                "full_name": request.form.get("full_name", ""),
                "email": request.form.get("email", ""),
                "phone": request.form.get("phone", ""),
            }
            ok, msg = admin_portal_register_service(
                request.form.get("portal_password", ""),
                form_data["full_name"],
                form_data["email"],
                form_data["phone"],
                request.form.get("password", ""),
                request.form.get("confirm_password", ""),
            )
            if ok:
                flash(msg, "success")
                registration_success = True
                form_data = {}
            else:
                flash(msg, "error")

        return render_template(
            "admin/admin_register.html",
            form_data=form_data,
            registration_success=registration_success,
        )

    @app.route("/admin/logout", methods=["POST"])
    def admin_logout():
        admin_id = session.get("admin_id")
        if admin_id:
            admin_record_logout_audit(admin_id)
        rotate_user_session(session)
        flash("Admin logged out successfully.", "success")
        return redirect(url_for("admin_login"))

    @app.route("/admin/dashboard")
    @admin_login_required
    def admin_dashboard():
        stats = admin_get_dashboard_stats()
        return render_template("admin/admin_dashboard.html", stats=stats)

    @app.route("/admin/register", methods=["POST"])
    @admin_login_required
    def admin_register():
        ok, msg = admin_register_service(
            session["admin_id"],
            request.form.get("full_name", ""),
            request.form.get("email", ""),
            request.form.get("phone", ""),
            request.form.get("password", ""),
            request.form.get("confirm_password", ""),
        )
        flash(msg, "success" if ok else "error")
        return redirect(url_for("admin_dashboard"))

    @app.route("/admin/users")
    @admin_login_required
    def admin_users():
        users = admin_list_users()
        return render_template("admin/users.html", users=users)

    @app.route("/admin/users/<int:user_id>/status", methods=["POST"])
    @admin_login_required
    def admin_user_status(user_id):
        ok, msg = admin_update_user_status(
            session["admin_id"],
            user_id,
            request.form.get("account_status", ""),
        )
        flash(msg, "success" if ok else "error")
        return redirect(url_for("admin_users"))

    @app.route("/admin/vehicles")
    @admin_login_required
    def admin_vehicles():
        vehicles = admin_list_vehicles()
        return render_template("admin/vehicles.html", vehicles=vehicles)

    @app.route("/admin/vehicles/<int:vehicle_id>/status", methods=["POST"])
    @admin_login_required
    def admin_vehicle_status(vehicle_id):
        ok, msg = admin_update_vehicle_status(
            session["admin_id"],
            vehicle_id,
            request.form.get("vehicle_status", ""),
        )
        flash(msg, "success" if ok else "error")
        return redirect(url_for("admin_vehicles"))

    @app.route("/admin/reports")
    @admin_login_required
    def admin_reports():
        reports = admin_list_reports()
        return render_template("admin/reports.html", reports=reports)

    @app.route("/admin/reports/<int:report_id>/update", methods=["POST"])
    @admin_login_required
    def admin_report_update(report_id):
        ok, msg = admin_update_report(
            session["admin_id"],
            report_id,
            request.form.get("report_status", ""),
            request.form.get("admin_action", ""),
        )
        flash(msg, "success" if ok else "error")
        return redirect(url_for("admin_reports"))

    @app.route("/admin/feedback")
    @admin_login_required
    def admin_feedback():
        feedbacks = admin_list_feedback()
        return render_template("admin/feedback.html", feedbacks=feedbacks)

    @app.route("/admin/ongoing-rides")
    @admin_login_required
    def admin_ongoing_rides():
        rides = admin_list_ongoing_rides()
        return render_template("admin/ongoing_rides.html", rides=rides)

    @app.route("/admin/audit-logs")
    @admin_login_required
    def admin_audit_logs():
        logs = admin_list_audit_logs()
        return render_template("admin/audit_logs.html", logs=logs)
