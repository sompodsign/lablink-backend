"""Centralized email templates for all transactional emails.

Each template is a tuple of (subject_template, body_template) using str.format()
with context variables. Templates are grouped by category.
"""

# ── Auth & Account ──────────────────────────────────────────────────

WELCOME_PATIENT = (
    "Welcome to {center_name} — LabLink",
    (
        "Hi {patient_name},\n\n"
        "Welcome! Your account at {center_name} has been created successfully.\n\n"
        "You can now:\n"
        "  • Book appointments online\n"
        "  • View your lab reports\n"
        "  • Track your medical history\n\n"
        "Log in here: {login_url}\n\n"
        "— {center_name} Team"
    ),
)

PASSWORD_RESET = (
    "Password Reset — LabLink",
    (
        "Hi {user_name},\n\n"
        "Click the link below to reset your password:\n"
        "{reset_url}\n\n"
        "This link expires after one use.\n\n"
        "If you did not request this, ignore this email."
    ),
)

PASSWORD_RESET_SUCCESS = (
    "Password Changed — LabLink",
    (
        "Hi {user_name},\n\n"
        "Your password has been changed successfully.\n\n"
        "If you did not make this change, please reset your password "
        "immediately or contact support."
    ),
)

ACCOUNT_APPROVED = (
    "Account Approved — {center_name}",
    (
        "Hi {patient_name},\n\n"
        "Your account at {center_name} has been approved.\n\n"
        "You can now log in and start using our services:\n"
        "{login_url}\n\n"
        "— {center_name} Team"
    ),
)

ACCOUNT_DECLINED = (
    "Account Update — {center_name}",
    (
        "Hi {patient_name},\n\n"
        "Unfortunately, your account request at {center_name} "
        "has been declined.\n\n"
        "If you believe this is an error, please contact the center directly.\n\n"
        "— {center_name} Team"
    ),
)


# ── Appointments ────────────────────────────────────────────────────

APPOINTMENT_BOOKED = (
    "Appointment Booked — {center_name}",
    (
        "Hi {patient_name},\n\n"
        "Your appointment has been booked at {center_name}.\n\n"
        "Details:\n"
        "  • Date: {date}\n"
        "  • Time: {time}\n"
        "  • Doctor: {doctor_name}\n"
        "  • Status: Pending confirmation\n\n"
        "You will receive a confirmation once the center confirms your booking.\n\n"
        "— {center_name} Team"
    ),
)

APPOINTMENT_CONFIRMED = (
    "Appointment Confirmed — {center_name}",
    (
        "Hi {patient_name},\n\n"
        "Your appointment at {center_name} has been confirmed.\n\n"
        "Details:\n"
        "  • Date: {date}\n"
        "  • Time: {time}\n"
        "  • Doctor: {doctor_name}\n\n"
        "Please arrive 10 minutes before your scheduled time.\n\n"
        "— {center_name} Team"
    ),
)

APPOINTMENT_CANCELLED = (
    "Appointment Cancelled — {center_name}",
    (
        "Hi {patient_name},\n\n"
        "Your appointment at {center_name} has been cancelled.\n\n"
        "Details:\n"
        "  • Date: {date}\n"
        "  • Time: {time}\n\n"
        "If you need to reschedule, please contact the center or "
        "book a new appointment online.\n\n"
        "— {center_name} Team"
    ),
)


# ── Reports ─────────────────────────────────────────────────────────

REPORT_READY = (
    "Your Lab Report is Ready — {center_name}",
    (
        "Dear {patient_name},\n\n"
        "Your lab report for {test_name} is ready.\n\n"
        "You can view your report online at:\n"
        "{report_url}\n\n"
        "Report Details:\n"
        "  • Test: {test_name}\n"
        "  • Date: {report_date}\n"
        "  • Center: {center_name}\n\n"
        "This is an automated message from {center_name}.\n"
        "Please contact us if you have any questions."
    ),
)


# ── Staff & Doctor Credentials ──────────────────────────────────────

STAFF_CREDENTIALS = (
    "Welcome to {center_name} — Your Account Credentials",
    (
        "Hi {first_name},\n\n"
        "You have been added as a {role_name} at {center_name}.\n\n"
        "Your login credentials:\n"
        "  Username: {username}\n"
        "  Password: {password}\n\n"
        "Please change your password after first login.\n\n"
        "— {center_name} Team"
    ),
)

DOCTOR_CREDENTIALS = (
    "Welcome to {center_name} — Your Account Credentials",
    (
        "Hi Dr. {first_name},\n\n"
        "You have been added as a doctor at {center_name}.\n\n"
        "Your login credentials:\n"
        "  Username: {username}\n"
        "  Password: {password}\n\n"
        "Please change your password after first login.\n\n"
        "— {center_name} Team"
    ),
)


# ── Subscriptions & Billing ─────────────────────────────────────────

TRIAL_EXPIRY_WARNING = (
    "Trial Expiring Soon — {center_name}",
    (
        "Dear Admin,\n\n"
        "The trial period for {center_name} will expire in "
        "{days_left} day(s).\n\n"
        "To continue using LabLink without interruption, please "
        "subscribe to a plan.\n\n"
        "— LabLink Team"
    ),
)

TRIAL_EXPIRED = (
    "Trial Expired — {center_name}",
    (
        "Dear Admin,\n\n"
        "The trial period for {center_name} has expired.\n\n"
        "Your center data is safe, but some features may be "
        "restricted until you subscribe to a plan.\n\n"
        "Please contact LabLink support to activate your subscription.\n\n"
        "— LabLink Team"
    ),
)

INVOICE_GENERATED = (
    "New Invoice — {center_name}",
    (
        "Dear Admin,\n\n"
        "A new invoice has been generated for {center_name}.\n\n"
        "Invoice Details:\n"
        "  • Amount: ৳{amount}\n"
        "  • Due Date: {due_date}\n\n"
        "Please ensure timely payment to avoid service interruption.\n\n"
        "— LabLink Team"
    ),
)

INVOICE_OVERDUE = (
    "Invoice Overdue — {center_name}",
    (
        "Dear Admin,\n\n"
        "Your invoice for {center_name} is now overdue.\n\n"
        "Invoice Details:\n"
        "  • Amount: ৳{amount}\n"
        "  • Due Date: {due_date}\n\n"
        "Please make the payment as soon as possible to avoid "
        "service restrictions.\n\n"
        "— LabLink Team"
    ),
)

PAYMENT_RECEIVED = (
    "Payment Confirmed — {center_name}",
    (
        "Dear Admin,\n\n"
        "Payment has been received for {center_name}.\n\n"
        "Details:\n"
        "  • Amount: ৳{amount}\n"
        "  • Plan: {plan_name}\n\n"
        "Thank you for your continued subscription.\n\n"
        "— LabLink Team"
    ),
)


# ── Admin Operations ────────────────────────────────────────────────

CENTER_CREATED = (
    "Welcome to LabLink — {center_name}",
    (
        "Congratulations!\n\n"
        "{center_name} has been registered on the LabLink platform.\n\n"
        "You can now set up your center, add staff and doctors, "
        "and start managing patients.\n\n"
        "— LabLink Team"
    ),
)

CENTER_DEACTIVATED = (
    "Center Deactivated — {center_name}",
    (
        "Dear Admin,\n\n"
        "{center_name} has been deactivated on the LabLink platform.\n\n"
        "If you believe this is an error, please contact LabLink support.\n\n"
        "— LabLink Team"
    ),
)


# ── Template registry ──────────────────────────────────────────────

TEMPLATES: dict[str, tuple[str, str]] = {
    "welcome_patient": WELCOME_PATIENT,
    "password_reset": PASSWORD_RESET,
    "password_reset_success": PASSWORD_RESET_SUCCESS,
    "account_approved": ACCOUNT_APPROVED,
    "account_declined": ACCOUNT_DECLINED,
    "appointment_booked": APPOINTMENT_BOOKED,
    "appointment_confirmed": APPOINTMENT_CONFIRMED,
    "appointment_cancelled": APPOINTMENT_CANCELLED,
    "report_ready": REPORT_READY,
    "staff_credentials": STAFF_CREDENTIALS,
    "doctor_credentials": DOCTOR_CREDENTIALS,
    "trial_expiry_warning": TRIAL_EXPIRY_WARNING,
    "trial_expired": TRIAL_EXPIRED,
    "invoice_generated": INVOICE_GENERATED,
    "invoice_overdue": INVOICE_OVERDUE,
    "payment_received": PAYMENT_RECEIVED,
    "center_created": CENTER_CREATED,
    "center_deactivated": CENTER_DEACTIVATED,
}
