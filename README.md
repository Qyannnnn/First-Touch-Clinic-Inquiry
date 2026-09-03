# Nightingale — First-Touch Clinic Inquiry

Nightingale is a 48-hour Django prototype that connects a guest clinic inquiry into a secure PatientSession with risk-gated AI chat, Living Memory, provenance, and Send to Clinic escalation.

## Setup & Run

1. Clone the repository.
2. Create and activate a virtual environment.
3. Install dependencies:
   pip install -r requirements.txt
4. Copy .env.example to .env and add:
   GEMINI_API_KEY=your-key
   GEMINI_MODEL=gemini-3.5-flash-lite
   DJANGO_SECRET_KEY=your-secret
   DJANGO_DEBUG=True
5. Run:
   python manage.py migrate
   python manage.py setup_demo
   python manage.py runserver

Open:
http://127.0.0.1:8000/

Staff portal:
http://127.0.0.1:8000/staff/

Demo staff:
Username: demo_staff
Password: NightingaleDemo123!

## Automated Tests

Run:
python manage.py test core.tests

The test suite covers:
- Guest to Patient conversion
- Value events
- Escalation payload
- Risk escalation
- Living Memory mutation
- PHI redaction
- Access control
- Trust / AI identity response

Current result: 12 tests passing.

## PHI Redaction

Redaction is implemented in core/redaction.py.
Before text is sent to Gemini, supported identifiers are removed or anonymized, including names, phone numbers, email addresses, Singapore NRIC/FIN-style IDs, and Malaysian IC-style IDs.

Microsoft Presidio is used together with deterministic regex rules. Risk processing and redaction are coordinated in core/services.py -> process_incoming_message().

Only synthetic demo data should be used.

## RBAC / Access Control

Server-side access control is implemented in core/views.py -> get_authorized_patient_session().
A patient can access only their own PatientSession. The check protects patient_chat, patient_send, and send_to_clinic.

Patients cannot access the staff admin area. Staff access is protected by Django Admin authentication.

## Main Flow

Acquisition -> LeadSession -> Guest conversation -> Value event -> Trust transition -> Consent -> PatientSession -> Risk-gated AI intake -> Living Memory -> Send to Clinic

## Risk Safety

Every health message is risk assessed before the AI response.
Mandatory HIGH-risk phrases include:
- crushing chest pain
- difficulty breathing
- heavy bleeding
- want to hurt myself

HIGH-risk messages receive urgent safety guidance and the interface always shows:
“If this is an emergency, exit Nightingale and dial 999 for Emergency Services.”

## Living Memory

After consent, Nightingale extracts structured facts such as chief complaint, symptoms, timeline, medications, and allergies.
Each memory item stores value, status, provenance pointer, and updated timestamp. Previous states are preserved as superseded rather than deleted.

## Send to Clinic

For Medium, High, or Ambiguous PatientSession concerns, the user can choose “Send to Clinic”.
The escalation stores the triggering message, triage summary, profile snapshot, provenance, acquisition context, and status.
The patient receives a confirmation with an expected response time of approximately 12–18 hours.

## Tech Stack

Python 3.12, Django 5.2, SQLite, Google Gemini, Microsoft Presidio, Pydantic, HTML, CSS, JavaScript.

## Prototype Limitations

This is a 48-hour candidate prototype. Production deployment would still require full verified authentication such as OTP/MFA, production-grade encryption at rest, hardened staff visibility controls, formal retention/deletion policies, production monitoring, and live Meta/TikTok integrations.

The prototype is non-diagnostic and must not be treated as a replacement for licensed clinical care or emergency services.
