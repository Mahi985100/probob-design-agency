import sqlite3
import random
import uuid
import datetime

# Predefined data for random generation
FIRST_NAMES = ['John', 'Jane', 'Michael', 'Emily', 'David', 'Sarah', 'Chris', 'Laura', 'James', 'Emma', 'Robert', 'Olivia', 'Daniel', 'Sophia', 'William', 'Ava']
LAST_NAMES = ['Smith', 'Johnson', 'Brown', 'Taylor', 'Anderson', 'Thomas', 'Jackson', 'White', 'Harris', 'Martin', 'Thompson', 'Garcia', 'Martinez', 'Robinson', 'Clark']
COMPANY_NAMES = ['TechCorp', 'InnoSoft', 'Globex', 'Soylent Corp', 'Initech', 'Umbrella Corp', 'Stark Ind', 'Wayne Ent', 'Massive Dynamic']
WORDS = ['innovative', 'design', 'future', 'process', 'creative', 'solution', 'digital', 'marketing', 'agency', 'growth', 'dynamic', 'smart', 'branding', 'visual']
MAIL_DOMAINS = ['example.com', 'test.com', 'demo.org', 'fake.net', 'company.com']

def random_name(): return f"{random.choice(FIRST_NAMES)} {random.choice(LAST_NAMES)}"
def random_email(name): return f"{name.lower().replace(' ', '.')}_{random.randint(1,999)}@{random.choice(MAIL_DOMAINS)}"
def random_company(): return f"{random.choice(COMPANY_NAMES)} {random.choice(['LLC', 'Inc', 'Ltd', ''])}".strip()
def random_sentence(words=5): return " ".join(random.choices(WORDS, k=words)).capitalize() + "."
def random_text(words=20): return " ".join(random.choices(WORDS, k=words)).capitalize() + "."
def random_phone(): return f"+1-{random.randint(200,999)}-{random.randint(200,999)}-{random.randint(1000,9999)}"
def random_url(): return f"https://www.{random.choice(WORDS)}{random.randint(1,100)}.com"

def generate_random_date(start_days_ago=365):
    if start_days_ago < 0:
        days = random.randint(start_days_ago, 0)
    else:
        days = random.randint(0, start_days_ago)
    secs = random.randint(0, 86400)
    dt = datetime.datetime.now() - datetime.timedelta(days=days, seconds=secs)
    return dt.isoformat(' ', 'seconds')

def get_db():
    db = sqlite3.connect('probob.db')
    db.row_factory = sqlite3.Row
    return db

def seed_db():
    db = get_db()
    cursor = db.cursor()

    # 1. users
    print("Seeding users...")
    user_ids = []
    for _ in range(50):
        name = random_name()
        email = random_email(name)
        pwd = "hashed_password"
        role = random.choice(['user', 'user', 'user', 'admin'])
        created_at = generate_random_date()
        try:
            cursor.execute("INSERT INTO users (name, email, password_hash, role, created_at) VALUES (?, ?, ?, ?, ?)",
                           (name, email, pwd, role, created_at))
            user_ids.append(cursor.lastrowid)
        except sqlite3.IntegrityError:
            pass

    if not user_ids: user_ids = [1] # fallback

    # 2. contacts
    print("Seeding contacts...")
    for _ in range(50):
        name = random_name()
        email = random_email(name)
        subject = random_sentence(6)
        message = random_text(20)
        status = random.choice(['new', 'read', 'replied'])
        created_at = generate_random_date()
        cursor.execute("INSERT INTO contacts (name, email, subject, message, status, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                       (name, email, subject, message, status, created_at))

    # 3. newsletter_subscribers
    print("Seeding newsletter...")
    for _ in range(50):
        email = random_email(random_name())
        subscribed_at = generate_random_date()
        try:
            cursor.execute("INSERT INTO newsletter_subscribers (email, subscribed_at) VALUES (?, ?)", (email, subscribed_at))
        except sqlite3.IntegrityError:
            pass

    # 4. job_applications
    print("Seeding job applications...")
    jobs = ['Graphic Designer', 'Frontend Developer', 'Marketing Manager', 'UI/UX Designer', 'Accountant']
    for _ in range(50):
        job_title = random.choice(jobs)
        applicant_name = random_name()
        applicant_email = random_email(applicant_name)
        portfolio_url = random_url()
        cover_letter = random_text(30)
        status = random.choice(['pending', 'reviewed', 'accepted', 'rejected'])
        applied_at = generate_random_date()
        cursor.execute("INSERT INTO job_applications (job_title, applicant_name, applicant_email, portfolio_url, cover_letter, status, applied_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                       (job_title, applicant_name, applicant_email, portfolio_url, cover_letter, status, applied_at))

    # 5. blog_posts
    print("Seeding blog posts...")
    categories = ['Design', 'Marketing', 'Development', 'Business', 'Lifestyle']
    emojis = ['🎨', '💻', '📈', '🚀', '💡', '🔥']
    for _ in range(50):
        title = random_sentence(6)
        excerpt = random_text(10)
        content = random_text(50)
        category = random.choice(categories)
        author = random_name()
        published_at = generate_random_date()
        emoji = random.choice(emojis)
        cursor.execute("INSERT INTO blog_posts (title, excerpt, content, category, author, published_at, cover_emoji) VALUES (?, ?, ?, ?, ?, ?, ?)",
                       (title, excerpt, content, category, author, published_at, emoji))

    # 6. portfolio_items
    print("Seeding portfolio...")
    for _ in range(50):
        title = random_sentence(3)
        description = random_text(15)
        category = random.choice(['Branding', 'Web Design', 'App Development', 'Print', 'Illustration'])
        emoji = random.choice(emojis)
        featured = random.choice([0, 0, 1])
        created_at = generate_random_date()
        cursor.execute("INSERT INTO portfolio_items (title, description, category, emoji, featured, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                       (title, description, category, emoji, featured, created_at))

    # 7. testimonials
    print("Seeding testimonials...")
    for _ in range(50):
        client_name = random_name()
        company = random_company()
        message = random_text(12)
        rating = random.randint(3, 5)
        created_at = generate_random_date()
        cursor.execute("INSERT INTO testimonials (client_name, company, message, rating, created_at) VALUES (?, ?, ?, ?, ?)",
                       (client_name, company, message, rating, created_at))

    # 8. service_items
    print("Seeding services...")
    for _ in range(50):
        title = random_sentence(2)
        description = random_text(10)
        icon = random.choice(emojis)
        f1 = random.choice(WORDS)
        f2 = random.choice(WORDS)
        f3 = random.choice(WORDS)
        f4 = random.choice(WORDS)
        created_at = generate_random_date()
        cursor.execute("INSERT INTO service_items (title, description, icon, feature_1, feature_2, feature_3, feature_4, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                       (title, description, icon, f1, f2, f3, f4, created_at))

    # 9. quote_requests
    print("Seeding quote requests...")
    quote_ids = []
    services = ['Logo Design', 'Web Development', 'SEO Optimization', 'Branding', 'Content Creation']
    for _ in range(50):
        user_id = random.choice(user_ids)
        client_name = random_name()
        email = random_email(client_name)
        phone = random_phone()
        company = random_company()
        service = random.choice(services)
        budget = random.choice(['1k-5k', '5k-10k', '10k+', 'Not sure'])
        deadline = generate_random_date(-30) # Future roughly
        business_type = random.choice(['B2B', 'B2C', 'E-commerce', 'Startup'])
        description = random_text(20)
        status = random.choice(['New', 'In Progress', 'Completed', 'Rejected'])
        source = random.choice(['website', 'referral', 'social media'])
        created_at = generate_random_date()
        cursor.execute('''INSERT INTO quote_requests (user_id, client_name, email, phone, company, service, budget_range, deadline, business_type, project_description, status, source, created_at)
                          VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                       (user_id, client_name, email, phone, company, service, budget, deadline, business_type, description, status, source, created_at))
        quote_ids.append(cursor.lastrowid)

    # 10. projects
    print("Seeding projects...")
    project_ids = []
    for _ in range(50):
        user_id = random.choice(user_ids)
        quote_id = random.choice(quote_ids + [None])
        title = random_sentence(3)
        service = random.choice(services)
        brief = random_text(20)
        status = random.choice(['Inquiry Received', 'In Progress', 'Review', 'Completed'])
        priority = random.choice(['Low', 'Medium', 'High'])
        budget = f"{random.randint(1000, 20000)}"
        due_date = generate_random_date(-60)
        designer = random_name()
        progress = random.randint(0, 100)
        created_at = generate_random_date()
        cursor.execute('''INSERT INTO projects (user_id, quote_id, title, service, brief, status, priority, budget, due_date, designer_name, progress, created_at)
                          VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                       (user_id, quote_id, title, service, brief, status, priority, budget, due_date, designer, progress, created_at))
        project_ids.append(cursor.lastrowid)

    # 11. payments
    print("Seeding payments...")
    for _ in range(50):
        receipt = f"REC-{random.randint(10000000, 99999999)}"
        name = random_name()
        email = random_email(name)
        phone = random_phone()
        service = random.choice(services)
        project = random_sentence(3)
        amount = random.randint(1000, 50000)
        currency = random.choice(['INR', 'USD'])
        status = random.choice(['created', 'paid', 'failed'])
        date_str = generate_random_date()
        created_at = date_str
        try:
            cursor.execute('''INSERT INTO payments (receipt_no, name, email, phone, service, project, amount, currency, status, date_str, created_at)
                              VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                           (receipt, name, email, phone, service, project, amount, currency, status, date_str, created_at))
        except sqlite3.IntegrityError:
            pass

    # 12. bookings
    print("Seeding bookings...")
    for _ in range(50):
        user_id = random.choice(user_ids)
        name = random_name()
        email = random_email(name)
        phone = random_phone()
        service = random.choice(services)
        b_date = generate_random_date()
        b_time = f"{random.randint(9, 17)}:00"
        mode = random.choice(['Zoom', 'Google Meet', 'In-Person'])
        notes = random_text(10)
        status = random.choice(['Requested', 'Confirmed', 'Cancelled'])
        created_at = generate_random_date()
        cursor.execute('''INSERT INTO bookings (user_id, name, email, phone, service_interest, booking_date, booking_time, meeting_mode, notes, status, created_at)
                          VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                       (user_id, name, email, phone, service, b_date, b_time, mode, notes, status, created_at))

    # 13. project_files
    print("Seeding project files...")
    for _ in range(50):
        p_id = random.choice(project_ids) if project_ids else 1
        u_id = random.choice(user_ids)
        title = random.choice(WORDS)
        filename = f"file_{random.randint(1,1000)}.pdf"
        filepath = f"/static/uploads/{filename}"
        ftype = 'pdf'
        role = random.choice(['user', 'admin'])
        created_at = generate_random_date()
        cursor.execute("INSERT INTO project_files (project_id, user_id, title, filename, file_path, file_type, uploaded_by_role, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                       (p_id, u_id, title, filename, filepath, ftype, role, created_at))

    # 14. revision_requests
    print("Seeding revision requests...")
    for _ in range(50):
        p_id = random.choice(project_ids) if project_ids else 1
        u_id = random.choice(user_ids)
        rev_no = random.randint(1, 3)
        comments = random_text(15)
        status = random.choice(['Pending', 'Reviewed', 'Implemented'])
        created_at = generate_random_date()
        cursor.execute("INSERT INTO revision_requests (project_id, user_id, revision_no, comments, status, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                       (p_id, u_id, rev_no, comments, status, created_at))

    # 15. invoices
    print("Seeding invoices...")
    for _ in range(50):
        p_id = random.choice(project_ids) if project_ids else 1
        u_id = random.choice(user_ids)
        inv_no = f"INV-{random.randint(100000, 999999)}"
        title = "Phase payment"
        amount = f"{random.randint(500, 5000)}"
        due_date = generate_random_date(-30)
        status = random.choice(['Pending', 'Paid', 'Overdue'])
        notes = random_text(10)
        created_at = generate_random_date()
        cursor.execute("INSERT INTO invoices (project_id, user_id, invoice_no, title, amount, due_date, status, notes, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                       (p_id, u_id, inv_no, title, amount, due_date, status, notes, created_at))

    # 16. project_status_history
    print("Seeding status history...")
    for _ in range(50):
        p_id = random.choice(project_ids) if project_ids else 1
        old_s = 'Pending'
        new_s = 'In Progress'
        note = random_sentence(4)
        created_at = generate_random_date()
        cursor.execute("INSERT INTO project_status_history (project_id, old_status, new_status, note, created_at) VALUES (?, ?, ?, ?, ?)",
                       (p_id, old_s, new_s, note, created_at))

    # 17. notifications
    print("Seeding notifications...")
    for _ in range(50):
        u_id = random.choice(user_ids)
        title = random_sentence(3)
        msg = random_text(10)
        link = "/dashboard"
        is_read = random.choice([0, 1])
        created_at = generate_random_date()
        cursor.execute("INSERT INTO notifications (user_id, title, message, link, is_read, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                       (u_id, title, msg, link, is_read, created_at))

    db.commit()
    print("Successfully seeded all tables with ~50 records each!")

if __name__ == '__main__':
    seed_db()
