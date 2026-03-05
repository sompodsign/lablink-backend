# LabLink Backend — API Reference for Frontend Development

> **Base URL**: `http://<subdomain>.localhost:8200` (dev) or `https://<subdomain>.lablink.com.bd` (prod)
>
> **OpenAPI spec**: `GET /api/schema/` • **Swagger UI**: `/swagger/` • **ReDoc**: `/redoc/`

---

## 1. Multi-Tenancy

Every request is **scoped to a diagnostic center** based on the subdomain. The backend middleware extracts the subdomain from the `Host` header and attaches `request.tenant` (a `DiagnosticCenter` instance). All queries are filtered by this tenant automatically.

- `popularhospital.lablink.com.bd` → data for "Popular Hospital"
- `demo.localhost:8200` → demo center (local dev)

**Cross-tenant data access is impossible by design.** The frontend does NOT need to pass a center ID — the subdomain handles it.

---

## 2. Authentication (JWT)

All endpoints except **Tenant Info** and **User Registration** require JWT Bearer authentication.

### 2.1 Obtain Token

```
POST /api/token/
Content-Type: application/json
```

**Request:**

```json
{
  "username": "admin",
  "password": "password123"
}
```

**Response (200):**

```json
{
  "access": "eyJ0eXAiOiJKV1QiLCJhbGciOiJI...",
  "refresh": "eyJ0eXAiOiJKV1QiLCJhbGciOiJI..."
}
```

**Token lifetimes:**

- **Access token**: 90 days
- **Refresh token**: 180 days

### 2.2 Refresh Token

```
POST /api/token/refresh/
Content-Type: application/json
```

**Request:**

```json
{
  "refresh": "eyJ0eXAiOiJKV1QiLCJhbGciOiJI..."
}
```

**Response (200):**

```json
{
  "access": "eyJ0eXAiOiJKV1QiLCJhbGciOiJI..."
}
```

### 2.3 Using the Token

Add to every authenticated request:

```
Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJI...
```

### 2.4 Error Responses

**401 Unauthorized** (missing or invalid token):

```json
{
  "detail": "Authentication credentials were not provided."
}
```

**401 Token expired:**

```json
{
  "detail": "Given token not valid for any token type",
  "code": "token_not_valid",
  "messages": [
    {
      "token_class": "AccessToken",
      "token_type": "access",
      "message": "Token is invalid or expired"
    }
  ]
}
```

---

## 3. Roles & Permissions

Users have different roles that control what endpoints they can access:

| Role               | How it's determined                           | Access scope                                     |
| ------------------ | --------------------------------------------- | ------------------------------------------------ |
| **Admin**          | `user.staff_profile.role == "ADMIN"`          | Full center access                               |
| **Receptionist**   | `user.staff_profile.role == "RECEPTIONIST"`   | Patient registration, appointments, payments     |
| **Lab Technician** | `user.staff_profile.role == "LAB_TECHNICIAN"` | Test orders, report creation                     |
| **Doctor**         | `user.doctor_profile` exists                  | Own appointments, prescribe tests, consultations |
| **Patient**        | No staff/doctor profile                       | View own appointments and reports only           |

**403 Forbidden** (wrong role):

```json
{
  "detail": "You do not have permission to perform this action."
}
```

---

## 4. Pagination

All list endpoints use **page-based pagination** with 20 items per page.

**Query parameter:** `?page=2`

**Response format:**

```json
{
    "count": 45,
    "next": "http://demo.localhost:8200/api/appointments/appointments/?page=3",
    "previous": "http://demo.localhost:8200/api/appointments/appointments/?page=1",
    "results": [ ... ]
}
```

---

## 5. Validation Errors

When request data fails validation, the API returns **400 Bad Request**:

```json
{
  "field_name": ["Error message 1.", "Error message 2."],
  "non_field_errors": ["General error not tied to a specific field."]
}
```

Example:

```json
{
  "appointment": ["Appointment does not belong to this center."],
  "test_type": ["This test type is not available at this center."]
}
```

---

## 6. Endpoints

### 6.1 Tenant — Public Center Info

#### `GET /api/tenants/current/`

**Auth:** ❌ None required
**Role:** Anyone
**Description:** Returns branding, configuration, and services for the center matching the current subdomain. Use this to dynamically render the landing page, logos, colors, etc.

**Response (200):**

```json
{
  "id": 1,
  "name": "Popular Hospital Diagnostics",
  "domain": "popularhospital",
  "tagline": "Your trusted diagnostic partner",
  "address": "12/A Dhanmondi, Dhaka-1205",
  "contact_number": "01700000000",
  "email": "info@popularhospital.com",
  "logo_url": "http://demo.localhost:8200/media/center_logos/logo.png",
  "primary_color": "#0d9488",
  "opening_hours": "8:00 AM - 10:00 PM",
  "years_of_experience": "15+",
  "happy_patients_count": "50,000+",
  "test_types_available_count": "100+",
  "lab_support_availability": "24/7",
  "services": [
    {
      "id": 1,
      "title": "Blood Testing",
      "description": "Complete blood count, lipid profile, and more",
      "icon": "🩸",
      "order": 1
    },
    {
      "id": 2,
      "title": "X-Ray",
      "description": "Digital X-ray with fast results",
      "icon": "📷",
      "order": 2
    }
  ]
}
```

**Response (404):** No center found for this subdomain.

```json
{
  "error": "No diagnostic center found for this domain"
}
```

---

### 6.2 Authentication — User Registration & Profile

#### `POST /api/auth/register/`

**Auth:** ❌ None required
**Description:** Creates a generic user account. This does NOT create a patient, doctor, or staff member. Use `/api/auth/patients/` for patient registration.

**Request:**

```json
{
  "username": "johndoe",
  "email": "john@example.com",
  "password": "securepass123",
  "first_name": "John",
  "last_name": "Doe",
  "phone_number": "01712345678"
}
```

**Required fields:** `username`, `password`
**Optional fields:** `email`, `first_name`, `last_name`, `phone_number`

**Response (201):**

```json
{
  "id": 5,
  "username": "johndoe",
  "email": "john@example.com",
  "first_name": "John",
  "last_name": "Doe",
  "phone_number": "01712345678"
}
```

#### `GET /api/auth/profile/`

**Auth:** ✅ JWT
**Description:** Get current logged-in user's profile.

**Response (200):**

```json
{
  "id": 5,
  "username": "johndoe",
  "email": "john@example.com",
  "first_name": "John",
  "last_name": "Doe",
  "phone_number": "01712345678"
}
```

#### `PUT /api/auth/profile/`

**Auth:** ✅ JWT
**Description:** Full update of current user's profile.

#### `PATCH /api/auth/profile/`

**Auth:** ✅ JWT
**Description:** Partial update of current user's profile. Send only the fields to change.

**Request:**

```json
{
  "phone_number": "01800000001"
}
```

---

### 6.3 Patients — Walk-in Registration & Management

#### `GET /api/auth/patients/`

**Auth:** ✅ JWT
**Role:** Staff or Doctor
**Description:** List all patients registered at or with appointments at the current center. Ordered by first name, then last name.

**Response (200):**

```json
{
  "count": 2,
  "next": null,
  "previous": null,
  "results": [
    {
      "id": 10,
      "username": "01700000099",
      "email": "",
      "first_name": "Fatima",
      "last_name": "Khan",
      "full_name": "Fatima Khan",
      "phone_number": "01700000099",
      "patient_profile": {
        "id": 1,
        "phone_number": "01700000099",
        "date_of_birth": "1990-05-15",
        "blood_group": "B+",
        "address": "12/A Dhanmondi, Dhaka",
        "medical_history": "",
        "emergency_contact_name": "Karim Khan",
        "emergency_contact_phone": "01800000088",
        "registered_at_center": 1,
        "created_at": "2026-03-05T10:30:00Z",
        "updated_at": "2026-03-05T10:30:00Z"
      }
    }
  ]
}
```

#### `POST /api/auth/patients/`

**Auth:** ✅ JWT
**Role:** Staff only
**Description:** Register a walk-in patient. Creates a `User` (without login credentials — password is `null`) and a `PatientProfile` linked to the current center. The `username` is auto-generated from `phone_number` or `first_name.last_name`.

**Request (full):**

```json
{
  "first_name": "Fatima",
  "last_name": "Khan",
  "phone_number": "01700000099",
  "email": "fatima@example.com",
  "date_of_birth": "1990-05-15",
  "blood_group": "B+",
  "address": "12/A Dhanmondi, Dhaka",
  "medical_history": "No known allergies",
  "emergency_contact_name": "Karim Khan",
  "emergency_contact_phone": "01800000088"
}
```

**Required fields:** `first_name`, `last_name`
**Optional fields:** `phone_number`, `email`, `date_of_birth`, `blood_group`, `address`, `medical_history`, `emergency_contact_name`, `emergency_contact_phone`

**`blood_group` enum values:** `A+`, `A-`, `B+`, `B-`, `AB+`, `AB-`, `O+`, `O-`

**Request (minimal):**

```json
{
  "first_name": "Rahim",
  "last_name": "Uddin"
}
```

**Response (201):** Same as the Patient object in list response (User + patient_profile).

**Side effects:**

- Auto-generates `username` from phone or name
- Creates `PatientProfile` linked to the current center
- User has NO password (cannot log in until upgraded)

#### `GET /api/auth/patients/{id}/`

**Auth:** ✅ JWT
**Role:** Staff or Doctor
**Response:** Same structure as single item in list.

#### `PATCH /api/auth/patients/{id}/`

**Auth:** ✅ JWT
**Role:** Staff only
**Description:** Update patient profile (name, phone, medical history, etc.).

---

### 6.4 Doctors — Management & Activity

#### `GET /api/tenants/doctors/`

**Auth:** ✅ JWT
**Role:** Staff
**Description:** List all doctors associated with the current center.

**Response (200):**

```json
{
  "count": 2,
  "next": null,
  "previous": null,
  "results": [
    {
      "id": 1,
      "name": "Dr. Rina Akter",
      "email": "rina@example.com",
      "username": "dr.rina",
      "specialization": "Cardiology",
      "designation": "Senior Consultant",
      "bio": "15 years of experience in cardiology..."
    }
  ]
}
```

#### `GET /api/tenants/doctors/{id}/`

**Auth:** ✅ JWT
**Role:** Staff
**Response:** Single doctor object.

#### `POST /api/tenants/doctors/{id}/add-to-center/`

**Auth:** ✅ JWT
**Role:** Admin only
**Description:** Add an existing doctor (by ID) to the current center. This creates the M2M relationship — it does NOT create a new doctor record.
**Request body:** None required.

**Response (200):** Doctor object.

**Error (403):**

```json
{
  "detail": "Only admins can add doctors to the center."
}
```

#### `POST /api/tenants/doctors/{id}/remove-from-center/`

**Auth:** ✅ JWT
**Role:** Admin only
**Description:** Remove a doctor from the current center. This only removes the M2M relationship — the doctor record is NOT deleted.
**Request body:** None required.

**Response:** `204 No Content`

#### `GET /api/tenants/doctors/{id}/activity/`

**Auth:** ✅ JWT
**Role:** Staff
**Description:** Returns a summary of the doctor's recent activity at the current center — total appointments, total test orders prescribed, and last 10 consultations.

**Response (200):**

```json
{
  "doctor": {
    "id": 1,
    "name": "Dr. Rina Akter",
    "email": "rina@example.com",
    "specialization": "Cardiology",
    "designation": "Senior Consultant",
    "bio": ""
  },
  "total_appointments": 42,
  "total_test_orders": 87,
  "recent_appointments": [
    {
      "id": 101,
      "patient": "Karim Ahmed",
      "date": "2026-03-05",
      "status": "COMPLETED"
    },
    {
      "id": 98,
      "patient": "Fatima Khan",
      "date": "2026-03-04",
      "status": "COMPLETED"
    }
  ]
}
```

---

### 6.5 Staff — Listing

#### `GET /api/tenants/staff/`

**Auth:** ✅ JWT
**Role:** Admin only
**Description:** List all staff members at the current center.

**Response (200):**

```json
{
  "count": 3,
  "next": null,
  "previous": null,
  "results": [
    {
      "id": 1,
      "name": "Aminul Islam",
      "email": "aminul@example.com",
      "role": "ADMIN",
      "role_display": "Admin"
    },
    {
      "id": 2,
      "name": "Reshma Begum",
      "email": "reshma@example.com",
      "role": "RECEPTIONIST",
      "role_display": "Receptionist"
    },
    {
      "id": 3,
      "name": "Nasir Uddin",
      "email": "nasir@example.com",
      "role": "LAB_TECHNICIAN",
      "role_display": "Lab Technician"
    }
  ]
}
```

**`role` enum:** `ADMIN`, `RECEPTIONIST`, `LAB_TECHNICIAN`

#### `GET /api/tenants/staff/{id}/`

**Auth:** ✅ JWT
**Role:** Admin only

---

### 6.6 Appointments — Scheduling & Consultations

#### `GET /api/appointments/appointments/`

**Auth:** ✅ JWT
**Role:** Any authenticated user (role-filtered queryset)
**Description:**

- **Doctors** see only their own appointments
- **Staff** see all appointments at the center
- **Patients** see only their own appointments

**Response (200):**

```json
{
  "count": 1,
  "next": null,
  "previous": null,
  "results": [
    {
      "id": 1,
      "patient": 10,
      "patient_name": "Fatima Khan",
      "center": 1,
      "doctor": 1,
      "doctor_name": "Dr. Rina Akter",
      "date": "2026-03-10",
      "time": "10:30:00",
      "status": "PENDING",
      "symptoms": "Persistent headache for 3 days",
      "created_at": "2026-03-05T08:00:00Z"
    }
  ]
}
```

**`status` enum:** `PENDING`, `CONFIRMED`, `COMPLETED`, `CANCELLED`

#### `POST /api/appointments/appointments/`

**Auth:** ✅ JWT
**Role:** Staff or Doctor

**Request:**

```json
{
  "patient": 10,
  "center": 1,
  "doctor": 1,
  "date": "2026-03-10",
  "time": "10:30",
  "symptoms": "Persistent headache for 3 days"
}
```

**Required fields:** `patient` (user ID), `center` (center ID), `doctor` (doctor ID), `date`, `time`
**Optional fields:** `symptoms`, `status` (defaults to `"PENDING"`)

**Response (201):** Appointment object.

> **Note:** `patient` is a User ID. `doctor` is a Doctor ID (not User ID). `center` should match the current tenant ID.

#### `GET /api/appointments/appointments/{id}/`

**Auth:** ✅ JWT

#### `PATCH /api/appointments/appointments/{id}/`

**Auth:** ✅ JWT
**Role:** Staff only
**Description:** Update appointment status, date, time, or reassign doctor.

**Request:**

```json
{
  "status": "CONFIRMED",
  "date": "2026-03-12"
}
```

#### `DELETE /api/appointments/appointments/{id}/`

**Auth:** ✅ JWT
**Role:** Staff only
**Response:** `204 No Content`

#### `GET /api/appointments/appointments/today/`

**Auth:** ✅ JWT
**Role:** Doctor only
**Description:** Returns today's appointments for the logged-in doctor, ordered by time. Useful for the daily consultation dashboard.

**Response (200):** Array of Appointment objects (same structure as list, but **not paginated** — returns raw array):

```json
[
  {
    "id": 1,
    "patient": 10,
    "patient_name": "Fatima Khan",
    "center": 1,
    "doctor": 1,
    "doctor_name": "Dr. Rina Akter",
    "date": "2026-03-05",
    "time": "09:00:00",
    "status": "PENDING",
    "symptoms": "Fever",
    "created_at": "2026-03-04T18:00:00Z"
  }
]
```

#### `PATCH /api/appointments/appointments/{id}/consult/`

**Auth:** ✅ JWT
**Role:** Doctor only
**Description:** Doctor updates an appointment with clinical notes, symptoms, or changes the status.

**Request:**

```json
{
  "symptoms": "Fever for 3 days, body ache, loss of appetite.",
  "status": "COMPLETED"
}
```

**Optional fields:** `symptoms` (string), `status` (enum)

**Response (200):** Full Appointment object.

---

### 6.7 Test Types & Center Pricing — Diagnostics Catalog

#### `GET /api/diagnostics/test-types/`

**Auth:** Optional (public read)
**Description:** List all available diagnostic test types (global, not center-specific).

**Response (200):**

```json
{
  "count": 5,
  "next": null,
  "previous": null,
  "results": [
    {
      "id": 1,
      "name": "Complete Blood Count (CBC)",
      "description": "Measures red blood cells, white blood cells, hemoglobin, hematocrit, and platelets.",
      "base_price": "500.00"
    },
    {
      "id": 2,
      "name": "Lipid Profile",
      "description": "Total cholesterol, HDL, LDL, and triglycerides.",
      "base_price": "800.00"
    }
  ]
}
```

#### `POST /api/diagnostics/test-types/`

**Auth:** ✅ JWT

**Request:**

```json
{
  "name": "HbA1c",
  "description": "Glycated hemoglobin test for diabetes monitoring.",
  "base_price": "600.00"
}
```

#### `GET/PUT/PATCH/DELETE /api/diagnostics/test-types/{id}/`

Standard CRUD. Auth required for write operations.

---

#### `GET /api/diagnostics/pricing/`

**Auth:** Optional (public read)
**Description:** List test types with center-specific pricing. Only shows tests available at the current center.

**Response (200):**

```json
{
  "count": 3,
  "next": null,
  "previous": null,
  "results": [
    {
      "id": 1,
      "center": 1,
      "test_type": 1,
      "price": "550.00",
      "is_available": true,
      "test_type_details": {
        "id": 1,
        "name": "Complete Blood Count (CBC)",
        "description": "Measures red blood cells, white blood cells...",
        "base_price": "500.00"
      }
    }
  ]
}
```

#### `POST /api/diagnostics/pricing/`

**Auth:** ✅ JWT

**Request:**

```json
{
  "center": 1,
  "test_type": 1,
  "price": "550.00",
  "is_available": true
}
```

#### `GET/PUT/PATCH/DELETE /api/diagnostics/pricing/{id}/`

Standard CRUD. Auth required for write operations.

---

### 6.8 Test Orders — Lab Test Prescriptions

#### `GET /api/diagnostics/test-orders/`

**Auth:** ✅ JWT
**Role:** Staff or Doctor
**Description:** List test orders for the current center. Supports status filtering.

**Query parameter:** `?status=PENDING` (values: `PENDING`, `IN_PROGRESS`, `COMPLETED`, `CANCELLED`)

**Response (200):**

```json
{
  "count": 1,
  "next": null,
  "previous": null,
  "results": [
    {
      "id": 1,
      "appointment": 1,
      "center": 1,
      "test_type": 3,
      "test_type_name": "Complete Blood Count (CBC)",
      "ordered_by": 5,
      "ordered_by_name": "Dr. Rina Akter",
      "patient_name": "Fatima Khan",
      "status": "PENDING",
      "priority": "URGENT",
      "clinical_notes": "Patient reports persistent fatigue and dizziness for 2 weeks.",
      "created_at": "2026-03-05T11:00:00Z",
      "updated_at": "2026-03-05T11:00:00Z"
    }
  ]
}
```

**`status` enum:** `PENDING` → `IN_PROGRESS` → `COMPLETED` | `CANCELLED`
**`priority` enum:** `NORMAL`, `URGENT`

#### `POST /api/diagnostics/test-orders/`

**Auth:** ✅ JWT
**Role:** Doctor only
**Description:** Doctor prescribes a lab test for a patient's appointment. The test type must be available at the current center (must have a `CenterTestPricing` entry with `is_available=true`). The center and ordering doctor are set automatically from the request.

**Request:**

```json
{
  "appointment": 1,
  "test_type": 3,
  "priority": "URGENT",
  "clinical_notes": "Patient reports persistent fatigue and dizziness for 2 weeks."
}
```

**Required fields:** `appointment` (ID), `test_type` (ID)
**Optional fields:** `priority` (defaults to `"NORMAL"`), `clinical_notes`

**Auto-populated fields:** `center` (from tenant), `ordered_by` (from authenticated user)

**Response (201):** TestOrder object.

**Validation errors:**

```json
{
  "appointment": ["Appointment does not belong to this center."],
  "test_type": ["This test type is not available at this center."]
}
```

**Side effects:** Sends SMS notification to the patient (async via Celery).

#### `GET /api/diagnostics/test-orders/{id}/`

**Auth:** ✅ JWT
**Role:** Staff or Doctor

#### `PATCH /api/diagnostics/test-orders/{id}/`

**Auth:** ✅ JWT
**Role:** Staff or Doctor (different serializers depending on role)

**If Lab Technician/Staff** — can only update status:

```json
{
  "status": "IN_PROGRESS"
}
```

**If Doctor** — can update all fields (appointment, test_type, priority, clinical_notes, status).

**Response (200):** TestOrder object.

#### `DELETE /api/diagnostics/test-orders/{id}/`

**Auth:** ✅ JWT
**Role:** Doctor only
**Response:** `204 No Content`

---

### 6.9 Reports — Lab Results

#### `GET /api/diagnostics/reports/`

**Auth:** ✅ JWT
**Role:** Any authenticated (role-filtered queryset)
**Description:**

- **Staff/Doctor** see all reports at the center
- **Patient** sees only their own reports

**Response (200):**

```json
{
  "count": 1,
  "next": null,
  "previous": null,
  "results": [
    {
      "id": 1,
      "appointment": 1,
      "test_order": 1,
      "test_type": 3,
      "test_type_name": "Complete Blood Count (CBC)",
      "patient_name": "Fatima Khan",
      "file": "http://demo.localhost:8200/media/reports/cbc_fatima.pdf",
      "result_text": "Hemoglobin: 14.2 g/dL (Normal)\nWBC: 7,500/μL (Normal)\nPlatelets: 250,000/μL (Normal)",
      "result_data": {
        "hemoglobin": {
          "value": 14.2,
          "unit": "g/dL",
          "ref_range": "12.0-17.5"
        },
        "wbc": { "value": 7500, "unit": "/μL", "ref_range": "4500-11000" },
        "platelets": {
          "value": 250000,
          "unit": "/μL",
          "ref_range": "150000-400000"
        }
      },
      "status": "VERIFIED",
      "status_display": "Verified",
      "verified_by": 2,
      "is_delivered_online": false,
      "created_at": "2026-03-05T12:00:00Z",
      "updated_at": "2026-03-05T12:30:00Z"
    }
  ]
}
```

**`status` enum:** `DRAFT` → `VERIFIED` → `DELIVERED`

**Important fields:**

- `result_text` — human-readable text result
- `result_data` — structured JSON (flexible schema, typically `{test_name: {value, unit, ref_range}}`)
- `file` — URL to uploaded PDF/image report (nullable)
- `verified_by` — User ID of the staff who verified (nullable if not yet verified)

#### `POST /api/diagnostics/reports/`

**Auth:** ✅ JWT
**Role:** Lab Technician only
**Description:** Create a lab report from a completed test order. The `test_order` must belong to the current center and not already have a report.

**Request:**

```json
{
  "test_order": 1,
  "result_text": "Hemoglobin: 14.2 g/dL (Normal)\nWBC: 7,500/μL (Normal)\nPlatelets: 250,000/μL (Normal)\nRBC: 4.8 million/μL (Normal)",
  "result_data": {
    "hemoglobin": { "value": 14.2, "unit": "g/dL", "ref_range": "12.0-17.5" },
    "wbc": { "value": 7500, "unit": "/μL", "ref_range": "4500-11000" },
    "platelets": {
      "value": 250000,
      "unit": "/μL",
      "ref_range": "150000-400000"
    }
  }
}
```

**Required fields:** `test_order` (ID)
**Optional fields:** `result_text`, `result_data` (JSON), `file` (binary upload — use `multipart/form-data`)

**Auto-populated fields:** `appointment` (from test_order), `test_type` (from test_order), `status` (defaults to `"DRAFT"`)

**Response (201):** Full Report object.

**Side effects:**

- The test order status is automatically set to `COMPLETED`
- Sends SMS notification to patient when report is ready (async via Celery)

**Validation errors:**

```json
{
  "test_order": ["Test order does not belong to this center."]
}
```

```json
{
  "test_order": ["A report already exists for this test order."]
}
```

#### `GET /api/diagnostics/reports/{id}/`

**Auth:** ✅ JWT

#### `PATCH /api/diagnostics/reports/{id}/`

**Auth:** ✅ JWT
**Role:** Lab Technician only
**Description:** Update report result text, data, or upload file.

#### `POST /api/diagnostics/reports/{id}/verify/`

**Auth:** ✅ JWT
**Role:** Staff only
**Description:** Verify a draft report. Changes status from `DRAFT` to `VERIFIED`. The verifying user is recorded. A report can only be verified once.

**Request body:** None required.

**Response (200):** Full Report object with `status: "VERIFIED"` and `verified_by` populated.

**Error (400):**

```json
{
  "detail": "Report is already verified."
}
```

---

### 6.10 Payments — Recording & Tracking

#### `GET /api/payments/payments/`

**Auth:** ✅ JWT
**Role:** Staff only
**Description:** List all payments for appointments at the current center, ordered by most recent first.

**Response (200):**

```json
{
  "count": 1,
  "next": null,
  "previous": null,
  "results": [
    {
      "id": 1,
      "appointment": 1,
      "test_order": 3,
      "amount": "1500.00",
      "method": "CASH",
      "method_display": "Cash",
      "status": "COMPLETED",
      "status_display": "Completed",
      "transaction_id": "",
      "patient_name": "Fatima Khan",
      "test_type_name": "Complete Blood Count (CBC)",
      "created_at": "2026-03-05T14:00:00Z"
    }
  ]
}
```

**`method` enum:** `CASH`, `CARD`, `MOBILE_BANKING`, `ONLINE`
**`status` enum:** `PENDING`, `COMPLETED`, `FAILED`

#### `POST /api/payments/payments/`

**Auth:** ✅ JWT
**Role:** Staff only
**Description:** Record a payment for an appointment. Optionally link to a specific test order.

**Request (cash for full appointment):**

```json
{
  "appointment": 1,
  "amount": "1500.00",
  "method": "CASH",
  "status": "COMPLETED"
}
```

**Request (mobile banking for specific test):**

```json
{
  "appointment": 1,
  "test_order": 3,
  "amount": "800.00",
  "method": "MOBILE_BANKING",
  "transaction_id": "BKS20260305001",
  "status": "COMPLETED"
}
```

**Required fields:** `appointment` (ID), `amount`, `method`
**Optional fields:** `test_order` (ID), `transaction_id`, `status` (defaults to `"PENDING"`)

**Validation:** Both `appointment` and `test_order` (if provided) must belong to the current center.

**Response (201):** Payment object.

#### `GET /api/payments/payments/{id}/`

**Auth:** ✅ JWT
**Role:** Staff only

#### `PATCH /api/payments/payments/{id}/`

**Auth:** ✅ JWT
**Role:** Staff only
**Description:** Update payment status (e.g., mark pending payment as completed or failed).

```json
{
  "status": "COMPLETED"
}
```

---

## 7. Complete Enum Reference

| Enum                 | Values                                             | Used in        |
| -------------------- | -------------------------------------------------- | -------------- |
| `BloodGroup`         | `A+`, `A-`, `B+`, `B-`, `AB+`, `AB-`, `O+`, `O-`   | PatientProfile |
| `Staff.Role`         | `ADMIN`, `RECEPTIONIST`, `LAB_TECHNICIAN`          | Staff          |
| `TestOrder.Status`   | `PENDING`, `IN_PROGRESS`, `COMPLETED`, `CANCELLED` | TestOrder      |
| `TestOrder.Priority` | `NORMAL`, `URGENT`                                 | TestOrder      |
| `Report.Status`      | `DRAFT`, `VERIFIED`, `DELIVERED`                   | Report         |
| `Payment.Method`     | `CASH`, `CARD`, `MOBILE_BANKING`, `ONLINE`         | Payment        |
| `Payment.Status`     | `PENDING`, `COMPLETED`, `FAILED`                   | Payment        |
| `Appointment.Status` | `PENDING`, `CONFIRMED`, `COMPLETED`, `CANCELLED`   | Appointment    |

---

## 8. ID Reference — What IDs Mean

When sending requests, different `{id}` values refer to different models:

| Field         | Refers to               | Example            |
| ------------- | ----------------------- | ------------------ |
| `patient`     | User ID                 | `"patient": 10`    |
| `center`      | DiagnosticCenter ID     | `"center": 1`      |
| `doctor`      | Doctor ID (NOT User ID) | `"doctor": 2`      |
| `appointment` | Appointment ID          | `"appointment": 1` |
| `test_type`   | TestType ID             | `"test_type": 3`   |
| `test_order`  | TestOrder ID            | `"test_order": 1`  |
| `verified_by` | User ID (read-only)     | —                  |
| `ordered_by`  | User ID (read-only)     | —                  |

---

## 9. Workflow Sequences

### 9.1 Patient Visit Flow

```
1. Staff registers patient          → POST /api/auth/patients/
2. Staff creates appointment        → POST /api/appointments/appointments/
3. Doctor views today's schedule     → GET  /api/appointments/appointments/today/
4. Doctor adds consultation notes    → PATCH /api/appointments/appointments/{id}/consult/
5. Doctor prescribes tests           → POST /api/diagnostics/test-orders/
6. Lab tech starts processing        → PATCH /api/diagnostics/test-orders/{id}/  (status: IN_PROGRESS)
7. Lab tech creates report           → POST /api/diagnostics/reports/  (auto-sets order to COMPLETED)
8. Staff verifies report             → POST /api/diagnostics/reports/{id}/verify/
9. Staff records payment             → POST /api/payments/payments/
10. Patient views own reports        → GET  /api/diagnostics/reports/
```

### 9.2 Morning Setup (Doctor)

```
1. Get center info (branding)        → GET /api/tenants/current/
2. Login                             → POST /api/token/
3. View today's appointments         → GET /api/appointments/appointments/today/
4. View pending test orders          → GET /api/diagnostics/test-orders/?status=PENDING
```

### 9.3 Lab Technician Flow

```
1. View pending test orders          → GET /api/diagnostics/test-orders/?status=PENDING
2. Start processing                  → PATCH /api/diagnostics/test-orders/{id}/  → {"status": "IN_PROGRESS"}
3. Create report                     → POST /api/diagnostics/reports/
4. Upload report file (optional)     → PATCH /api/diagnostics/reports/{id}/  (multipart/form-data with file)
```
