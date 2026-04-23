import re

with open('app.py', 'r', encoding='utf-8') as f:
    code = f.read()

# 1. Update admin_paginate definition
old_def = """def admin_paginate(query, params=(), page=1, per_page=8):
    db = get_db()
    count_query = f"SELECT COUNT(*) FROM ({query}) AS subquery"
    total = db.execute(count_query, params).fetchone()[0]
    pages = max((total + per_page - 1) // per_page, 1)
    page = max(1, min(page, pages))
    offset = (page - 1) * per_page
    rows = db.execute(f"{query} LIMIT ? OFFSET ?", (*params, per_page, offset)).fetchall()"""
new_def = """def admin_paginate(query, params=(), page=1, per_page=8, search='', search_cols=[]):
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
    rows = db.execute(f"{query} LIMIT ? OFFSET ?", (*params, per_page, offset)).fetchall()"""
code = code.replace(old_def, new_def)

# 2. Update endpoints to extract search and pass it
# admin_panel
code = code.replace(
"""    booking_page = int(request.args.get('booking_page', 1) or 1)
    revision_page = int(request.args.get('revision_page', 1) or 1)
    account_page = int(request.args.get('account_page', 1) or 1)""",
"""    booking_page = int(request.args.get('booking_page', 1) or 1)
    revision_page = int(request.args.get('revision_page', 1) or 1)
    account_page = int(request.args.get('account_page', 1) or 1)
    search = request.args.get('search', '').strip()"""
)
code = code.replace(
"""        page=booking_page,
        per_page=6,
    )""",
"""        page=booking_page,
        per_page=6,
        search=search, search_cols=['name', 'email', 'service_interest', 'status']
    )"""
)
code = code.replace(
"""        page=revision_page,
        per_page=6,
    )""",
"""        page=revision_page,
        per_page=6,
        search=search, search_cols=['comments', 'status', 'project_title', 'client_name']
    )"""
)
code = code.replace(
"""        page=account_page,
        per_page=6,
    )""",
"""        page=account_page,
        per_page=6,
        search=search, search_cols=['name', 'email', 'role']
    )"""
)

# admin_quotes
code = code.replace(
"""@app.route('/admin/quotes')
@admin_required
def admin_quotes():
    page = int(request.args.get('page', 1) or 1)
    quotes = admin_paginate(
        "SELECT q.*, u.name AS account_name FROM quote_requests q LEFT JOIN users u ON q.user_id=u.id ORDER BY q.id DESC",
        page=page,
        per_page=8,
    )""",
"""@app.route('/admin/quotes')
@admin_required
def admin_quotes():
    page = int(request.args.get('page', 1) or 1)
    search = request.args.get('search', '').strip()
    quotes = admin_paginate(
        "SELECT q.*, u.name AS account_name FROM quote_requests q LEFT JOIN users u ON q.user_id=u.id ORDER BY q.id DESC",
        page=page,
        per_page=8,
        search=search, search_cols=['client_name', 'email', 'company', 'service', 'project_description', 'status']
    )"""
)

# admin_services_page
code = code.replace(
"""    category = request.args.get('category', '').strip()
    page = int(request.args.get('page', 1) or 1)
    query = 'SELECT * FROM service_items'""",
"""    category = request.args.get('category', '').strip()
    page = int(request.args.get('page', 1) or 1)
    search = request.args.get('search', '').strip()
    query = 'SELECT * FROM service_items'"""
)
code = code.replace(
"""    services = admin_paginate(query, params, page=page, per_page=8)""",
"""    services = admin_paginate(query, params, page=page, per_page=8, search=search, search_cols=['title', 'description', 'category'])"""
)

# admin_portfolio_page
code = code.replace(
"""@app.route('/admin/work/portfolio')
@admin_required
def admin_portfolio_page():
    page = int(request.args.get('page', 1) or 1)
    items = admin_paginate('SELECT * FROM portfolio_items ORDER BY id DESC', page=page, per_page=8)""",
"""@app.route('/admin/work/portfolio')
@admin_required
def admin_portfolio_page():
    page = int(request.args.get('page', 1) or 1)
    search = request.args.get('search', '').strip()
    items = admin_paginate('SELECT * FROM portfolio_items ORDER BY id DESC', page=page, per_page=8, search=search, search_cols=['title', 'description', 'category'])"""
)

# admin_blog_page
code = code.replace(
"""@app.route('/admin/work/blog')
@admin_required
def admin_blog_page():
    page = int(request.args.get('page', 1) or 1)
    posts = admin_paginate('SELECT * FROM blog_posts ORDER BY id DESC', page=page, per_page=8)""",
"""@app.route('/admin/work/blog')
@admin_required
def admin_blog_page():
    page = int(request.args.get('page', 1) or 1)
    search = request.args.get('search', '').strip()
    posts = admin_paginate('SELECT * FROM blog_posts ORDER BY id DESC', page=page, per_page=8, search=search, search_cols=['title', 'excerpt', 'author', 'category'])"""
)

# admin_projects_page
code = code.replace(
"""@app.route('/admin/manage/projects')
@admin_required
def admin_projects_page():
    sync_started_projects_to_admin()
    page = int(request.args.get('page', 1) or 1)
    projects = admin_paginate('SELECT p.*, u.name AS client_name, u.email AS client_email FROM projects p LEFT JOIN users u ON p.user_id=u.id ORDER BY p.id DESC', page=page, per_page=8)""",
"""@app.route('/admin/manage/projects')
@admin_required
def admin_projects_page():
    sync_started_projects_to_admin()
    page = int(request.args.get('page', 1) or 1)
    search = request.args.get('search', '').strip()
    projects = admin_paginate('SELECT p.*, u.name AS client_name, u.email AS client_email FROM projects p LEFT JOIN users u ON p.user_id=u.id ORDER BY p.id DESC', page=page, per_page=8, search=search, search_cols=['title', 'service', 'status', 'client_name', 'client_email'])"""
)

# admin_invoices_page
code = code.replace(
"""@app.route('/admin/manage/invoices')
@admin_required
def admin_invoices_page():
    conn = get_db()
    page = int(request.args.get('page', 1) or 1)

    invoices = admin_paginate(\"\"\"""",
"""@app.route('/admin/manage/invoices')
@admin_required
def admin_invoices_page():
    conn = get_db()
    page = int(request.args.get('page', 1) or 1)
    search = request.args.get('search', '').strip()

    invoices = admin_paginate(\"\"\""""
)
code = code.replace(
"""        ORDER BY invoices.created_at DESC
    \"\"\", page=page, per_page=8)""",
"""        ORDER BY invoices.created_at DESC
    \"\"\", page=page, per_page=8, search=search, search_cols=['invoice_no', 'title', 'status', 'client_name', 'user_name', 'user_email'])"""
)

# admin_billing_page
code = code.replace(
"""@app.route('/admin/manage/billing')
@admin_required
def admin_billing_page():
    page = int(request.args.get('page', 1) or 1)
    payments = admin_paginate('SELECT * FROM payments ORDER BY COALESCE(created_at, date_str) DESC, id DESC', page=page, per_page=8)""",
"""@app.route('/admin/manage/billing')
@admin_required
def admin_billing_page():
    page = int(request.args.get('page', 1) or 1)
    search = request.args.get('search', '').strip()
    payments = admin_paginate('SELECT * FROM payments ORDER BY COALESCE(created_at, date_str) DESC, id DESC', page=page, per_page=8, search=search, search_cols=['receipt_no', 'name', 'email', 'project', 'service', 'status'])"""
)

# admin_assets_page
code = code.replace(
"""@app.route('/admin/assets')
@admin_required
def admin_assets_page():
    page = int(request.args.get('page', 1) or 1)
    files = admin_paginate('SELECT pf.*, p.title AS project_title, u.name AS client_name FROM project_files pf LEFT JOIN projects p ON pf.project_id=p.id LEFT JOIN users u ON pf.user_id=u.id ORDER BY pf.id DESC', page=page, per_page=8)""",
"""@app.route('/admin/assets')
@admin_required
def admin_assets_page():
    page = int(request.args.get('page', 1) or 1)
    search = request.args.get('search', '').strip()
    files = admin_paginate('SELECT pf.*, p.title AS project_title, u.name AS client_name FROM project_files pf LEFT JOIN projects p ON pf.project_id=p.id LEFT JOIN users u ON pf.user_id=u.id ORDER BY pf.id DESC', page=page, per_page=8, search=search, search_cols=['title', 'filename', 'project_title', 'client_name'])"""
)

# admin_contact_page
code = code.replace(
"""@app.route('/admin/contact')
@admin_required
def admin_contact_page():
    page = int(request.args.get('page', 1) or 1)
    contacts = admin_paginate('SELECT * FROM contacts ORDER BY id DESC', page=page, per_page=8)""",
"""@app.route('/admin/contact')
@admin_required
def admin_contact_page():
    page = int(request.args.get('page', 1) or 1)
    search = request.args.get('search', '').strip()
    contacts = admin_paginate('SELECT * FROM contacts ORDER BY id DESC', page=page, per_page=8, search=search, search_cols=['name', 'email', 'subject', 'message'])"""
)

# admin_activity_page
code = code.replace(
"""@app.route('/admin/activity')
@admin_required
def admin_activity_page():
    page = int(request.args.get('page', 1) or 1)
    logs = admin_paginate("SELECT a.*, u.name AS actor_name, u.email AS actor_email FROM activity_logs a LEFT JOIN users u ON a.actor_user_id=u.id ORDER BY a.id DESC", page=page, per_page=20)""",
"""@app.route('/admin/activity')
@admin_required
def admin_activity_page():
    page = int(request.args.get('page', 1) or 1)
    search = request.args.get('search', '').strip()
    logs = admin_paginate("SELECT a.*, u.name AS actor_name, u.email AS actor_email FROM activity_logs a LEFT JOIN users u ON a.actor_user_id=u.id ORDER BY a.id DESC", page=page, per_page=20, search=search, search_cols=['area', 'action', 'details', 'actor_name', 'actor_email'])"""
)

with open('app.py', 'w', encoding='utf-8') as f:
    f.write(code)
print("app.py updated with search pagination")
