import os
import hashlib
import hmac
import secrets
import smtplib
import uuid
from datetime import datetime, timedelta
from functools import wraps
from email.message import EmailMessage
from pathlib import Path
import sqlite3
import calendar
import csv
from io import BytesIO, StringIO

from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify, g, send_file
from werkzeug.utils import secure_filename
from fpdf import FPDF

try:
    from dotenv import load_dotenv
except Exception:
    def load_dotenv(*args, **kwargs):
        return False

try:
    import razorpay
except Exception:
    razorpay = None

load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY') or secrets.token_hex(32)
app.permanent_session_lifetime = timedelta(hours=8)
BASE_DIR = Path(__file__).resolve().parent
DATABASE = os.environ.get('DATABASE_PATH', str(BASE_DIR / 'probob.db'))
UPLOAD_FOLDER = BASE_DIR / 'static' / 'uploads'
UPLOAD_FOLDER.mkdir(parents=True, exist_ok=True)
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp', 'pdf', 'doc', 'docx', 'txt', 'svg'}
MAX_CONTENT_LENGTH = 10 * 1024 * 1024
app.config['MAX_CONTENT_LENGTH'] = MAX_CONTENT_LENGTH

MAIL_SERVER = os.environ.get('MAIL_SERVER', 'smtp.gmail.com')
MAIL_PORT = int(os.environ.get('MAIL_PORT', '587'))
MAIL_USERNAME = os.environ.get('MAIL_USERNAME', '')
MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD', '')
MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS', 'true').lower() == 'true'
MAIL_FROM = os.environ.get('MAIL_FROM', MAIL_USERNAME or 'no-reply@probobdesign.com')
RAZORPAY_KEY_ID = os.environ.get('RAZORPAY_KEY_ID', '')
RAZORPAY_KEY_SECRET = os.environ.get('RAZORPAY_KEY_SECRET', '')
RAZORPAY_WEBHOOK_SECRET = os.environ.get('RAZORPAY_WEBHOOK_SECRET', '')

if razorpay and RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET:
    razorpay_client = razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET))
else:
    razorpay_client = None


def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
        db.row_factory = sqlite3.Row
    return db


@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()


def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


def allowed_file(filename: str) -> bool:
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def now_iso() -> str:
    return datetime.utcnow().replace(microsecond=0).isoformat()


def parse_money_to_int(value, default=0):
    try:
        if value is None:
            return default
        cleaned = str(value).replace(',', '').replace('₹', '').strip()
        if not cleaned:
            return default
        return int(round(float(cleaned)))
    except (TypeError, ValueError):
        return default


def format_invoice_status(status):
    raw = (status or 'Pending').strip().lower()
    mapping = {
        'paid': 'Paid',
        'partially_paid': 'Partially Paid',
        'partial': 'Partially Paid',
        'overdue': 'Overdue',
        'cancelled': 'Cancelled',
        'failed': 'Failed',
    }
    return mapping.get(raw, 'Pending')


def parse_package_features(raw_text):
    return [line.strip() for line in (raw_text or '').splitlines() if line.strip()]


def get_read_time(content):
    words = len((content or '').split())
    minutes = max(1, round(words / 200))
    return f"{minutes} min read"


def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('login', next=request.path))
        return f(*args, **kwargs)
    return decorated


def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        user = get_current_user()
        if not user:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('login', next=request.path))
        if user['role'] != 'admin':
            flash('Admin access only.', 'error')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated


def get_current_user():
    if 'user_id' not in session:
        return None
    return get_db().execute('SELECT * FROM users WHERE id=?', (session['user_id'],)).fetchone()


def get_user_notifications(limit=5, only_unread=False):
    user = get_current_user()
    if not user:
        return []
    query = 'SELECT * FROM notifications WHERE user_id=?'
    params = [user['id']]
    if only_unread:
        query += ' AND is_read=0'
    query += ' ORDER BY id DESC LIMIT ?'
    params.append(limit)
    return get_db().execute(query, tuple(params)).fetchall()


def unread_notification_count():
    user = get_current_user()
    if not user:
        return 0
    return get_db().execute('SELECT COUNT(*) FROM notifications WHERE user_id=? AND is_read=0', (user['id'],)).fetchone()[0]


def log_activity(actor_user_id, area, action, details=''):
    db = get_db()
    db.execute('INSERT INTO activity_logs (actor_user_id, area, action, details, created_at) VALUES (?,?,?,?,?)', (actor_user_id, area, action, details, now_iso()))
    db.commit()


@app.context_processor
def inject_user():
    user = get_current_user()
    play_login_sound = bool(session.pop('play_login_sound', False))
    return {
        'current_user': user,
        'notif_preview': get_user_notifications(limit=5) if user else [],
        'notif_unread_count': unread_notification_count() if user else 0,
        'play_login_sound': play_login_sound,
        'now_iso': now_iso
    }


def send_email_notice(to_email: str, subject: str, body: str):
    if not MAIL_USERNAME or not MAIL_PASSWORD:
        return False
    msg = EmailMessage()
    msg['Subject'] = subject
    msg['From'] = MAIL_FROM
    msg['To'] = to_email
    msg.set_content(body)
    try:
        with smtplib.SMTP(MAIL_SERVER, MAIL_PORT) as server:
            if MAIL_USE_TLS:
                server.starttls()
            server.login(MAIL_USERNAME, MAIL_PASSWORD)
            server.send_message(msg)
        return True
    except Exception:
        return False


def add_notification(user_id, title, message, link=''):
    db = get_db()
    db.execute(
        'INSERT INTO notifications (user_id,title,message,link,is_read,created_at) VALUES (?,?,?,?,0,?)',
        (user_id, title, message, link, now_iso())
    )
    db.commit()


def ensure_column(db, table_name, column_name, definition):
    existing = {row[1] for row in db.execute(f"PRAGMA table_info({table_name})").fetchall()}
    if column_name not in existing:
        db.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {definition}")


def run_payment_migrations(db):
    ensure_column(db, 'payments', 'user_id', 'INTEGER')
    ensure_column(db, 'payments', 'project_id', 'INTEGER')
    ensure_column(db, 'payments', 'invoice_id', 'INTEGER')
    ensure_column(db, 'payments', 'payment_method', 'TEXT')
    ensure_column(db, 'payments', 'notes', 'TEXT')
    ensure_column(db, 'payments', 'verified_at', 'TEXT')
    ensure_column(db, 'payments', 'webhook_event_id', 'TEXT')
    ensure_column(db, 'payments', 'webhook_payload', 'TEXT')
    ensure_column(db, 'payments', 'failure_reason', 'TEXT')
    ensure_column(db, 'invoices', 'paid_amount', 'INTEGER DEFAULT 0')
    ensure_column(db, 'invoices', 'balance_amount', 'INTEGER DEFAULT 0')
    ensure_column(db, 'users', 'status', "TEXT DEFAULT 'active'")
    ensure_column(db, 'testimonials', 'user_id', 'INTEGER')
    ensure_column(db, 'testimonials', 'status', "TEXT DEFAULT 'approved'")
    ensure_column(db, 'testimonials', 'is_featured', 'INTEGER DEFAULT 0')


def sync_invoice_balance(db, invoice_id):
    if not invoice_id:
        return
    invoice = db.execute('SELECT * FROM invoices WHERE id=?', (invoice_id,)).fetchone()
    if not invoice:
        return
    total_amount = parse_money_to_int(invoice['amount'])
    paid_amount = db.execute(
        "SELECT COALESCE(SUM(amount), 0) FROM payments WHERE invoice_id=? AND LOWER(COALESCE(status,'')) IN ('paid','received')",
        (invoice_id,)
    ).fetchone()[0] or 0
    balance_amount = max(total_amount - paid_amount, 0)
    current_status = (invoice['status'] or '').strip().lower()
    if total_amount > 0 and paid_amount >= total_amount:
        status = 'Paid'
    elif paid_amount > 0:
        status = 'Partially Paid'
    elif current_status in {'overdue', 'cancelled'}:
        status = format_invoice_status(invoice['status'])
    else:
        status = 'Pending'
    db.execute('UPDATE invoices SET paid_amount=?, balance_amount=?, status=? WHERE id=?', (paid_amount, balance_amount, status, invoice_id))


def mark_payment_success(db, payment_row, payment_id, signature='', gateway_status='paid', payment_method='Razorpay', webhook_event_id=None, webhook_payload=None):
    if not payment_row:
        return None
    paid_at = now_iso()
    db.execute(
        '''UPDATE payments
           SET status=?, gateway_status=?, razorpay_payment_id=?, razorpay_signature=?, paid_at=?, verified_at=?, payment_method=?, webhook_event_id=COALESCE(?, webhook_event_id), webhook_payload=COALESCE(?, webhook_payload), failure_reason=NULL
           WHERE id=?''',
        ('paid', gateway_status, payment_id, signature, paid_at, paid_at, payment_method, webhook_event_id, webhook_payload, payment_row['id'])
    )
    if payment_row['invoice_id']:
        sync_invoice_balance(db, payment_row['invoice_id'])
        invoice = db.execute('SELECT * FROM invoices WHERE id=?', (payment_row['invoice_id'],)).fetchone()
        if invoice and payment_row['user_id']:
            add_notification(payment_row['user_id'], 'Payment received', f"Payment for invoice {invoice['invoice_no']} was received successfully.", f"/receipt/{payment_row['receipt_no']}")
    elif payment_row['user_id']:
        add_notification(payment_row['user_id'], 'Payment received', 'Your payment was received successfully.', f"/receipt/{payment_row['receipt_no']}")
    return paid_at



def init_db():
    db = get_db()
    db.executescript(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT DEFAULT 'user',
            reset_token TEXT,
            reset_token_expires TEXT,
            status TEXT DEFAULT 'active',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS contacts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT NOT NULL,
            subject TEXT,
            message TEXT NOT NULL,
            status TEXT DEFAULT 'new',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS newsletter_subscribers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            subscribed_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS job_applications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            job_title TEXT NOT NULL,
            applicant_name TEXT NOT NULL,
            applicant_email TEXT NOT NULL,
            portfolio_url TEXT,
            cover_letter TEXT,
            status TEXT DEFAULT 'pending',
            applied_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS blog_posts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            excerpt TEXT,
            content TEXT,
            category TEXT,
            author TEXT DEFAULT 'Probob Team',
            published_at TEXT DEFAULT CURRENT_TIMESTAMP,
            cover_emoji TEXT DEFAULT '📝'
        );
        CREATE TABLE IF NOT EXISTS portfolio_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT,
            category TEXT,
            emoji TEXT DEFAULT '🎨',
            featured INTEGER DEFAULT 0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS testimonials (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            client_name TEXT NOT NULL,
            company TEXT,
            message TEXT NOT NULL,
            rating INTEGER DEFAULT 5,
            user_id INTEGER,
            status TEXT DEFAULT 'approved',
            is_featured INTEGER DEFAULT 0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS service_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT,
            icon TEXT DEFAULT '🎨',
            feature_1 TEXT,
            feature_2 TEXT,
            feature_3 TEXT,
            feature_4 TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS payments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            receipt_no TEXT UNIQUE,
            user_id INTEGER,
            project_id INTEGER,
            invoice_id INTEGER,
            name TEXT,
            email TEXT,
            phone TEXT,
            service TEXT,
            project TEXT,
            amount INTEGER,
            currency TEXT DEFAULT 'INR',
            razorpay_order_id TEXT,
            razorpay_payment_id TEXT,
            razorpay_signature TEXT,
            payment_method TEXT,
            notes TEXT,
            status TEXT DEFAULT 'created',
            gateway_status TEXT,
            date_str TEXT,
            paid_at TEXT,
            verified_at TEXT,
            webhook_event_id TEXT,
            webhook_payload TEXT,
            failure_reason TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS quote_requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            client_name TEXT NOT NULL,
            email TEXT NOT NULL,
            phone TEXT,
            company TEXT,
            service TEXT NOT NULL,
            budget_range TEXT,
            deadline TEXT,
            business_type TEXT,
            project_description TEXT NOT NULL,
            status TEXT DEFAULT 'New',
            source TEXT DEFAULT 'website',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS bookings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            name TEXT NOT NULL,
            email TEXT NOT NULL,
            phone TEXT,
            service_interest TEXT,
            booking_date TEXT,
            booking_time TEXT,
            meeting_mode TEXT,
            notes TEXT,
            status TEXT DEFAULT 'Requested',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS projects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            quote_id INTEGER,
            title TEXT NOT NULL,
            service TEXT,
            brief TEXT,
            status TEXT DEFAULT 'Inquiry Received',
            priority TEXT DEFAULT 'Medium',
            budget TEXT,
            due_date TEXT,
            designer_name TEXT,
            progress INTEGER DEFAULT 0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS project_files (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER,
            user_id INTEGER,
            title TEXT,
            filename TEXT,
            file_path TEXT,
            file_type TEXT,
            uploaded_by_role TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS revision_requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER,
            user_id INTEGER,
            revision_no INTEGER DEFAULT 1,
            comments TEXT,
            attachment_path TEXT,
            status TEXT DEFAULT 'Pending',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS invoices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER,
            user_id INTEGER,
            invoice_no TEXT,
            title TEXT,
            amount TEXT,
            paid_amount INTEGER DEFAULT 0,
            balance_amount INTEGER DEFAULT 0,
            due_date TEXT,
            status TEXT DEFAULT 'Pending',
            notes TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS project_status_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER,
            old_status TEXT,
            new_status TEXT,
            note TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS notifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            title TEXT,
            message TEXT,
            link TEXT,
            is_read INTEGER DEFAULT 0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS activity_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            actor_user_id INTEGER,
            area TEXT,
            action TEXT,
            details TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS feedbacks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            rating INTEGER NOT NULL,
            comment TEXT,
            action_type TEXT,
            action_id INTEGER,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        """
    )
    db.commit()
    run_payment_migrations(db)
    seed_data(db)




def ensure_blog_posts_schema(db):
    try:
        columns = db.execute("PRAGMA table_info(blog_posts)").fetchall()
        column_names = [col[1] for col in columns]
        if "created_at" not in column_names:
            db.execute("ALTER TABLE blog_posts ADD COLUMN created_at TEXT")
        if "slug" not in column_names:
            db.execute("ALTER TABLE blog_posts ADD COLUMN slug TEXT")
        if "cover_image" not in column_names:
            db.execute("ALTER TABLE blog_posts ADD COLUMN cover_image TEXT")
        db.commit()
    except Exception as e:
        print("Schema check error:", e)


def ensure_portfolio_items_schema(db):
    try:
        columns = db.execute("PRAGMA table_info(portfolio_items)").fetchall()
        column_names = [col[1] for col in columns]
        if "cover_image" not in column_names:
            db.execute("ALTER TABLE portfolio_items ADD COLUMN cover_image TEXT")
        db.commit()
    except Exception as e:
        print("Portfolio schema check error:", e)


def seed_data(db):
    ensure_blog_posts_schema(db)
    ensure_portfolio_items_schema(db)
    if not db.execute('SELECT 1 FROM users WHERE email=?', ('admin@probobdesign.com',)).fetchone():
        db.execute('INSERT INTO users (name,email,password_hash,role) VALUES (?,?,?,?)', ('Admin', 'admin@probobdesign.com', hash_password('Admin@123'), 'admin'))

    services = [
        ('Logo & Stationary Design', 'Build a memorable identity system with logo concepts, business stationery, and brand-ready files.', '🧿', 'Logo concepts', 'Business card & letterhead', 'Color and typography guidance', 'Ready-to-use source files'),
        ('Branding & Advertising', 'Create a complete brand language for digital and offline campaigns, promotions, and market presence.', '📣', 'Brand positioning visuals', 'Ad creatives', 'Campaign design direction', 'Consistent brand collaterals'),
        ('Packaging & Label Design', 'Design shelf-ready packaging and labels that improve recall, trust, and product presentation.', '📦', 'Box and pouch design', 'Label system', 'Print-ready artwork', 'Packaging mockups'),
        ('Office Branding Design', 'Transform offices and retail spaces with signage, wall graphics, and branded interior visuals.', '🏢', 'Reception branding', 'Directional signage', 'Wall graphics', 'Storefront visuals'),
        ('Ambiance Design', 'Create aesthetic visual experiences for cafés, stores, events, and experiential spaces.', '✨', 'Moodboards', 'Theme direction', 'Visual styling support', 'Print/display coordination'),
        ('E-Commerce Design', 'Prepare optimized product images and creative content for marketplaces and D2C stores.', '🛒', 'Marketplace image design', 'Banner creatives', 'Image retouching', 'Conversion-focused layouts'),
        ('Social Media Marketing', 'Design high-engagement content systems for Instagram, Facebook, LinkedIn, and paid promotions.', '📱', 'Post templates', 'Story creatives', 'Campaign visuals', 'Monthly design support'),
        ('Event & Exhibition Stall Design', 'Design exhibition booths, event branding, and large-format graphics with strong visual impact.', '🎪', 'Stall concept design', 'Backdrop and standees', 'Print coordination files', 'Visitor flow visuals'),
        ('Website Design', 'Craft modern website UI layouts with clean structure, strong branding, and conversion-first sections.', '🌐', 'Landing page UI', 'Business website design', 'Responsive layouts', 'Developer handoff support'),
        ('Content Writing', 'Support visuals with conversion-oriented copy, service content, product text, and brand messaging.', '✍️', 'Website copy', 'Product descriptions', 'Brochure content', 'Campaign messaging'),
    ]
    existing_titles = {r['title'] for r in db.execute('SELECT title FROM service_items').fetchall()}
    if 'Logo & Stationary Design' not in existing_titles or len(existing_titles) < 10:
        db.execute('DELETE FROM service_items')
        db.executemany('INSERT INTO service_items (title,description,icon,feature_1,feature_2,feature_3,feature_4) VALUES (?,?,?,?,?,?,?)', services)


    if db.execute('SELECT COUNT(*) FROM blog_posts').fetchone()[0] == 0:
        posts = [
            ('How Good Packaging Improves Product Sales', 'A practical look at packaging decisions that influence trust and shelf appeal.', 'Strong packaging design communicates value before a customer even picks up the product. At Probob, we focus on structure, hierarchy, color, and clarity so packaging feels premium and purposeful.', 'Branding', 'Probob Team', '2026-04-01', '📦'),
            ('What Makes a Brand Identity Memorable', 'Simple identity systems help brands stay recognisable across every touchpoint.', 'A memorable brand identity is not just a logo. It is a consistent visual language that customers recognise in print, digital, packaging, and communication.', 'Design', 'Probob Team', '2026-03-18', '🎨'),
            ('Why Businesses Need a Better Design Brief', 'A good brief saves time and leads to faster approvals and stronger creative output.', 'A clear design brief reduces revisions, avoids confusion, and helps agencies move quickly with more confidence.', 'Process', 'Probob Team', '2026-03-02', '📝'),
        ]
        db.executemany('INSERT INTO blog_posts (title,excerpt,content,category,author,published_at,cover_emoji) VALUES (?,?,?,?,?,?,?)', posts)

    if db.execute('SELECT COUNT(*) FROM portfolio_items').fetchone()[0] == 0:
        items = [
            ('Snack Box Packaging Refresh', 'Premium packaging concept for a fast-growing FMCG brand.', 'Packaging', '📦', 1),
            ('Corporate Office Branding', 'Wayfinding, wall graphics, and reception branding for a modern office.', 'Branding', '🏢', 1),
            ('Marketplace Product Creative Set', 'Amazon/Flipkart-ready visual assets and product image optimization.', 'E-Commerce', '🛒', 1),
            ('Exhibition Stall Campaign', 'Booth design and print collaterals for a regional expo.', 'Event', '🎪', 0),
        ]
        db.executemany('INSERT INTO portfolio_items (title,description,category,emoji,featured) VALUES (?,?,?,?,?)', items)

    if db.execute('SELECT COUNT(*) FROM testimonials').fetchone()[0] == 0:
        testimonials = [
            ('Piyush Jesani', 'Managing Director', 'Very responsive team and strong design thinking from start to finish.', 5),
            ('Ravindra Puttewar', 'Aditi IT Services', 'Quick responses, clear communication, and dependable creative support.', 5),
            ('Kaushal Agrawal', 'Owner', 'The logo and packaging work was handled beautifully.', 5),
        ]
        db.executemany('INSERT INTO testimonials (client_name,company,message,rating) VALUES (?,?,?,?)', testimonials)
    db.commit()


def create_project_from_quote(quote_id, note='Project created from user start-project request', notify_user=True):
    db = get_db()
    quote = db.execute('SELECT * FROM quote_requests WHERE id=?', (quote_id,)).fetchone()
    if not quote:
        return None
    existing = db.execute('SELECT id FROM projects WHERE quote_id=?', (quote_id,)).fetchone()
    if existing:
        return existing['id']
    title = f"{quote['service']} Project"
    db.execute(
        '''
        INSERT INTO projects (user_id, quote_id, title, service, brief, status, priority, budget, due_date, designer_name, progress)
        VALUES (?, ?, ?, ?, ?, 'Inquiry Received', 'Medium', ?, ?, ?, 0)
        ''',
        (quote['user_id'], quote_id, title, quote['service'], quote['project_description'], quote['budget_range'], quote['deadline'], 'Probob Team')
    )
    project_id = db.execute('SELECT last_insert_rowid()').fetchone()[0]
    db.execute('INSERT INTO project_status_history (project_id,old_status,new_status,note,created_at) VALUES (?,?,?,?,?)', (project_id, 'New', 'Inquiry Received', note, now_iso()))
    db.commit()
    if notify_user and quote['user_id']:
        add_notification(quote['user_id'], 'Project request received', f"Your {quote['service']} project is now visible in tracking.", '/dashboard')
    return project_id


def sync_started_projects_to_admin():
    db = get_db()
    missing_quotes = db.execute('''
        SELECT qr.id
        FROM quote_requests qr
        LEFT JOIN projects p ON p.quote_id = qr.id
        WHERE p.id IS NULL
        ORDER BY qr.id ASC
    ''').fetchall()
    for row in missing_quotes:
        create_project_from_quote(row['id'], note='Backfilled into admin projects from existing start-project request', notify_user=False)


@app.route('/')
def index():
    db = get_db()
    portfolio = db.execute('SELECT * FROM portfolio_items WHERE featured=1 ORDER BY id DESC LIMIT 3').fetchall()
    testimonials = db.execute("SELECT * FROM testimonials WHERE status='approved' AND is_featured=1 ORDER BY id DESC LIMIT 6").fetchall()
    return render_template('index.html', portfolio=portfolio, testimonials=testimonials)


@app.route('/portfolio')
def portfolio():
    db = get_db()
    category = request.args.get('category', 'All')
    if category == 'All':
        items = db.execute('SELECT * FROM portfolio_items ORDER BY featured DESC, id DESC').fetchall()
    else:
        items = db.execute('SELECT * FROM portfolio_items WHERE category=? ORDER BY id DESC', (category,)).fetchall()
    categories = ['All'] + sorted({row['category'] for row in db.execute('SELECT DISTINCT category FROM portfolio_items WHERE category IS NOT NULL AND category != ""').fetchall()})
    return render_template('portfolio.html', items=items, categories=categories, active_cat=category)


@app.route('/case-studies')
def case_studies():
    items = get_db().execute('SELECT * FROM portfolio_items ORDER BY featured DESC, id DESC LIMIT 6').fetchall()
    return render_template('case_studies.html', items=items)


@app.route('/showreel')
def showreel():
    return render_template('showreel.html')


@app.route('/services')
def services():
    items = get_db().execute('SELECT * FROM service_items ORDER BY id ASC').fetchall()
    return render_template('services.html', items=items)


@app.route('/process')
def process():
    return render_template('process.html')



@app.route('/about')
def about():
    testimonials = get_db().execute("SELECT * FROM testimonials WHERE status='approved' ORDER BY id DESC").fetchall()
    return render_template('about.html', testimonials=testimonials)


@app.route('/team')
def team():
    return render_template('team.html')


@app.route('/careers', methods=['GET', 'POST'])
def careers():
    if request.method == 'POST':
        data = {
            'job_title': request.form.get('job_title', '').strip(),
            'applicant_name': request.form.get('name', '').strip(),
            'applicant_email': request.form.get('email', '').strip(),
            'portfolio_url': request.form.get('portfolio_url', '').strip(),
            'cover_letter': request.form.get('cover_letter', '').strip(),
        }
        if not data['applicant_name'] or not data['applicant_email']:
            flash('Name and email are required.', 'error')
        else:
            db = get_db()
            db.execute('INSERT INTO job_applications (job_title,applicant_name,applicant_email,portfolio_url,cover_letter) VALUES (?,?,?,?,?)',
                       (data['job_title'], data['applicant_name'], data['applicant_email'], data['portfolio_url'], data['cover_letter']))
            db.commit()
            flash('Application submitted! We will be in touch soon.', 'success')
            return redirect(url_for('careers'))
    jobs = [
        {'title': 'Graphic Designer', 'location': 'Ahmedabad', 'type': 'Full-time', 'icon': '🎨'},
        {'title': 'Branding Intern', 'location': 'Ahmedabad', 'type': 'Internship', 'icon': '📣'},
        {'title': 'Content Writer', 'location': 'Hybrid', 'type': 'Part-time', 'icon': '✍️'},
    ]
    return render_template('careers.html', jobs=jobs)


@app.route('/blog')
def blog():
    db = get_db()
    cat = request.args.get('category', '').strip()
    query = 'SELECT * FROM blog_posts'
    params = []
    if cat:
        query += ' WHERE category=?'
        params.append(cat)
    query += ' ORDER BY datetime(published_at) DESC, id DESC'
    
    post_rows = db.execute(query, params).fetchall()
    posts = [dict(row) for row in post_rows]
    
    # Get all unique categories for the filter
    categories = db.execute('SELECT DISTINCT category FROM blog_posts WHERE category IS NOT NULL').fetchall()
    
    return render_template('blog_react_exact.html', posts=posts, categories=[r['category'] for r in categories], active_cat=cat)


@app.route('/blog/<int:post_id>')
def blog_post(post_id):
    db = get_db()
    user = get_current_user()
    post = db.execute('SELECT * FROM blog_posts WHERE id=?', (post_id,)).fetchone()
    if not post:
        flash('Post not found.', 'error')
        return redirect(url_for('blog'))
    
    post = dict(post)
    post['read_time'] = get_read_time(post['content'])
    
    likes_count = db.execute('SELECT COUNT(*) FROM blog_likes WHERE post_id=?', (post_id,)).fetchone()[0]
    comments = db.execute(
        'SELECT c.*, u.name as user_name FROM blog_comments c JOIN users u ON c.user_id = u.id WHERE c.post_id=? ORDER BY c.id DESC',
        (post_id,)
    ).fetchall()
    
    user_liked = False
    if user:
        user_liked = db.execute('SELECT 1 FROM blog_likes WHERE post_id=? AND user_id=?', (post_id, user['id'])).fetchone() is not None

    return render_template('blog_post.html', post=post, likes_count=likes_count, comments=comments, user_liked=user_liked)


@app.route('/blog/<int:post_id>/like', methods=['POST'])
@login_required
def blog_like(post_id):
    user = get_current_user()
    db = get_db()
    existing = db.execute('SELECT id FROM blog_likes WHERE post_id=? AND user_id=?', (post_id, user['id'])).fetchone()
    if existing:
        db.execute('DELETE FROM blog_likes WHERE id=?', (existing['id'],))
        db.commit()
        return jsonify({'status': 'unliked'})
    else:
        db.execute('INSERT INTO blog_likes (post_id, user_id) VALUES (?, ?)', (post_id, user['id']))
        db.commit()
        return jsonify({'status': 'liked'})


@app.route('/blog/<int:post_id>/comment', methods=['POST'])
@login_required
def blog_comment(post_id):
    user = get_current_user()
    content = request.form.get('comment', '').strip()
    if content:
        db = get_db()
        db.execute('INSERT INTO blog_comments (post_id, user_id, comment) VALUES (?, ?, ?)', (post_id, user['id'], content))
        db.commit()
        flash('Comment added!', 'success')
    return redirect(url_for('blog_post', post_id=post_id))


@app.route('/faq')
def faq():
    faqs = [
        {'q': 'Can I request a quote online?', 'a': 'Yes. Use the Start Project form and the admin will review budget, scope, and delivery timeline.'},
        {'q': 'Can I upload brand assets after login?', 'a': 'Yes. Clients can upload briefs, logos, references, and payment proofs from the dashboard.'},
        {'q': 'Do you support revisions?', 'a': 'Yes. Each active project includes a revision request workflow with notes and optional attachments.'},
        {'q': 'Can I book a consultation?', 'a': 'Yes. Use the booking page to request a discovery call or design consultation.'},
    ]
    return render_template('faq.html', faqs=faqs)


@app.route('/contact', methods=['GET', 'POST'])
def contact():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip()
        subject = request.form.get('subject', '').strip()
        message = request.form.get('message', '').strip()
        if not name or not email or not message:
            flash('Name, email, and message are required.', 'error')
        else:
            db = get_db()
            db.execute('INSERT INTO contacts (name,email,subject,message,status,created_at) VALUES (?,?,?,?,?,?)',
                       (name, email, subject, message, 'new', now_iso()))
            db.commit()
            flash('Message sent successfully.', 'success')
            return redirect(url_for('contact'))
    return render_template('contact.html')


@app.route('/newsletter/subscribe', methods=['POST'])
def newsletter_subscribe():
    email = request.form.get('email', '').strip()
    if not email or '@' not in email:
        flash('Please enter a valid email address.', 'error')
        return redirect(request.referrer or url_for('index'))
    db = get_db()
    if db.execute('SELECT id FROM newsletter_subscribers WHERE email=?', (email,)).fetchone():
        flash('You are already subscribed.', 'info')
    else:
        db.execute('INSERT INTO newsletter_subscribers (email, subscribed_at) VALUES (?,?)', (email, now_iso()))
        db.commit()
        flash('Thanks for subscribing!', 'success')
    return redirect(request.referrer or url_for('index'))


@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if get_current_user():
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        confirm = request.form.get('confirm_password', '')
        if not name or not email or not password:
            flash('All fields are required.', 'error')
        elif password != confirm:
            flash('Passwords do not match.', 'error')
        elif len(password) < 6:
            flash('Password must be at least 6 characters.', 'error')
        else:
            db = get_db()
            if db.execute('SELECT id FROM users WHERE email=?', (email,)).fetchone():
                flash('An account with this email already exists.', 'error')
            else:
                db.execute('INSERT INTO users (name,email,password_hash,created_at) VALUES (?,?,?,?)', (name, email, hash_password(password), now_iso()))
                db.commit()
                user = db.execute('SELECT * FROM users WHERE email=?', (email,)).fetchone()
                session['user_id'] = user['id']
                session['user_name'] = user['name']
                flash('Welcome! Your account has been created.', 'success')
                return redirect(url_for('dashboard'))
    return render_template('signup.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if get_current_user():
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')

        user = get_db().execute(
            'SELECT * FROM users WHERE email=?', (email,)
        ).fetchone()

        print("Entered email:", email)
        print("User found:", user['email'] if user else None)
        print("Stored hash:", user['password_hash'] if user else None)
        print("Entered password hash:", hash_password(password))

        if user and user['password_hash'] == hash_password(password):
            session.permanent = True
            session['user_id'] = user['id']
            session['user_name'] = user['name']
            session['play_login_sound'] = True
            flash(f"Welcome back, {user['name']}!", 'success')
            log_activity(user['id'], 'auth', 'login', f"{user['email']} logged in")

            if user['status'] == 'inactive':
                flash('Your account has been deactivated. Please contact support.', 'error')
                return redirect(url_for('login'))

            if user['role'] == 'admin':
                return redirect(url_for('admin_panel'))

            return redirect(url_for('dashboard'))

        flash('Invalid email or password.', 'error')

    return render_template('login.html')

@app.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    reset_link = None
    email_sent = False
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        db = get_db()
        user = db.execute('SELECT * FROM users WHERE email=?', (email,)).fetchone()
        if not user:
            flash('No account found with that email address.', 'error')
        else:
            token = secrets.token_urlsafe(24)
            expires_at = (datetime.utcnow() + timedelta(minutes=30)).replace(microsecond=0).isoformat()
            db.execute('UPDATE users SET reset_token=?, reset_token_expires=? WHERE id=?', (token, expires_at, user['id']))
            db.commit()
            reset_link = url_for('reset_password', token=token, _external=True)
            email_sent = send_email_notice(email, 'Probob Password Reset', f'Use this link to reset your password: {reset_link}')
            if email_sent:
                flash('An email with instructions to reset your password has been sent to you.', 'success')
            else:
                flash('There was an error sending the reset email. Please contact support.', 'error')
    return render_template('forgot_password.html')


@app.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    db = get_db()
    user = db.execute('SELECT * FROM users WHERE reset_token=?', (token,)).fetchone()
    if not user:
        flash('Invalid or expired reset link.', 'error')
        return redirect(url_for('forgot_password'))
    if user['reset_token_expires'] and datetime.utcnow() > datetime.fromisoformat(user['reset_token_expires']):
        db.execute('UPDATE users SET reset_token=NULL, reset_token_expires=NULL WHERE id=?', (user['id'],))
        db.commit()
        flash('Reset link expired. Please request a new one.', 'error')
        return redirect(url_for('forgot_password'))
    if request.method == 'POST':
        password = request.form.get('password', '')
        confirm = request.form.get('confirm_password', '')
        if len(password) < 6:
            flash('Password must be at least 6 characters.', 'error')
        elif password != confirm:
            flash('Passwords do not match.', 'error')
        else:
            db.execute('UPDATE users SET password_hash=?, reset_token=NULL, reset_token_expires=NULL WHERE id=?', (hash_password(password), user['id']))
            db.commit()
            flash('Password updated successfully. Please log in.', 'success')
            return redirect(url_for('login'))
    return render_template('reset_password.html', token=token)


@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('index'))


@app.route('/start-project', methods=['GET', 'POST'])
@login_required
def start_project():
    db = get_db()
    user = get_current_user()
    services = db.execute('SELECT title FROM service_items ORDER BY id ASC').fetchall()
    if request.method == 'POST':
        form = {k: request.form.get(k, '').strip() for k in ['client_name', 'email', 'phone', 'company', 'service', 'budget_range', 'deadline', 'business_type', 'project_description']}
        if not form['client_name'] or not form['email'] or not form['service'] or not form['project_description']:
            flash('Please fill all required project fields.', 'error')
        else:
            db.execute(
                '''
                INSERT INTO quote_requests (user_id,client_name,email,phone,company,service,budget_range,deadline,business_type,project_description,status,source,created_at)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
                ''',
                (user['id'], form['client_name'], form['email'], form['phone'], form['company'], form['service'], form['budget_range'], form['deadline'], form['business_type'], form['project_description'], 'New', 'website', now_iso())
            )
            quote_id = db.execute('SELECT last_insert_rowid()').fetchone()[0]
            db.commit()
            create_project_from_quote(quote_id)
            add_notification(user['id'], 'Quote request submitted', f"Your request for {form['service']} has been submitted.", '/dashboard')
            log_activity(user['id'], 'quotes', 'created', f"{form['service']} quote submitted")
            session['show_feedback_prompt'] = True
            flash('Project request submitted successfully.', 'success')
            return redirect(url_for('dashboard'))
    return render_template('start_project.html', services=services, user=user)


@app.route('/book-consultation', methods=['GET', 'POST'])
@login_required
def book_consultation():
    db = get_db()
    user = get_current_user()
    services = db.execute('SELECT title FROM service_items ORDER BY id ASC').fetchall()
    
    # Realistic Booking: Get booked slots to prevent double bookings
    booked_slots = db.execute('SELECT booking_date, booking_time FROM bookings WHERE status NOT IN ("Cancelled", "Rejected")').fetchall()
    booked_list = [f"{row['booking_date']} {row['booking_time']}" for row in booked_slots]

    if request.method == 'POST':
        form = {k: request.form.get(k, '').strip() for k in ['name', 'email', 'phone', 'service_interest', 'booking_date', 'booking_time', 'meeting_mode', 'notes']}
        
        slot_key = f"{form['booking_date']} {form['booking_time']}"
        
        if not form['name'] or not form['email'] or not form['booking_date'] or not form['booking_time']:
            flash('Name, email, date, and time are required.', 'error')
        elif slot_key in booked_list:
            flash('This time slot is already booked. Please choose another.', 'error')
        else:
            db.execute(
                '''INSERT INTO bookings (user_id,name,email,phone,service_interest,booking_date,booking_time,meeting_mode,notes,status,created_at)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?)''',
                (user['id'], form['name'], form['email'], form['phone'], form['service_interest'], form['booking_date'], form['booking_time'], form['meeting_mode'], form['notes'], 'Requested', now_iso())
            )
            db.commit()
            add_notification(user['id'], 'Consultation requested', 'Your consultation request has been submitted.', '/dashboard')
            log_activity(user['id'], 'bookings', 'created', f"Consultation requested for {form['booking_date']} {form['booking_time']}")
            session['show_feedback_prompt'] = True
            flash('Consultation request submitted.', 'success')
            return redirect(url_for('dashboard'))
    return render_template('booking.html', services=services, user=user, booked_list=booked_list)


@app.route('/client/files', methods=['GET', 'POST'])
@login_required
def client_files():
    db = get_db()
    user = get_current_user()
    projects = db.execute('SELECT id,title FROM projects WHERE user_id=? ORDER BY id DESC', (user['id'],)).fetchall()
    if request.method == 'POST':
        project_id = request.form.get('project_id')
        title = request.form.get('title', '').strip() or 'Client File'
        upload = request.files.get('file')
        if not project_id or not upload or upload.filename == '':
            flash('Select a project and file.', 'error')
        elif not allowed_file(upload.filename):
            flash('Unsupported file type.', 'error')
        else:
            filename = f"{uuid.uuid4().hex}_{secure_filename(upload.filename)}"
            file_path = UPLOAD_FOLDER / filename
            upload.save(file_path)
            ext = filename.rsplit('.', 1)[1].lower()
            db.execute('INSERT INTO project_files (project_id,user_id,title,filename,file_path,file_type,uploaded_by_role,created_at) VALUES (?,?,?,?,?,?,?,?)',
                       (project_id, user['id'], title, upload.filename, f'/static/uploads/{filename}', ext, 'client', now_iso()))
            db.commit()
            add_notification(user['id'], 'File uploaded', f"{upload.filename} was uploaded successfully.", '/client/files')
            log_activity(user['id'], 'files', 'uploaded', upload.filename)
            flash('File uploaded successfully.', 'success')
            return redirect(url_for('client_files'))
    files = db.execute(
        '''SELECT pf.*, p.title AS project_title FROM project_files pf
           LEFT JOIN projects p ON pf.project_id=p.id
           WHERE pf.user_id=? ORDER BY pf.id DESC''',
        (user['id'],)
    ).fetchall()
    return render_template('client_files.html', projects=projects, files=files)


@app.route('/client/revisions', methods=['GET', 'POST'])
@login_required
def client_revisions():
    db = get_db()
    user = get_current_user()
    projects = db.execute('SELECT id,title FROM projects WHERE user_id=? ORDER BY id DESC', (user['id'],)).fetchall()
    if request.method == 'POST':
        project_id = request.form.get('project_id')
        comments = request.form.get('comments', '').strip()
        upload = request.files.get('attachment')
        attachment_path = ''
        if not project_id or not comments:
            flash('Project and revision comments are required.', 'error')
        else:
            if upload and upload.filename:
                if not allowed_file(upload.filename):
                    flash('Unsupported attachment type.', 'error')
                    return redirect(url_for('client_revisions'))
                filename = f"rev_{uuid.uuid4().hex}_{secure_filename(upload.filename)}"
                upload.save(UPLOAD_FOLDER / filename)
                attachment_path = f'/static/uploads/{filename}'
            row = db.execute('SELECT COUNT(*) FROM revision_requests WHERE project_id=?', (project_id,)).fetchone()[0]
            db.execute('INSERT INTO revision_requests (project_id,user_id,revision_no,comments,attachment_path,status,created_at) VALUES (?,?,?,?,?,?,?)',
                       (project_id, user['id'], row + 1, comments, attachment_path, 'Pending', now_iso()))
            db.commit()
            add_notification(user['id'], 'Revision submitted', 'Your revision request has been sent to the team.', '/client/revisions')
            log_activity(user['id'], 'revisions', 'created', f"Revision submitted for project #{project_id}")
            flash('Revision request submitted.', 'success')
            return redirect(url_for('client_revisions'))
    revisions = db.execute(
        '''SELECT r.*, p.title AS project_title FROM revision_requests r
           LEFT JOIN projects p ON r.project_id=p.id
           WHERE r.user_id=? ORDER BY r.id DESC''',
        (user['id'],)
    ).fetchall()
    return render_template('revisions.html', projects=projects, revisions=revisions)


def user_chart_data(user_id):
    db = get_db()
    # Monthly Bookings
    monthly_bookings = db.execute(
        """
        SELECT substr(created_at, 1, 7) AS month, COUNT(*) AS count
        FROM bookings
        WHERE user_id=?
        GROUP BY month
        ORDER BY month DESC LIMIT 6
        """, (user_id,)
    ).fetchall()[::-1]

    # Project Status
    project_status = db.execute(
        "SELECT status AS label, COUNT(*) AS value FROM projects WHERE user_id=? GROUP BY status", (user_id,)
    ).fetchall()

    # Activity Heatmap (by weekday)
    activity = db.execute(
        """
        SELECT strftime('%w', created_at) as weekday, COUNT(*) as count
        FROM activity_logs
        WHERE actor_user_id=?
        GROUP BY weekday
        """, (user_id,)
    ).fetchall()
    
    weekdays = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat']
    activity_data = [0] * 7
    for row in activity:
        activity_data[int(row['weekday'])] = row['count']

    # Top Services (overall popular services for the user to see)
    top_services = db.execute(
        "SELECT service, COUNT(*) as count FROM quote_requests GROUP BY service ORDER BY count DESC LIMIT 5"
    ).fetchall()

    return {
        'booking_labels': [r['month'] for r in monthly_bookings],
        'booking_values': [r['count'] for r in monthly_bookings],
        'status_labels': [r['label'] for r in project_status],
        'status_values': [r['value'] for r in project_status],
        'activity_labels': weekdays,
        'activity_values': activity_data,
        'top_services': [{'name': r['service'], 'count': r['count']} for r in top_services]
    }


@app.route('/dashboard/feedback', methods=['POST'])
@login_required
def submit_feedback():
    rating = int(request.form.get('rating', 5))
    message = request.form.get('message', '').strip()
    company = request.form.get('company', '').strip()
    user = get_current_user()
    
    if not message:
        flash('Please include a message with your feedback.', 'error')
        return redirect(url_for('dashboard'))
    
    db = get_db()
    db.execute(
        'INSERT INTO testimonials (client_name, company, message, rating, user_id, status) VALUES (?,?,?,?,?,?)',
        (user['name'], company, message, rating, user['id'], 'pending')
    )
    db.commit()
    
    log_activity(user['id'], 'feedback', 'submit', f"Rated {rating} stars")
    flash('Thank you for your feedback! It will be visible once approved.', 'success')
    return redirect(url_for('dashboard'))


@app.route('/dashboard')
@login_required
def dashboard():
    user = get_current_user()
    if user['role'] == 'admin':
        return redirect(url_for('admin_panel'))
    db = get_db()
    stats = {
        'quotes': db.execute('SELECT COUNT(*) FROM quote_requests WHERE user_id=?', (user['id'],)).fetchone()[0],
        'projects': db.execute('SELECT COUNT(*) FROM projects WHERE user_id=?', (user['id'],)).fetchone()[0],
        'files': db.execute('SELECT COUNT(*) FROM project_files WHERE user_id=?', (user['id'],)).fetchone()[0],
        'invoices': db.execute('SELECT COUNT(*) FROM invoices WHERE user_id=?', (user['id'],)).fetchone()[0],
    }
    recent_quotes = db.execute('SELECT * FROM quote_requests WHERE user_id=? ORDER BY id DESC LIMIT 5', (user['id'],)).fetchall()
    projects = db.execute('SELECT * FROM projects WHERE user_id=? ORDER BY id DESC LIMIT 6', (user['id'],)).fetchall()
    revisions = db.execute(
        '''SELECT r.*, p.title AS project_title FROM revision_requests r LEFT JOIN projects p ON r.project_id=p.id
           WHERE r.user_id=? ORDER BY r.id DESC LIMIT 5''',
        (user['id'],)
    ).fetchall()
    bookings = db.execute('SELECT * FROM bookings WHERE user_id=? ORDER BY id DESC LIMIT 4', (user['id'],)).fetchall()
    invoices = db.execute('SELECT i.*, p.title AS project_title FROM invoices i LEFT JOIN projects p ON i.project_id=p.id WHERE i.user_id=? ORDER BY i.id DESC LIMIT 5', (user['id'],)).fetchall()
    notifications = db.execute('SELECT * FROM notifications WHERE user_id=? ORDER BY id DESC LIMIT 6', (user['id'],)).fetchall()
    
    chart_data = user_chart_data(user['id'])
    
    return render_template('dashboard.html', user=user, stats=stats, recent_quotes=recent_quotes, projects=projects, revisions=revisions, bookings=bookings, invoices=invoices, notifications=notifications, chart_data=chart_data)


@app.route('/profile')
@login_required
def profile():
    user = get_current_user()
    db = get_db()
    bookings = db.execute('SELECT * FROM bookings WHERE user_id=? ORDER BY id DESC', (user['id'],)).fetchall()
    wishlist = db.execute(
        '''SELECT w.*, s.title, s.icon, s.description FROM wishlist w
           JOIN service_items s ON w.service_id = s.id
           WHERE w.user_id=?''', (user['id'],)
    ).fetchall()
    return render_template('profile.html', user=user, bookings=bookings, wishlist=wishlist)


@app.route('/profile/edit', methods=['GET', 'POST'])
@login_required
def profile_edit():
    user = get_current_user()
    if request.method == 'POST':
        name = request.form.get('name').strip()
        phone = request.form.get('phone').strip()
        location = request.form.get('location').strip()
        bio = request.form.get('bio').strip()
        
        db = get_db()
        
        profile_picture = user['profile_picture']
        file = request.files.get('profile_picture')
        if file and file.filename != '':
            if allowed_file(file.filename):
                filename = f"user_{user['id']}_{uuid.uuid4().hex}_{secure_filename(file.filename)}"
                file.save(UPLOAD_FOLDER / filename)
                profile_picture = f'/static/uploads/{filename}'
        
        db.execute(
            'UPDATE users SET name=?, phone=?, location=?, bio=?, profile_picture=? WHERE id=?',
            (name, phone, location, bio, profile_picture, user['id'])
        )
        db.commit()
        flash('Profile updated successfully.', 'success')
        return redirect(url_for('profile'))
        
    return render_template('profile_edit.html', user=user)


@app.route('/wishlist/toggle/<int:service_id>', methods=['POST'])
@login_required
def wishlist_toggle(service_id):
    user = get_current_user()
    db = get_db()
    existing = db.execute('SELECT id FROM wishlist WHERE user_id=? AND service_id=?', (user['id'], service_id)).fetchone()
    if existing:
        db.execute('DELETE FROM wishlist WHERE id=?', (existing['id'],))
        db.commit()
        return jsonify({'status': 'removed'})
    else:
        db.execute('INSERT INTO wishlist (user_id, service_id) VALUES (?, ?)', (user['id'], service_id))
        db.commit()
        return jsonify({'status': 'added'})



def admin_paginate(query, params=(), page=1, per_page=8, search='', search_cols=[]):
    db = get_db()
    if search and search_cols:
        search_clauses = " OR ".join([f"LOWER(CAST({col} AS TEXT)) LIKE ?" for col in search_cols])
        query = f"SELECT * FROM ({query}) AS subquery WHERE {search_clauses}"
        search_term = f"%{search.lower()}%"
        params = list(params) + [search_term] * len(search_cols)

    count_query = f"SELECT COUNT(*) FROM ({query}) AS subquery_count"
    total = db.execute(count_query, params).fetchone()[0]
    pages = max((total + per_page - 1) // per_page, 1)
    page = max(1, min(page, pages))
    offset = (page - 1) * per_page
    rows = db.execute(f"{query} LIMIT ? OFFSET ?", (*params, per_page, offset)).fetchall()
    return {
        'items': rows,
        'page': page,
        'pages': pages,
        'per_page': per_page,
        'total': total,
        'has_prev': page > 1,
        'has_next': page < pages,
        'prev_page': page - 1,
        'next_page': page + 1,
    }


def admin_overview_stats():
    db = get_db()
    revenue = db.execute("SELECT COALESCE(SUM(amount), 0) FROM payments WHERE LOWER(COALESCE(status, '')) IN ('paid','received')").fetchone()[0]
    active_projects = db.execute("SELECT COUNT(*) FROM projects WHERE status NOT IN ('Completed','Cancelled','Closed')").fetchone()[0]
    return {
        'clients': db.execute("SELECT COUNT(*) FROM users WHERE role != 'admin'").fetchone()[0],
        'quotes': db.execute('SELECT COUNT(*) FROM quote_requests').fetchone()[0],
        'bookings': db.execute('SELECT COUNT(*) FROM bookings').fetchone()[0],
        'revisions': db.execute('SELECT COUNT(*) FROM revision_requests').fetchone()[0],
        'accounts': db.execute("SELECT COUNT(*) FROM users WHERE role != 'admin'").fetchone()[0],
        'projects': db.execute('SELECT COUNT(*) FROM projects').fetchone()[0],
        'active_projects': active_projects,
        'revenue': revenue or 0,
        'files': db.execute('SELECT COUNT(*) FROM project_files').fetchone()[0],
        'contacts': db.execute('SELECT COUNT(*) FROM contacts').fetchone()[0],
        'invoices': db.execute('SELECT COUNT(*) FROM invoices').fetchone()[0],
        'payments': db.execute('SELECT COUNT(*) FROM payments').fetchone()[0],
        'pending_quotes': db.execute("SELECT COUNT(*) FROM quote_requests WHERE status IN ('New', 'Reviewing')").fetchone()[0],
    }


def admin_chart_data():
    db = get_db()
    monthly_revenue = db.execute(
        """
        SELECT substr(COALESCE(paid_at, created_at),1,7) AS month, COALESCE(SUM(amount),0) AS total
        FROM payments
        WHERE LOWER(COALESCE(status,'')) IN ('paid','received')
        GROUP BY substr(COALESCE(CASE WHEN paid_at IS NOT NULL AND paid_at != '' THEN paid_at ELSE created_at END, created_at),1,7)
        ORDER BY month DESC LIMIT 6
        """
    ).fetchall()[::-1]
    project_status = db.execute(
        "SELECT COALESCE(status,'Unknown') AS label, COUNT(*) AS value FROM projects GROUP BY COALESCE(status,'Unknown') ORDER BY value DESC LIMIT 6"
    ).fetchall()
    return {
        'client_count': db.execute("SELECT COUNT(*) FROM users WHERE role != 'admin'").fetchone()[0],
        'revenue_total': db.execute("SELECT COALESCE(SUM(amount),0) FROM payments WHERE LOWER(COALESCE(status,'')) IN ('paid','received')").fetchone()[0] or 0,
        'active_projects': db.execute("SELECT COUNT(*) FROM projects WHERE status NOT IN ('Completed','Cancelled','Closed')").fetchone()[0],
        'monthly_labels': [r['month'] for r in monthly_revenue],
        'monthly_values': [r['total'] for r in monthly_revenue],
        'project_status_labels': [r['label'] for r in project_status],
        'project_status_values': [r['value'] for r in project_status],
    }


def admin_common_context(section='dashboard'):
    return {'admin_section': section, 'admin_stats': admin_overview_stats()}


@app.route('/admin')
@admin_required
def admin_panel():
    db = get_db()
    booking_page = int(request.args.get('booking_page', 1) or 1)
    revision_page = int(request.args.get('revision_page', 1) or 1)
    account_page = int(request.args.get('account_page', 1) or 1)
    search = request.args.get('search', '').strip()
    bookings = admin_paginate(
        "SELECT b.*, u.name AS account_name FROM bookings b LEFT JOIN users u ON b.user_id=u.id ORDER BY b.id DESC",
        page=booking_page,
        per_page=6,
        search=search, search_cols=['name', 'email', 'service_interest', 'status']
    )
    revisions = admin_paginate(
        "SELECT r.*, p.title AS project_title, u.name AS client_name FROM revision_requests r LEFT JOIN projects p ON r.project_id=p.id LEFT JOIN users u ON r.user_id=u.id ORDER BY r.id DESC",
        page=revision_page,
        per_page=6,
        search=search, search_cols=['comments', 'status', 'project_title', 'client_name']
    )
    accounts = admin_paginate(
        "SELECT id, name, email, role, created_at FROM users WHERE role != 'admin' ORDER BY id DESC",
        page=account_page,
        per_page=6,
        search=search, search_cols=['name', 'email', 'role']
    )
    unpaid_invoices = db.execute("""
        SELECT i.*, u.name AS client_name, p.title AS project_title 
        FROM invoices i 
        LEFT JOIN users u ON i.user_id = u.id 
        LEFT JOIN projects p ON i.project_id = p.id
        WHERE i.status NOT IN ('Paid', 'Cancelled') 
        ORDER BY i.due_date ASC LIMIT 10
    """).fetchall()

    today_date = datetime.now().strftime('%Y-%m-%d')
    three_days_later = (datetime.now() + timedelta(days=3)).strftime('%Y-%m-%d')

    # Dashboard Metrics
    metrics = {
        'unpaid_count': db.execute("SELECT COUNT(*) FROM invoices WHERE status NOT IN ('Paid', 'Cancelled')").fetchone()[0],
        'unpaid_total': db.execute("SELECT SUM(balance_amount) FROM invoices WHERE status NOT IN ('Paid', 'Cancelled')").fetchone()[0] or 0,
        'today_quotes': db.execute("SELECT COUNT(*) FROM quote_requests WHERE created_at LIKE ?", (f"{today_date}%",)).fetchone()[0],
        'pending_contacts': db.execute("SELECT COUNT(*) FROM contacts WHERE status='new'").fetchone()[0],
        'upcoming_deadlines': db.execute("SELECT COUNT(*) FROM projects WHERE status NOT IN ('Completed', 'Cancelled') AND due_date <= ?", (three_days_later,)).fetchone()[0],
        'recent_payment': db.execute("SELECT amount FROM payments WHERE status IN ('paid', 'received') ORDER BY id DESC LIMIT 1").fetchone(),
        'recent_file': db.execute("SELECT title FROM project_files ORDER BY id DESC LIMIT 1").fetchone()
    }

    recent_quotes = db.execute("SELECT * FROM quote_requests ORDER BY id DESC LIMIT 5").fetchall()
    return render_template('admin_dashboard.html', bookings=bookings, revisions=revisions, accounts=accounts, unpaid_invoices=unpaid_invoices, recent_quotes=recent_quotes, metrics=metrics, **admin_common_context('dashboard'))


@app.route('/admin/manage/users')
@admin_required
def admin_users_page():
    page = int(request.args.get('page', 1) or 1)
    search = request.args.get('search', '').strip()
    users = admin_paginate(
        "SELECT id, name, email, role, status, created_at FROM users ORDER BY id DESC",
        page=page,
        per_page=10,
        search=search, search_cols=['name', 'email', 'role', 'status']
    )
    return render_template('admin_users.html', users=users, **admin_common_context('users'))


@app.route('/admin/users/<int:user_id>/toggle-status', methods=['POST'])
@admin_required
def admin_toggle_user_status(user_id):
    db = get_db()
    user = db.execute('SELECT * FROM users WHERE id=?', (user_id,)).fetchone()
    if not user:
        flash('User not found.', 'error')
        return redirect(url_for('admin_users_page'))
    
    if user['role'] == 'admin' and user['id'] == session.get('user_id'):
        flash('You cannot deactivate your own admin account.', 'error')
        return redirect(url_for('admin_users_page'))

    new_status = 'inactive' if user['status'] == 'active' else 'active'
    db.execute('UPDATE users SET status=? WHERE id=?', (new_status, user_id))
    db.commit()
    
    log_activity(session.get('user_id'), 'users', 'status_update', f"User {user['email']} marked as {new_status}")
    flash(f"User {user['name']} is now {new_status}.", 'success')
    return redirect(url_for('admin_users_page', page=request.args.get('page', 1), search=request.args.get('search', '')))


@app.route('/admin/users/<int:user_id>/change-role', methods=['POST'])
@admin_required
def admin_change_user_role(user_id):
    new_role = request.form.get('role')
    if new_role not in ['user', 'admin']:
        flash('Invalid role.', 'error')
        return redirect(url_for('admin_users_page'))
    
    db = get_db()
    user = db.execute('SELECT * FROM users WHERE id=?', (user_id,)).fetchone()
    if not user:
        flash('User not found.', 'error')
        return redirect(url_for('admin_users_page'))

    if user['id'] == session.get('user_id') and new_role != 'admin':
        flash('You cannot demote yourself from admin.', 'error')
        return redirect(url_for('admin_users_page'))

    db.execute('UPDATE users SET role=? WHERE id=?', (new_role, user_id))
    db.commit()
    
    log_activity(session.get('user_id'), 'users', 'role_update', f"User {user['email']} role changed to {new_role}")
    flash(f"User {user['name']} role updated to {new_role}.", 'success')
    return redirect(url_for('admin_users_page', page=request.args.get('page', 1), search=request.args.get('search', '')))


@app.route('/admin/users/<int:user_id>/delete', methods=['POST'])
@admin_required
def admin_delete_user(user_id):
    db = get_db()
    user = db.execute('SELECT * FROM users WHERE id=?', (user_id,)).fetchone()
    if not user:
        flash('User not found.', 'error')
        return redirect(url_for('admin_users_page'))

    if user['id'] == session.get('user_id'):
        flash('You cannot delete your own account.', 'error')
        return redirect(url_for('admin_users_page'))

    # Optional: Delete related data or nullify user_id in other tables
    # For now, we'll just delete the user. SQLite handles the rest if foreign keys are set, 
    # but here we should probably be careful.
    db.execute('DELETE FROM users WHERE id=?', (user_id,))
    db.commit()
    
    log_activity(session.get('user_id'), 'users', 'delete', f"User {user['email']} deleted")
    flash(f"User {user['name']} has been deleted.", 'info')
    return redirect(url_for('admin_users_page', page=request.args.get('page', 1), search=request.args.get('search', '')))


@app.route('/admin/manage/clients')
@admin_required
def admin_clients_page():
    page = int(request.args.get('page', 1) or 1)
    search = request.args.get('search', '').strip()
    
    query = """
        SELECT 
            u.id, u.name, u.email, u.created_at,
            (SELECT COUNT(*) FROM projects WHERE user_id = u.id) as total_projects,
            (SELECT COUNT(*) FROM projects WHERE user_id = u.id AND status = 'Completed') as completed_projects,
            (SELECT COUNT(*) FROM projects WHERE user_id = u.id AND status NOT IN ('Completed', 'Cancelled', 'Closed')) as active_projects,
            (SELECT COUNT(*) FROM invoices WHERE user_id = u.id) as total_invoices,
            (SELECT COALESCE(SUM(amount), 0) FROM payments WHERE user_id = u.id AND status IN ('paid', 'received')) as total_payments
        FROM users u
        WHERE u.role != 'admin'
        ORDER BY u.id DESC
    """
    
    clients = admin_paginate(
        query,
        page=page,
        per_page=10,
        search=search, search_cols=['name', 'email']
    )
    
    return render_template('admin_clients.html', clients=clients, **admin_common_context('clients'))


@app.route('/admin/manage/feedback')
@admin_required
def admin_feedback_page():
    page = int(request.args.get('page', 1) or 1)
    search = request.args.get('search', '').strip()
    rating_filter = request.args.get('rating', '')
    
    query = "SELECT * FROM testimonials WHERE 1=1"
    params = []
    
    if rating_filter:
        query += " AND rating = ?"
        params.append(rating_filter)
        
    query += " ORDER BY id DESC"
    
    feedbacks = admin_paginate(
        query,
        page=page,
        per_page=10,
        search=search, search_cols=['client_name', 'company', 'message'],
        params=params
    )
    
    return render_template('admin_feedback.html', feedbacks=feedbacks, **admin_common_context('feedback'))


@app.route('/admin/feedback/<int:feedback_id>/update', methods=['POST'])
@admin_required
def admin_update_feedback(feedback_id):
    status = request.form.get('status')
    is_featured = 1 if request.form.get('is_featured') == 'on' else 0
    
    db = get_db()
    db.execute('UPDATE testimonials SET status=?, is_featured=? WHERE id=?', (status, is_featured, feedback_id))
    db.commit()
    
    flash('Feedback updated.', 'success')
    return redirect(url_for('admin_feedback_page', page=request.args.get('page', 1), search=request.args.get('search', '')))


@app.route('/admin/feedback/<int:feedback_id>/delete', methods=['POST'])
@admin_required
def admin_delete_feedback(feedback_id):
    db = get_db()
    db.execute('DELETE FROM testimonials WHERE id=?', (feedback_id,))
    db.commit()
    flash('Feedback deleted.', 'info')
    return redirect(url_for('admin_feedback_page', page=request.args.get('page', 1), search=request.args.get('search', '')))


@app.route('/admin/quotes')
@admin_required
def admin_quotes():
    page = int(request.args.get('page', 1) or 1)
    search = request.args.get('search', '').strip()
    quotes = admin_paginate(
        "SELECT q.*, u.name AS account_name FROM quote_requests q LEFT JOIN users u ON q.user_id=u.id ORDER BY q.id DESC",
        page=page,
        per_page=8,
        search=search, search_cols=['client_name', 'email', 'company', 'service', 'project_description', 'status']
    )
    return render_template('admin_quotes.html', quotes=quotes, **admin_common_context('quotes'))


@app.route('/admin/quotes/<int:quote_id>/update', methods=['POST'])
@admin_required
def admin_update_quote(quote_id):
    status = request.form.get('status', 'Reviewing').strip()
    allowed = {'New', 'Reviewing', 'Quoted', 'Accepted', 'Rejected'}
    if status not in allowed:
        status = 'Reviewing'
    db = get_db()
    db.execute('UPDATE quote_requests SET status=? WHERE id=?', (status, quote_id))
    db.commit()
    quote = db.execute('SELECT * FROM quote_requests WHERE id=?', (quote_id,)).fetchone()
    if quote and quote['user_id']:
        add_notification(quote['user_id'], 'Quote status updated', f"Your quote request is now marked as {status}.", '/dashboard')
    if status == 'Accepted':
        create_project_from_quote(quote_id)
    flash('Quote status updated.', 'success')
    return redirect(url_for('admin_quotes', page=request.args.get('page', 1)))


@app.route('/admin/work/services')
@admin_required
def admin_services_page():
    db = get_db()
    category = request.args.get('category', '').strip()
    page = int(request.args.get('page', 1) or 1)
    search = request.args.get('search', '').strip()
    query = 'SELECT * FROM service_items'
    params = []
    if category:
        query += ' WHERE category=?'
        params.append(category)
    query += ' ORDER BY id DESC'
    services = admin_paginate(query, params, page=page, per_page=8, search=search, search_cols=['title', 'description', 'category'])
    categories = db.execute('SELECT DISTINCT category FROM service_items WHERE category IS NOT NULL').fetchall()
    return render_template('admin_services.html', services=services, categories=[r['category'] for r in categories], active_cat=category, edit_item=None, **admin_common_context('services'))


@app.route('/admin/export/<string:export_type>')
@admin_required
def admin_export_csv(export_type):
    db = get_db()
    if export_type == 'users':
        data = db.execute("SELECT id, name, email, role, created_at FROM users").fetchall()
        filename = "users_export.csv"
    elif export_type == 'projects':
        data = db.execute("SELECT id, title, service, status, progress, created_at FROM projects").fetchall()
        filename = "projects_export.csv"
    elif export_type == 'payments':
        data = db.execute("SELECT id, receipt_no, amount, status, paid_at FROM payments").fetchall()
        filename = "payments_export.csv"
    else:
        flash("Invalid export type", "error")
        return redirect(url_for('admin_panel'))

    si = StringIO()
    cw = csv.writer(si)
    if data:
        cw.writerow(data[0].keys())
        cw.writerows(data)
    
    output = BytesIO()
    output.write(si.getvalue().encode('utf-8'))
    output.seek(0)
    
    return send_file(output, mimetype='text/csv', as_attachment=True, download_name=filename)


@app.route('/admin/services/create', methods=['POST'])
@admin_required
def admin_create_service():
    get_db().execute('INSERT INTO service_items (title,description,icon,feature_1,feature_2,feature_3,feature_4,created_at) VALUES (?,?,?,?,?,?,?,?)',
                     (request.form.get('title', '').strip(), request.form.get('description', '').strip(), request.form.get('icon', '✨').strip() or '✨', request.form.get('feature_1', '').strip(), request.form.get('feature_2', '').strip(), request.form.get('feature_3', '').strip(), request.form.get('feature_4', '').strip(), now_iso()))
    get_db().commit()
    flash('Service added.', 'success')
    return redirect(url_for('admin_services_page'))


@app.route('/admin/services/<int:service_id>/edit', methods=['GET', 'POST'])
@admin_required
def admin_edit_service(service_id):
    db = get_db()
    if request.method == 'POST':
        db.execute('UPDATE service_items SET title=?,description=?,icon=?,feature_1=?,feature_2=?,feature_3=?,feature_4=? WHERE id=?',
                   (request.form.get('title', '').strip(), request.form.get('description', '').strip(), request.form.get('icon', '✨').strip() or '✨', request.form.get('feature_1', '').strip(), request.form.get('feature_2', '').strip(), request.form.get('feature_3', '').strip(), request.form.get('feature_4', '').strip(), service_id))
        db.commit()
        flash('Service updated.', 'success')
        return redirect(url_for('admin_services_page'))
    services = db.execute('SELECT * FROM service_items ORDER BY id DESC').fetchall()
    edit_item = db.execute('SELECT * FROM service_items WHERE id=?', (service_id,)).fetchone()
    return render_template('admin_services.html', services=services, edit_item=edit_item, **admin_common_context('services'))


@app.route('/admin/services/<int:service_id>/delete', methods=['POST'])
@admin_required
def admin_delete_service(service_id):
    get_db().execute('DELETE FROM service_items WHERE id=?', (service_id,))
    get_db().commit()
    flash('Service deleted.', 'info')
    return redirect(url_for('admin_services_page'))


@app.route('/admin/work/portfolio')
@admin_required
def admin_portfolio_page():
    page = int(request.args.get('page', 1) or 1)
    search = request.args.get('search', '').strip()
    items = admin_paginate('SELECT * FROM portfolio_items ORDER BY id DESC', page=page, per_page=8, search=search, search_cols=['title', 'description', 'category'])
    return render_template('admin_portfolio.html', portfolio_items=items, edit_item=None, **admin_common_context('portfolio'))


@app.route('/admin/portfolio/create', methods=['POST'])
@admin_required
def admin_create_portfolio():
    cover_image = None
    if 'image' in request.files:
        file = request.files['image']
        if file.filename != '':
            filename = f"{int(datetime.utcnow().timestamp())}_{secure_filename(file.filename)}"
            file.save(UPLOAD_FOLDER / filename)
            cover_image = filename

    get_db().execute('INSERT INTO portfolio_items (title,description,category,emoji,featured,cover_image,created_at) VALUES (?,?,?,?,?,?,?)',
                     (request.form.get('title', '').strip(), request.form.get('description', '').strip(), request.form.get('category', '').strip(), request.form.get('emoji', '🎨').strip() or '🎨', 1 if request.form.get('featured') else 0, cover_image, now_iso()))
    get_db().commit()
    flash('Portfolio item added.', 'success')
    return redirect(url_for('admin_portfolio_page'))


@app.route('/admin/portfolio/<int:item_id>/edit', methods=['GET', 'POST'])
@admin_required
def admin_edit_portfolio(item_id):
    db = get_db()
    if request.method == 'POST':
        cover_image = None
        if 'image' in request.files:
            file = request.files['image']
            if file.filename != '':
                filename = f"{int(datetime.utcnow().timestamp())}_{secure_filename(file.filename)}"
                file.save(UPLOAD_FOLDER / filename)
                cover_image = filename
                db.execute('UPDATE portfolio_items SET cover_image=? WHERE id=?', (cover_image, item_id))

        db.execute('UPDATE portfolio_items SET title=?, description=?, category=?, emoji=?, featured=? WHERE id=?',
                   (request.form.get('title', '').strip(), request.form.get('description', '').strip(), request.form.get('category', '').strip(), request.form.get('emoji', '🎨').strip() or '🎨', 1 if request.form.get('featured') else 0, item_id))
        db.commit()
        flash('Portfolio item updated.', 'success')
        return redirect(url_for('admin_portfolio_page'))
    items = db.execute('SELECT * FROM portfolio_items ORDER BY id DESC').fetchall()
    edit_item = db.execute('SELECT * FROM portfolio_items WHERE id=?', (item_id,)).fetchone()
    return render_template('admin_portfolio.html', portfolio_items=items, edit_item=edit_item, **admin_common_context('portfolio'))


@app.route('/admin/portfolio/<int:item_id>/delete', methods=['POST'])
@admin_required
def admin_delete_portfolio(item_id):
    get_db().execute('DELETE FROM portfolio_items WHERE id=?', (item_id,))
    get_db().commit()
    flash('Portfolio item deleted.', 'info')
    return redirect(url_for('admin_portfolio_page'))


@app.route('/admin/work/blog')
@admin_required
def admin_blog_page():
    page = int(request.args.get('page', 1) or 1)
    search = request.args.get('search', '').strip()
    posts = admin_paginate('SELECT * FROM blog_posts ORDER BY id DESC', page=page, per_page=8, search=search, search_cols=['title', 'excerpt', 'author', 'category'])
    return render_template('admin_blog.html', blog_posts=posts, edit_item=None, **admin_common_context('blog'))


@app.route('/admin/blog/create', methods=['POST'])
@admin_required
def admin_create_blog():
    cover_image = None
    if 'image' in request.files:
        file = request.files['image']
        if file.filename != '':
            from werkzeug.utils import secure_filename
            import os, time
            filename = str(int(time.time())) + '_' + secure_filename(file.filename)
            upload_folder = os.path.join(app.root_path, 'static', 'uploads')
            os.makedirs(upload_folder, exist_ok=True)
            file.save(os.path.join(upload_folder, filename))
            cover_image = filename

    get_db().execute('INSERT INTO blog_posts (title,excerpt,content,category,author,published_at,cover_emoji,tags,cover_image) VALUES (?,?,?,?,?,?,?,?,?)',
                     (request.form.get('title', '').strip(), request.form.get('excerpt', '').strip(), request.form.get('content', '').strip(), request.form.get('category', '').strip(), request.form.get('author', 'Probob Team').strip() or 'Probob Team', request.form.get('published_at', '').strip() or datetime.now().strftime('%Y-%m-%d'), request.form.get('cover_emoji', '📝').strip() or '📝', request.form.get('tags', '').strip(), cover_image))
    get_db().commit()
    flash('Blog post published.', 'success')
    return redirect(url_for('admin_blog_page'))


@app.route('/admin/blog/<int:post_id>/edit', methods=['GET', 'POST'])
@admin_required
def admin_edit_blog(post_id):
    db = get_db()
    if request.method == 'POST':
        cover_image = None
        if 'image' in request.files:
            file = request.files['image']
            if file.filename != '':
                from werkzeug.utils import secure_filename
                import os, time
                filename = str(int(time.time())) + '_' + secure_filename(file.filename)
                upload_folder = os.path.join(app.root_path, 'static', 'uploads')
                os.makedirs(upload_folder, exist_ok=True)
                file.save(os.path.join(upload_folder, filename))
                cover_image = filename
                db.execute('UPDATE blog_posts SET cover_image=? WHERE id=?', (cover_image, post_id))

        db.execute('UPDATE blog_posts SET title=?, excerpt=?, content=?, category=?, author=?, published_at=?, cover_emoji=?, tags=? WHERE id=?',
                   (request.form.get('title', '').strip(), request.form.get('excerpt', '').strip(), request.form.get('content', '').strip(), request.form.get('category', '').strip(), request.form.get('author', 'Probob Team').strip() or 'Probob Team', request.form.get('published_at', '').strip() or datetime.now().strftime('%Y-%m-%d'), request.form.get('cover_emoji', '📝').strip() or '📝', request.form.get('tags', '').strip(), post_id))
        db.commit()
        flash('Blog post updated.', 'success')
        return redirect(url_for('admin_blog_page'))
    posts = db.execute('SELECT * FROM blog_posts ORDER BY id DESC').fetchall()
    edit_item = db.execute('SELECT * FROM blog_posts WHERE id=?', (post_id,)).fetchone()
    return render_template('admin_blog.html', blog_posts=posts, edit_item=edit_item, **admin_common_context('blog'))


@app.route('/admin/blog/<int:post_id>/delete', methods=['POST'])
@admin_required
def admin_delete_blog(post_id):
    get_db().execute('DELETE FROM blog_posts WHERE id=?', (post_id,))
    get_db().commit()
    flash('Blog post deleted.', 'info')
    return redirect(url_for('admin_blog_page'))


@app.route('/admin/manage/projects')
@admin_required
def admin_projects_page():
    sync_started_projects_to_admin()
    db = get_db()
    page = int(request.args.get('page', 1) or 1)
    search = request.args.get('search', '').strip()
    projects = admin_paginate('SELECT p.*, u.name AS client_name, u.email AS client_email, (SELECT id FROM invoices WHERE project_id = p.id ORDER BY id DESC LIMIT 1) as latest_invoice_id FROM projects p LEFT JOIN users u ON p.user_id=u.id ORDER BY p.id DESC', page=page, per_page=8, search=search, search_cols=['title', 'service', 'status', 'client_name', 'client_email', 'designer_name'])
    
    # Get all admins for the designer dropdown
    admins = db.execute("SELECT name FROM users WHERE role='admin'").fetchall()
    
    # Calculate workload per designer
    workload = db.execute("""
        SELECT designer_name, COUNT(*) as active_projects 
        FROM projects 
        WHERE status NOT IN ('Completed', 'Cancelled') AND designer_name IS NOT NULL AND designer_name != ''
        GROUP BY designer_name
    """).fetchall()
    
    today = datetime.now().strftime('%Y-%m-%d')
    three_days_later = (datetime.now() + timedelta(days=3)).strftime('%Y-%m-%d')

    return render_template(
        'admin_projects.html', 
        projects=projects, 
        admins=admins, 
        workload=workload, 
        today=today, 
        three_days_later=three_days_later,
        **admin_common_context('projects')
    )


# @app.route('/admin/projects/create', methods=['POST'])
# @admin_required
# def admin_create_project():
#     db = get_db()
#     user_email = request.form.get('client_email', '').strip().lower()
#     user = db.execute('SELECT id FROM users WHERE email=?', (user_email,)).fetchone() if user_email else None
#     db.execute(
#         """INSERT INTO projects (user_id,title,service,brief,status,priority,budget,due_date,designer_name,progress,created_at)
#            VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
#         (user['id'] if user else None, request.form.get('title', '').strip(), request.form.get('service', '').strip(),
#          request.form.get('brief', '').strip(), request.form.get('status', 'Discovery').strip(),
#          request.form.get('priority', 'Medium').strip(), request.form.get('budget', '').strip(),
#          request.form.get('due_date', '').strip(), request.form.get('designer_name', '').strip(),
#          int(request.form.get('progress', '0') or 0), now_iso())
#     )
#     db.commit()
#     if user:
#         add_notification(user['id'], 'New project assigned', 'A new project has been added to your dashboard.', '/dashboard')
#     flash('Project created successfully.', 'success')
#     return redirect(url_for('admin_projects_page'))


@app.route('/admin/projects/<int:project_id>/update', methods=['POST'])
@admin_required
def admin_update_project(project_id):
    db = get_db()
    project = db.execute('SELECT * FROM projects WHERE id=?', (project_id,)).fetchone()
    if not project:
        flash('Project not found.', 'error')
        return redirect(url_for('admin_projects_page'))
    new_status = request.form.get('status', project['status'])
    progress = int(request.form.get('progress', project['progress']) or project['progress'])
    db.execute('UPDATE projects SET status=?, progress=?, designer_name=?, due_date=?, priority=? WHERE id=?',
               (new_status, progress, request.form.get('designer_name', project['designer_name'] or ''), request.form.get('due_date', project['due_date'] or ''), request.form.get('priority', project['priority'] or 'Medium'), project_id))
    db.execute('INSERT INTO project_status_history (project_id,old_status,new_status,note,created_at) VALUES (?,?,?,?,?)',
               (project_id, project['status'], new_status, request.form.get('note', '').strip(), now_iso()))
    db.commit()
    if project['user_id']:
        add_notification(project['user_id'], 'Project updated', f"{project['title']} is now {new_status} ({progress}% complete).", '/dashboard')
    log_activity(session.get('user_id'), 'projects', 'updated', f"{project['title']} -> {new_status} ({progress}%)")
    flash('Project updated.', 'success')
    return redirect(url_for('admin_projects_page'))


# @app.route('/admin/manage/invoices')
# @admin_required
# def admin_invoices_page():
#     db = get_db()
#     invoices = db.execute('SELECT i.*, p.title AS project_title, u.name AS client_name FROM invoices i LEFT JOIN projects p ON i.project_id=p.id LEFT JOIN users u ON i.user_id=u.id ORDER BY i.id DESC').fetchall()
#     projects = db.execute('SELECT p.id, p.title, u.name AS client_name FROM projects p LEFT JOIN users u ON p.user_id=u.id ORDER BY p.id DESC').fetchall()
#     return render_template('admin_invoices.html', invoices=invoices, projects=projects, **admin_common_context('invoices'))
@app.route('/admin/manage/invoices')
@admin_required
def admin_invoices_page():
    conn = get_db()
    page = int(request.args.get('page', 1) or 1)
    search = request.args.get('search', '').strip()

    invoices = admin_paginate("""
        SELECT invoices.*,
               projects.title AS project_title,
               users.name AS client_name,
               users.name AS user_name,
               users.email AS user_email
        FROM invoices
        LEFT JOIN projects ON invoices.project_id = projects.id
        LEFT JOIN users ON invoices.user_id = users.id
        ORDER BY invoices.created_at DESC
    """, page=page, per_page=8, search=search, search_cols=['invoice_no', 'title', 'status', 'client_name', 'user_name', 'user_email'])

    projects = conn.execute("""
        SELECT projects.id, projects.title, users.name AS client_name
        FROM projects
        LEFT JOIN users ON projects.user_id = users.id
        ORDER BY projects.id DESC
    """).fetchall()

    users = conn.execute("""
        SELECT id, name, email
        FROM users
        ORDER BY id DESC
    """).fetchall()

    today = datetime.now().strftime('%Y-%m-%d')
    three_days_later = (datetime.now() + timedelta(days=3)).strftime('%Y-%m-%d')

    return render_template(
        'admin_invoices.html',
        invoices=invoices,
        projects=projects,
        users=users,
        today=today,
        three_days_later=three_days_later,
        **admin_common_context('invoices')
    )

# @app.route('/admin/invoices/create', methods=['POST'])
# @admin_required
# def admin_create_invoice():
#     user_id = request.form.get('user_id')
#     title = request.form.get('title')
#     amount = request.form.get('amount')
#     due_date = request.form.get('due_date')
#     status = request.form.get('status', 'pending')
#     notes = request.form.get('notes', '')

#     if not user_id or not title or not amount:
#         flash('User, title and amount are required.', 'error')
#         return redirect(url_for('admin_invoices_page'))

#     amount = float(amount)

#     conn = get_db_connection()
#     conn.execute("""
#         INSERT INTO invoices (
#             user_id, title, amount, paid_amount, balance_amount,
#             due_date, status, notes, created_at
#         )
#         VALUES (?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
#     """, (
#         user_id, title, amount, 0, amount,
#         due_date, status, notes
#     ))
#     conn.commit()
#     conn.close()

#     flash('Invoice created successfully.', 'success')
#     return redirect(url_for('admin_invoices_page'))
import time  # add this at top if not already

@app.route('/admin/invoices/create', methods=['POST'])
@admin_required
def admin_create_invoice():
    user_id = request.form.get('user_id')
    project_id = request.form.get('project_id') or None
    title = request.form.get('title')
    amount = request.form.get('amount')
    due_date = request.form.get('due_date')
    status = request.form.get('status', 'Pending')
    notes = request.form.get('notes', '')

    if not user_id or not amount:
        flash('User and amount are required.', 'error')
        return redirect(url_for('admin_invoices_page'))

    amount = float(amount)

    conn = get_db()

    invoice_no = f"INV-{int(time.time())}"

    conn.execute("""
        INSERT INTO invoices (
            invoice_no, user_id, project_id, title, amount,
            paid_amount, balance_amount, due_date, status, notes, created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
    """, (
        invoice_no, user_id, project_id, title, amount,
        0, amount, due_date, status, notes
    ))

    conn.commit()

    flash('Invoice created successfully.', 'success')
    return redirect(url_for('admin_invoices_page'))

@app.route('/admin/invoices/<int:invoice_id>/update', methods=['POST'])
@admin_required
def admin_update_invoice(invoice_id):
    status = request.form.get('status', 'Paid')
    db = get_db()
    inv = db.execute('SELECT * FROM invoices WHERE id=?', (invoice_id,)).fetchone()
    if not inv:
        flash('Invoice not found.', 'error')
        return redirect(url_for('admin_invoices_page'))

    old_status = inv['status']
    db.execute('UPDATE invoices SET status=?, due_date=?, notes=? WHERE id=?', (status, request.form.get('due_date', inv['due_date']), request.form.get('notes', inv['notes']), invoice_id))
    
    # Auto-create payment if marked as Paid and wasn't Paid before
    if status == 'Paid' and old_status != 'Paid':
        # Check if a payment already exists for this invoice that covers the amount
        existing_payment = db.execute("SELECT id FROM payments WHERE invoice_id=? AND status IN ('paid', 'received')", (invoice_id,)).fetchone()
        if not existing_payment:
            receipt_no = f"AUTO-{int(time.time())}-{uuid.uuid4().hex[:4].upper()}"
            amount = parse_money_to_int(inv['amount'])
            db.execute(
                '''INSERT INTO payments (receipt_no, user_id, project_id, invoice_id, name, email, service, project, amount, currency, status, gateway_status, date_str, paid_at, created_at, notes)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)''',
                (receipt_no, inv['user_id'], inv['project_id'], invoice_id, 'System Auto', '', 'Invoice Payment', inv['title'], amount, 'INR', 'paid', 'paid', now_iso()[:10], now_iso(), now_iso(), f"Auto-generated for Invoice {inv['invoice_no']}")
            )
            sync_invoice_balance(db, invoice_id)

    db.commit()
    if inv['user_id']:
        add_notification(inv['user_id'], 'Invoice updated', f"Invoice {inv['invoice_no']} is now {status}.", '/dashboard')
    log_activity(session.get('user_id'), 'invoices', 'updated', f"Invoice #{invoice_id} marked {status}")
    flash('Invoice updated.', 'success')
    return redirect(url_for('admin_invoices_page'))


@app.route('/admin/manage/billing')
@admin_required
def admin_billing_page():
    db = get_db()
    page = int(request.args.get('page', 1) or 1)
    search = request.args.get('search', '').strip()
    payments = admin_paginate("""
        SELECT p.*, i.invoice_no, i.title AS invoice_title 
        FROM payments p 
        LEFT JOIN invoices i ON p.invoice_id = i.id 
        ORDER BY COALESCE(p.created_at, p.date_str) DESC, p.id DESC
    """, page=page, per_page=8, search=search, search_cols=['receipt_no', 'name', 'email', 'project', 'service', 'p.status', 'invoice_no', 'invoice_title'])
    invoices = db.execute("SELECT id, invoice_no, title, amount, balance_amount FROM invoices WHERE status != 'Paid' ORDER BY id DESC").fetchall()
    return render_template('admin_billing.html', payments=payments, invoices=invoices, **admin_common_context('billing'))


@app.route('/admin/payments/create', methods=['POST'])
@admin_required
def admin_create_payment():
    db = get_db()
    name = request.form.get('name', '').strip()
    email = request.form.get('email', '').strip()
    phone = request.form.get('phone', '').strip()
    service = request.form.get('service', '').strip()
    project = request.form.get('project', '').strip()
    amount_raw = request.form.get('amount', '0').strip()
    date_str = request.form.get('date_str', '').strip() or datetime.now().strftime('%Y-%m-%d')
    status = request.form.get('status', 'created').strip().lower()
    allowed = {'created', 'paid', 'received', 'failed', 'refunded'}
    if status not in allowed:
        status = 'created'
    try:
        amount = int(float(amount_raw))
    except (TypeError, ValueError):
        flash('Enter a valid bill amount.', 'danger')
        return redirect(url_for('admin_billing_page'))
    if not name or not service:
        flash('Client name and service are required.', 'danger')
        return redirect(url_for('admin_billing_page'))
    receipt_no = f"BILL-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:5].upper()}"
    paid_at = now_iso() if status in {'paid', 'received'} else ''
    invoice_id = request.form.get('invoice_id') or None
    user_id = None
    project_id = None
    if invoice_id:
        inv = db.execute('SELECT user_id, project_id FROM invoices WHERE id=?', (invoice_id,)).fetchone()
        if inv:
            user_id = inv['user_id']
            project_id = inv['project_id']

    db.execute(
        '''INSERT INTO payments (receipt_no,user_id,project_id,invoice_id,name,email,phone,service,project,amount,currency,status,gateway_status,date_str,paid_at,created_at)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)''',
        (receipt_no, user_id, project_id, invoice_id, name, email, phone, service, project, amount, 'INR', status, status, date_str, paid_at, now_iso())
    )
    if invoice_id:
        sync_invoice_balance(db, invoice_id)
    db.commit()
    flash('New bill recorded successfully.', 'success')
    return redirect(url_for('admin_billing_page'))


@app.route('/admin/payments/<int:payment_id>/update', methods=['POST'])
@admin_required
def admin_update_payment(payment_id):
    status = request.form.get('status', 'paid').strip().lower()
    allowed = {'created', 'paid', 'received', 'failed', 'refunded'}
    if status not in allowed:
        status = 'created'
    db = get_db()
    payment = db.execute('SELECT * FROM payments WHERE id=?', (payment_id,)).fetchone()
    existing_paid_at = payment['paid_at'] if payment and payment['paid_at'] else ''
    paid_at = now_iso() if status in {'paid', 'received'} and not existing_paid_at else existing_paid_at
    if status not in {'paid', 'received'}:
        paid_at = existing_paid_at
    db.execute('UPDATE payments SET status=?, gateway_status=?, paid_at=? WHERE id=?', (status, status, paid_at, payment_id))
    if payment and payment['invoice_id']:
        sync_invoice_balance(db, payment['invoice_id'])
    db.commit()
    flash('Billing record updated.', 'success')
    return redirect(url_for('admin_billing_page'))


@app.route('/admin/assets')
@admin_required
def admin_assets_page():
    page = int(request.args.get('page', 1) or 1)
    search = request.args.get('search', '').strip()
    files = admin_paginate('SELECT pf.*, p.title AS project_title, u.name AS client_name FROM project_files pf LEFT JOIN projects p ON pf.project_id=p.id LEFT JOIN users u ON pf.user_id=u.id ORDER BY pf.id DESC', page=page, per_page=8, search=search, search_cols=['title', 'filename', 'project_title', 'client_name'])
    return render_template('admin_assets.html', files=files, **admin_common_context('assets'))


@app.route('/admin/contact')
@admin_required
def admin_contact_page():
    page = int(request.args.get('page', 1) or 1)
    search = request.args.get('search', '').strip()
    contacts = admin_paginate('SELECT * FROM contacts ORDER BY id DESC', page=page, per_page=8, search=search, search_cols=['name', 'email', 'subject', 'message'])
    return render_template('admin_contact.html', contacts=contacts, **admin_common_context('contact'))


@app.route('/admin/contacts/<int:contact_id>/update', methods=['POST'])
@admin_required
def admin_update_contact(contact_id):
    status = request.form.get('status', 'reviewing').strip().lower()
    db = get_db()
    db.execute('UPDATE contacts SET status=? WHERE id=?', (status, contact_id))
    db.commit()
    flash('Contact status updated.', 'success')
    return redirect(url_for('admin_contact_page'))


@app.route('/admin/analytics')
@admin_required
def admin_analytics_page():
    return render_template('admin_analytics.html', chart_data=admin_chart_data(), **admin_common_context('analytics'))


@app.route('/admin/bookings/<int:booking_id>/update', methods=['POST'])
@admin_required
def admin_update_booking(booking_id):
    status = request.form.get('status', 'Confirmed')
    db = get_db()
    booking = db.execute('SELECT * FROM bookings WHERE id=?', (booking_id,)).fetchone()
    db.execute('UPDATE bookings SET status=? WHERE id=?', (status, booking_id))
    db.commit()
    if booking and booking['user_id']:
        add_notification(booking['user_id'], 'Consultation updated', f"Your consultation request is now {status}.", '/dashboard')
    log_activity(session.get('user_id'), 'bookings', 'updated', f"Booking #{booking_id} marked {status}")
    flash('Booking updated.', 'success')
    return redirect(url_for('admin_view_dates'))


@app.route('/admin/revisions/<int:revision_id>/update', methods=['POST'])
@admin_required
def admin_update_revision(revision_id):
    status = request.form.get('status', 'Resolved')
    db = get_db()
    rev = db.execute('SELECT * FROM revision_requests WHERE id=?', (revision_id,)).fetchone()
    db.execute('UPDATE revision_requests SET status=? WHERE id=?', (status, revision_id))
    db.commit()
    if rev and rev['user_id']:
        add_notification(rev['user_id'], 'Revision updated', f"Your revision request is now {status}.", '/dashboard')
    log_activity(session.get('user_id'), 'revisions', 'updated', f"Revision #{revision_id} marked {status}")
    flash('Revision updated.', 'success')
    return redirect(url_for('admin_panel', booking_page=request.args.get('booking_page', 1), revision_page=request.args.get('revision_page', 1), account_page=request.args.get('account_page', 1)))


@app.route('/payment/create-order', methods=['POST'])
def create_payment_order():
    db = get_db()
    invoice_id_raw = request.form.get('invoice_id', '').strip()
    invoice = None
    user = get_current_user()
    if invoice_id_raw:
        invoice = db.execute(
            "SELECT i.*, p.title AS project_title, p.service AS project_service, u.name AS client_name, u.email AS client_email, u.id AS invoice_user_id FROM invoices i LEFT JOIN projects p ON i.project_id=p.id LEFT JOIN users u ON i.user_id=u.id WHERE i.id=?",
            (invoice_id_raw,)
        ).fetchone()
        if not invoice:
            flash('Invoice not found.', 'error')
            return redirect(url_for('dashboard' if user else 'services'))
        if user and user['role'] != 'admin' and invoice['invoice_user_id'] != user['id']:
            flash('You are not allowed to pay this invoice.', 'error')
            return redirect(url_for('dashboard'))
        name = (user['name'] if user else invoice['client_name']) or request.form.get('name', '').strip() or 'Client'
        email = (user['email'] if user else invoice['client_email']) or request.form.get('email', '').strip()
        phone = request.form.get('phone', '').strip()
        service = invoice['project_service'] or request.form.get('service', '').strip() or 'Design Service'
        project = invoice['project_title'] or invoice['title'] or request.form.get('project', '').strip()
        amount = parse_money_to_int(invoice['balance_amount'] if invoice['balance_amount'] not in (None, '') else invoice['amount'])
        user_id = invoice['invoice_user_id']
        project_id = invoice['project_id']
    else:
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip()
        phone = request.form.get('phone', '').strip()
        service = request.form.get('service', '').strip()
        project = request.form.get('project', '').strip()
        amount = parse_money_to_int(request.form.get('amount'), 0)
        user_id = user['id'] if user else None
        project_id = request.form.get('project_id') or None
    if not all([name, email, service]) or amount <= 0:
        flash('Please fill all required payment fields.', 'error')
        return redirect(url_for('dashboard' if user else 'services'))
    receipt_no = f"PB-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"
    date_str = datetime.now().strftime('%d %B %Y, %I:%M %p')
    razorpay_order_id = ''
    gateway_status = 'created'
    if razorpay_client:
        order = razorpay_client.order.create({
            'amount': amount * 100,
            'currency': 'INR',
            'receipt': receipt_no,
            'notes': {'invoice_id': str(invoice['id']) if invoice else '', 'project': project or '', 'service': service or ''}
        })
        razorpay_order_id = order['id']
    else:
        gateway_status = 'manual_pending'
    db.execute(
        '''INSERT INTO payments (receipt_no,user_id,project_id,invoice_id,name,email,phone,service,project,amount,currency,razorpay_order_id,status,gateway_status,date_str,created_at,notes)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)''',
        (receipt_no, user_id, project_id, invoice['id'] if invoice else None, name, email, phone, service, project, amount, 'INR', razorpay_order_id, 'created', gateway_status, date_str, now_iso(), f"Invoice payment" if invoice else None)
    )
    db.commit()
    return render_template('payment.html', order={'name': name, 'email': email, 'phone': phone, 'service': service, 'project': project, 'amount': amount, 'receipt_no': receipt_no, 'razorpay_order_id': razorpay_order_id, 'currency': 'INR', 'razorpay_key_id': RAZORPAY_KEY_ID, 'invoice_id': invoice['id'] if invoice else '', 'gateway_enabled': bool(razorpay_client)})


@app.route('/payment/verify', methods=['POST'])
def verify_payment():
    data = request.get_json(force=True, silent=True) or {}
    order_id = data.get('razorpay_order_id', '')
    payment_id = data.get('razorpay_payment_id', '') or f"manual_{uuid.uuid4().hex[:8]}"
    signature = data.get('razorpay_signature', '')
    receipt_no = data.get('receipt_no', '')
    utr_number = data.get('utr_number', '').strip()
    db = get_db()

    if order_id:
        payment = db.execute('SELECT * FROM payments WHERE razorpay_order_id=?', (order_id,)).fetchone()
    elif receipt_no:
        payment = db.execute('SELECT * FROM payments WHERE receipt_no=?', (receipt_no,)).fetchone()
    else:
        payment = None

    if not payment:
        return jsonify({'success': False, 'message': 'Payment record not found.'}), 404

    if order_id and razorpay_client and signature:
        try:
            razorpay_client.utility.verify_payment_signature({
                'razorpay_order_id': order_id,
                'razorpay_payment_id': payment_id,
                'razorpay_signature': signature
            })
        except Exception:
            db.execute('UPDATE payments SET status=?, gateway_status=?, failure_reason=? WHERE id=?', ('failed', 'verification_failed', 'Signature verification failed', payment['id']))
            db.commit()
            return jsonify({'success': False, 'message': 'Payment signature verification failed.'}), 400

    mark_payment_success(db, payment, payment_id, signature=signature, gateway_status='paid', payment_method='Razorpay' if order_id else 'Manual UPI')
    
    if not order_id and receipt_no and utr_number:
        # Save the authenticated UTR number submitted via the manual check
        existing_notes = payment['notes'] or ''
        new_notes = (existing_notes + f"\nVerified UTR: {utr_number}").strip()
        db.execute("UPDATE payments SET notes=? WHERE id=?", (new_notes, payment['id']))

    db.commit()
    updated_payment = db.execute('SELECT * FROM payments WHERE id=?', (payment['id'],)).fetchone()
    return jsonify({'success': True, 'receipt_no': updated_payment['receipt_no']})


@app.route('/payment/webhook', methods=['POST'])
def razorpay_webhook():
    payload = request.get_data(as_text=True) or ''
    signature = request.headers.get('X-Razorpay-Signature', '')
    if RAZORPAY_WEBHOOK_SECRET:
        expected = hmac.new(RAZORPAY_WEBHOOK_SECRET.encode(), payload.encode(), hashlib.sha256).hexdigest()
        # fallback to SDK verification when available
        if razorpay_client:
            try:
                razorpay_client.utility.verify_webhook_signature(payload, signature, RAZORPAY_WEBHOOK_SECRET)
            except Exception:
                return jsonify({'success': False, 'message': 'Invalid webhook signature'}), 400
        elif expected != signature:
            return jsonify({'success': False, 'message': 'Invalid webhook signature'}), 400
    data = request.get_json(silent=True) or {}
    event = data.get('event', '')
    payload_obj = data.get('payload', {})
    payment_entity = ((payload_obj.get('payment') or {}).get('entity')) or {}
    order_id = payment_entity.get('order_id', '')
    payment_id = payment_entity.get('id', '')
    event_id = data.get('created_at') or data.get('id') or now_iso()
    db = get_db()
    payment = db.execute('SELECT * FROM payments WHERE razorpay_order_id=?', (order_id,)).fetchone() if order_id else None
    if payment:
        if event == 'payment.captured':
            mark_payment_success(db, payment, payment_id or payment['razorpay_payment_id'] or f"webhook_{uuid.uuid4().hex[:8]}", signature=signature, gateway_status='captured', payment_method='Razorpay', webhook_event_id=str(event_id), webhook_payload=payload)
        elif event == 'payment.failed':
            reason = payment_entity.get('error_description') or payment_entity.get('error_reason') or 'Payment failed'
            db.execute('UPDATE payments SET status=?, gateway_status=?, failure_reason=?, webhook_event_id=?, webhook_payload=? WHERE id=?', ('failed', 'failed', reason, str(event_id), payload, payment['id']))
        elif event == 'refund.processed':
            db.execute('UPDATE payments SET status=?, gateway_status=?, webhook_event_id=?, webhook_payload=? WHERE id=?', ('refunded', 'refunded', str(event_id), payload, payment['id']))
            if payment['invoice_id']:
                sync_invoice_balance(db, payment['invoice_id'])
        db.commit()
    return jsonify({'success': True})


@app.route('/receipt/<receipt_no>')
def view_receipt(receipt_no):
    payment = get_db().execute('SELECT * FROM payments WHERE receipt_no=?', (receipt_no,)).fetchone()
    if not payment:
        flash('Receipt not found.', 'error')
        return redirect(url_for('index'))
    receipt = dict(payment)
    receipt['date'] = receipt.get('date_str') or receipt.get('paid_at')
    return render_template('receipt.html', receipt=receipt)


@app.route('/notifications')
@login_required
def notifications_page():
    user = get_current_user()
    notifications = get_db().execute('SELECT * FROM notifications WHERE user_id=? ORDER BY id DESC', (user['id'],)).fetchall()
    return render_template('notifications.html', notifications=notifications)


@app.route('/notifications/<int:notification_id>/open')
@login_required
def open_notification(notification_id):
    user = get_current_user()
    db = get_db()
    notification = db.execute('SELECT * FROM notifications WHERE id=? AND user_id=?', (notification_id, user['id'])).fetchone()
    if notification:
        db.execute('UPDATE notifications SET is_read=1 WHERE id=?', (notification_id,))
        db.commit()
        if notification['link']:
            return redirect(notification['link'])
    return redirect(url_for('notifications_page'))


@app.route('/notifications/read-all', methods=['POST'])
@login_required
def notifications_read_all():
    user = get_current_user()
    db = get_db()
    db.execute('UPDATE notifications SET is_read=1 WHERE user_id=?', (user['id'],))
    db.commit()
    flash('All notifications marked as read.', 'success')
    return redirect(url_for('notifications_page'))


@app.route('/invoice/<int:invoice_id>/download')
@login_required
def download_invoice_pdf(invoice_id):
    db = get_db()
    invoice = db.execute("SELECT i.*, p.title AS project_title, p.service AS project_service, u.name AS client_name, u.email AS client_email FROM invoices i LEFT JOIN projects p ON i.project_id=p.id LEFT JOIN users u ON i.user_id=u.id WHERE i.id=?", (invoice_id,)).fetchone()
    user = get_current_user()
    if not invoice:
        flash('Invoice not found.', 'error')
        return redirect(url_for('admin_invoices_page') if user['role'] == 'admin' else url_for('dashboard'))
    if user['role'] != 'admin' and invoice['user_id'] != user['id']:
        flash('You are not allowed to access that invoice.', 'error')
        return redirect(url_for('dashboard'))

    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_font('Helvetica', 'B', 18)
    pdf.cell(0, 12, 'Probob Design Studio', ln=1)
    pdf.set_font('Helvetica', '', 11)
    pdf.cell(0, 8, 'Ahmedabad | Branding | Packaging | Web | Social Media', ln=1)
    pdf.ln(5)
    pdf.set_font('Helvetica', 'B', 14)
    pdf.cell(0, 10, f"Invoice {invoice['invoice_no']}", ln=1)
    pdf.set_font('Helvetica', '', 11)
    rows = [
        ('Client', invoice['client_name'] or 'Client'),
        ('Email', invoice['client_email'] or '-'),
        ('Project', invoice['project_title'] or invoice['title'] or '-'),
        ('Service', invoice['project_service'] or '-'),
        ('Amount', f"INR {invoice['amount']}"),
        ('Status', invoice['status'] or 'Pending'),
        ('Due Date', invoice['due_date'] or '-'),
        ('Created', (invoice['created_at'] or '')[:10] or '-'),
    ]
    for label, value in rows:
        pdf.set_font('Helvetica', 'B', 11)
        pdf.write(8, f'{label}: ')
        pdf.set_font('Helvetica', '', 11)
        pdf.write(8, f"{str(value)}\n")
    pdf.ln(4)
    pdf.set_font('Helvetica', 'B', 12)
    pdf.cell(0, 8, 'Notes', ln=1)
    pdf.set_font('Helvetica', '', 11)
    pdf.multi_cell(0, 8, invoice['notes'] or 'Thank you for choosing Probob Design Studio.')
    pdf.ln(6)
    pdf.multi_cell(0, 8, 'This is a system-generated invoice summary for project tracking and payment follow-up.')
    pdf_bytes = pdf.output(dest='S')
    if isinstance(pdf_bytes, str):
        pdf_bytes = pdf_bytes.encode('latin-1')
    return send_file(BytesIO(pdf_bytes), mimetype='application/pdf', as_attachment=True, download_name=f"{invoice['invoice_no']}.pdf")


@app.route('/admin/activity')
@admin_required
def admin_activity_page():
    page = int(request.args.get('page', 1) or 1)
    search = request.args.get('search', '').strip()
    logs = admin_paginate("SELECT a.*, u.name AS actor_name, u.email AS actor_email FROM activity_logs a LEFT JOIN users u ON a.actor_user_id=u.id ORDER BY a.id DESC", page=page, per_page=20, search=search, search_cols=['area', 'action', 'details', 'actor_name', 'actor_email'])
    return render_template('admin_activity.html', logs=logs, **admin_common_context('activity'))


@app.route('/api/portfolio')
def api_portfolio():
    rows = [dict(r) for r in get_db().execute('SELECT * FROM portfolio_items ORDER BY featured DESC, id DESC').fetchall()]
    return jsonify(rows)


@app.route('/api/testimonials')
def api_testimonials():
    rows = [dict(r) for r in get_db().execute('SELECT * FROM testimonials ORDER BY id DESC').fetchall()]
    return jsonify(rows)


@app.route('/api/stats')
def api_stats():
    db = get_db()
    return jsonify({
        'quotes': db.execute('SELECT COUNT(*) FROM quote_requests').fetchone()[0],
        'projects': db.execute('SELECT COUNT(*) FROM projects').fetchone()[0],
        'bookings': db.execute('SELECT COUNT(*) FROM bookings').fetchone()[0],
        'files': db.execute('SELECT COUNT(*) FROM project_files').fetchone()[0],
    })
#check#
@app.route('/api/portfolio-items')
def api_portfolio_items():
    db = get_db()
    items = db.execute('SELECT * FROM portfolio_items ORDER BY featured DESC, id DESC').fetchall()
    return jsonify([dict(item) for item in items])


@app.route('/api/client-accounts')
@admin_required
def api_client_accounts():
    db = get_db()
    clients = db.execute("""
        SELECT id, name, email, role, created_at
        FROM users
        WHERE role != 'admin'
        ORDER BY id DESC
    """).fetchall()
    return jsonify([dict(client) for client in clients])


@app.route('/api/invoices')
@admin_required
def api_invoices():
    db = get_db()
    invoices = db.execute("""
        SELECT i.*, p.title AS project_title, u.name AS client_name
        FROM invoices i
        LEFT JOIN projects p ON i.project_id = p.id
        LEFT JOIN users u ON i.user_id = u.id
        ORDER BY i.id DESC
    """).fetchall()
    return jsonify([dict(invoice) for invoice in invoices])


@app.route('/api/dashboard-stats')
@admin_required
def api_dashboard_stats():
    db = get_db()
    total_clients = db.execute("SELECT COUNT(*) AS count FROM users WHERE role != 'admin'").fetchone()['count']
    total_projects = db.execute('SELECT COUNT(*) AS count FROM projects').fetchone()['count']
    total_invoices = db.execute('SELECT COUNT(*) AS count FROM invoices').fetchone()['count']
    total_quotes = db.execute('SELECT COUNT(*) AS count FROM quote_requests').fetchone()['count']

    return jsonify({
        'total_clients': total_clients,
        'total_projects': total_projects,
        'total_invoices': total_invoices,
        'total_quotes': total_quotes
    })


@app.route('/admin/view-dates')
@admin_required
def admin_view_dates():
    db = get_db()
    month = request.args.get('month', type=int)
    year = request.args.get('year', type=int)
    today = datetime.today()
    if not month: month = today.month
    if not year: year = today.year

    # Projects Map
    projects = db.execute("SELECT id, title, due_date, status FROM projects WHERE due_date IS NOT NULL AND due_date != ''").fetchall()
    project_map = {}
    for p in projects:
        try:
            dt = datetime.strptime(p['due_date'], '%Y-%m-%d')
            if dt.month == month and dt.year == year:
                day = dt.day
                if day not in project_map: project_map[day] = []
                project_map[day].append({'type': 'project', 'id': p['id'], 'title': p['title'], 'status': p['status']})
        except ValueError: continue

    # Bookings Map
    bookings = db.execute("SELECT id, name, booking_date, booking_time, status, service_interest FROM bookings WHERE booking_date IS NOT NULL AND booking_date != ''").fetchall()
    booking_map = {}
    for b in bookings:
        try:
            dt = datetime.strptime(b['booking_date'], '%Y-%m-%d')
            if dt.month == month and dt.year == year:
                day = dt.day
                if day not in booking_map: booking_map[day] = []
                booking_map[day].append({'type': 'booking', 'id': b['id'], 'title': f"{b['name']} ({b['booking_time']})", 'status': b['status'], 'service': b['service_interest']})
        except ValueError: continue

    # Upcoming & Past Consultations
    upcoming_meetings = db.execute("SELECT * FROM bookings WHERE booking_date >= ? AND status NOT IN ('Cancelled', 'Completed') ORDER BY booking_date ASC, booking_time ASC", (today.strftime('%Y-%m-%d'),)).fetchall()
    past_meetings = db.execute("SELECT * FROM bookings WHERE booking_date < ? OR status IN ('Cancelled', 'Completed') ORDER BY booking_date DESC LIMIT 10", (today.strftime('%Y-%m-%d'),)).fetchall()

    cal = calendar.monthcalendar(year, month)
    month_name = calendar.month_name[month]
    prev_month, prev_year = (month-1, year) if month > 1 else (12, year-1)
    next_month, next_year = (month+1, year) if month < 12 else (1, year+1)

    return render_template(
        'admin_view_dates.html',
        cal=cal, month=month, year=year, month_name=month_name,
        project_map=project_map, booking_map=booking_map,
        upcoming_meetings=upcoming_meetings, past_meetings=past_meetings,
        prev_month=prev_month, prev_year=prev_year,
        next_month=next_month, next_year=next_year,
        today=today,
        **admin_common_context('view_dates')
    )




with app.app_context():
    init_db()




if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)