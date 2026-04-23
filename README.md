# Probob Design Studio — Enhanced Real-World Version

This updated Flask + SQLite project keeps the existing frontend structure and adds real-world business workflows for a design agency.

## Added Features

- Start Project / client onboarding form
- Quote request management with status updates
- Consultation booking system
- Client dashboard with quote/project/file/invoice data
- Project tracking module
- File upload / asset sharing module
- Revision request workflow
- Invoice management module
- Notifications for client workflow updates
- Admin controls for:
  - quotes
  - bookings
  - projects
  - revisions
  - invoices
  - services
  - pricing
  - portfolio
  - blog posts
  - testimonials
- Services synced to the live Probob service list

## Default Admin Login

- Email: `admin@probobdesign.com`
- Password: `Admin@123`

## Run Locally

```bash
pip install -r requirements.txt
python app.py
```

Then open:

```bash
http://127.0.0.1:5000
```

## Notes

- Database file: `probob.db`
- Uploaded client files are stored in: `static/uploads/`
- Razorpay is optional. If API keys are not configured, the rest of the portal still works.
