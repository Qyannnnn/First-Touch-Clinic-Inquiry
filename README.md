# Nightingale 48HR — First Prototype

This is the **first vertical slice** for the candidate build. It deliberately proves the journey before connecting a real LLM:

`Acquisition Simulator → LeadSession → Guest Chat → Value Event → Trust Transition → Consent → PatientSession`

## What is implemented

- Django monolith structure (Python backend + server-rendered HTML/CSS)
- PostgreSQL-only configuration
- Acquisition simulator with channel attribution
- `LeadSession` persistence
- Guest chat with channel-aware opening
- `visitor`, `conversation_started`, `value_event`, `auth_started`, `consented`, `patient_created` funnel events
- Trust-transition UI
- Basic email/phone collection + consent
- Immutable UUID Patient IDs
- LeadSession → PatientSession conversion
- Previous conversation carried into PatientSession
- Original acquisition source preserved
- Models already reserved for Living Memory, Risk Assessment, and Escalation

## Intentionally NOT implemented yet

Do **not** present this slice as production-secure yet. The next slice must add:

- verified email/phone authentication (current flow is a placeholder)
- encrypted original message storage
- PHI redaction before LLM calls
- deterministic emergency/risk gate
- real LLM integration
- Living Memory extraction and mutation history
- structured escalation payload / clinician queue
- RBAC tests and server-side patient isolation
- rate limiting / guest-retention cleanup

## Local setup

### 1. Create a virtual environment

```bash
python -m venv .venv
```

Activate it.

Windows PowerShell:

```powershell
.venv\Scripts\Activate.ps1
```

macOS/Linux:

```bash
source .venv/bin/activate
```

### 2. Install packages

```bash
pip install -r requirements.txt
```

### 3. Create PostgreSQL database/user

Example:

```sql
CREATE DATABASE nightingale_db;
CREATE USER nightingale_user WITH PASSWORD 'your-password';
GRANT ALL PRIVILEGES ON DATABASE nightingale_db TO nightingale_user;
```

### 4. Set environment variables

Copy `.env.example` values into your shell/environment. Django reads these directly from environment variables.

Minimum:

```text
DJANGO_SECRET_KEY=replace-this
POSTGRES_DB=nightingale_db
POSTGRES_USER=nightingale_user
POSTGRES_PASSWORD=your-password
POSTGRES_HOST=127.0.0.1
POSTGRES_PORT=5432
```

### 5. Create migrations

```bash
python manage.py makemigrations core
python manage.py migrate
```

### 6. Optional admin user

```bash
python manage.py createsuperuser
```

### 7. Run

```bash
python manage.py runserver
```

Open `http://127.0.0.1:8000/`.

## Demo path

1. Choose **Instagram comment** or **Staff referral**.
2. Simulate arrival.
3. In Guest Chat type: `What questions should I ask about egg freezing?`
4. A value event is created and the trust-transition CTA appears.
5. Choose **Review & continue securely**.
6. Enter test email/phone and tick consent.
7. The system creates a Patient + PatientSession and carries the existing conversation forward.
8. The Patient page shows the original acquisition channel/campaign.

## Next implementation slice

The next priority should be:

`message → redaction → deterministic risk gate → allowed LLM call → structured Memory update → response`

Then implement `Send to Clinic` and the required micro-tests.

## Optional: fastest PostgreSQL startup with Docker

If Docker Desktop is installed:

```bash
docker compose up -d db
```

Then use:

```text
POSTGRES_DB=nightingale_db
POSTGRES_USER=nightingale_user
POSTGRES_PASSWORD=nightingale_dev_password
POSTGRES_HOST=127.0.0.1
POSTGRES_PORT=5432
```

## Provenance note

When guest messages are carried into the PatientSession, the copied PatientSession message keeps an `origin_message` pointer back to the original LeadSession message. This prevents conversion from breaking the source chain.

## Channel-rules note

Channel-specific opening strategies live centrally in `core/channel_rules.py`. The request code performs generic rule lookup instead of embedding separate channel wording throughout views.
