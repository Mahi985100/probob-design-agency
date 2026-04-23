import re

with open('app.py', 'r', encoding='utf-8') as f:
    code = f.read()

# 1. admin_services_page
old_services = """@app.route('/admin/work/services')
@admin_required
def admin_services_page():
    db = get_db()
    category = request.args.get('category', '').strip()
    query = 'SELECT * FROM service_items'
    params = []
    if category:
        query += ' WHERE category=?'
        params.append(category)
    query += ' ORDER BY id DESC'
    services = db.execute(query, params).fetchall()"""
new_services = """@app.route('/admin/work/services')
@admin_required
def admin_services_page():
    db = get_db()
    category = request.args.get('category', '').strip()
    page = int(request.args.get('page', 1) or 1)
    query = 'SELECT * FROM service_items'
    params = []
    if category:
        query += ' WHERE category=?'
        params.append(category)
    query += ' ORDER BY id DESC'
    services = admin_paginate(query, params, page=page, per_page=8)"""
code = code.replace(old_services, new_services)

# 2. admin_portfolio_page
old_portfolio = """@app.route('/admin/work/portfolio')
@admin_required
def admin_portfolio_page():
    items = get_db().execute('SELECT * FROM portfolio_items ORDER BY id DESC').fetchall()"""
new_portfolio = """@app.route('/admin/work/portfolio')
@admin_required
def admin_portfolio_page():
    page = int(request.args.get('page', 1) or 1)
    items = admin_paginate('SELECT * FROM portfolio_items ORDER BY id DESC', page=page, per_page=8)"""
code = code.replace(old_portfolio, new_portfolio)

# 3. admin_blog_page
old_blog = """@app.route('/admin/work/blog')
@admin_required
def admin_blog_page():
    posts = get_db().execute('SELECT * FROM blog_posts ORDER BY id DESC').fetchall()"""
new_blog = """@app.route('/admin/work/blog')
@admin_required
def admin_blog_page():
    page = int(request.args.get('page', 1) or 1)
    posts = admin_paginate('SELECT * FROM blog_posts ORDER BY id DESC', page=page, per_page=8)"""
code = code.replace(old_blog, new_blog)

# 4. admin_projects_page
old_projects = """@app.route('/admin/manage/projects')
@admin_required
def admin_projects_page():
    sync_started_projects_to_admin()
    projects = get_db().execute('SELECT p.*, u.name AS client_name, u.email AS client_email FROM projects p LEFT JOIN users u ON p.user_id=u.id ORDER BY p.id DESC').fetchall()"""
new_projects = """@app.route('/admin/manage/projects')
@admin_required
def admin_projects_page():
    sync_started_projects_to_admin()
    page = int(request.args.get('page', 1) or 1)
    projects = admin_paginate('SELECT p.*, u.name AS client_name, u.email AS client_email FROM projects p LEFT JOIN users u ON p.user_id=u.id ORDER BY p.id DESC', page=page, per_page=8)"""
code = code.replace(old_projects, new_projects)

# 5. admin_invoices_page
old_invoices = """@app.route('/admin/manage/invoices')
@admin_required
def admin_invoices_page():
    conn = get_db()

    invoices = conn.execute(\"\"\"
        SELECT invoices.*,
               projects.title AS project_title,
               users.name AS client_name,
               users.name AS user_name,
               users.email AS user_email
        FROM invoices
        LEFT JOIN projects ON invoices.project_id = projects.id
        LEFT JOIN users ON invoices.user_id = users.id
        ORDER BY invoices.created_at DESC
    \"\"\").fetchall()"""
new_invoices = """@app.route('/admin/manage/invoices')
@admin_required
def admin_invoices_page():
    conn = get_db()
    page = int(request.args.get('page', 1) or 1)

    invoices = admin_paginate(\"\"\"
        SELECT invoices.*,
               projects.title AS project_title,
               users.name AS client_name,
               users.name AS user_name,
               users.email AS user_email
        FROM invoices
        LEFT JOIN projects ON invoices.project_id = projects.id
        LEFT JOIN users ON invoices.user_id = users.id
        ORDER BY invoices.created_at DESC
    \"\"\", page=page, per_page=8)"""
code = code.replace(old_invoices, new_invoices)

# 6. admin_billing_page
old_billing = """@app.route('/admin/manage/billing')
@admin_required
def admin_billing_page():
    payments = get_db().execute('SELECT * FROM payments ORDER BY COALESCE(created_at, date_str) DESC, id DESC').fetchall()"""
new_billing = """@app.route('/admin/manage/billing')
@admin_required
def admin_billing_page():
    page = int(request.args.get('page', 1) or 1)
    payments = admin_paginate('SELECT * FROM payments ORDER BY COALESCE(created_at, date_str) DESC, id DESC', page=page, per_page=8)"""
code = code.replace(old_billing, new_billing)

# 7. admin_assets_page
old_assets = """@app.route('/admin/assets')
@admin_required
def admin_assets_page():
    files = get_db().execute('SELECT pf.*, p.title AS project_title, u.name AS client_name FROM project_files pf LEFT JOIN projects p ON pf.project_id=p.id LEFT JOIN users u ON pf.user_id=u.id ORDER BY pf.id DESC').fetchall()"""
new_assets = """@app.route('/admin/assets')
@admin_required
def admin_assets_page():
    page = int(request.args.get('page', 1) or 1)
    files = admin_paginate('SELECT pf.*, p.title AS project_title, u.name AS client_name FROM project_files pf LEFT JOIN projects p ON pf.project_id=p.id LEFT JOIN users u ON pf.user_id=u.id ORDER BY pf.id DESC', page=page, per_page=8)"""
code = code.replace(old_assets, new_assets)

# 8. admin_contact_page
old_contact = """@app.route('/admin/contact')
@admin_required
def admin_contact_page():
    contacts = get_db().execute('SELECT * FROM contacts ORDER BY id DESC').fetchall()"""
new_contact = """@app.route('/admin/contact')
@admin_required
def admin_contact_page():
    page = int(request.args.get('page', 1) or 1)
    contacts = admin_paginate('SELECT * FROM contacts ORDER BY id DESC', page=page, per_page=8)"""
code = code.replace(old_contact, new_contact)

# 9. admin_activity_page
old_activity = """@app.route('/admin/activity')
@admin_required
def admin_activity_page():
    logs = get_db().execute("SELECT a.*, u.name AS actor_name, u.email AS actor_email FROM activity_logs a LEFT JOIN users u ON a.actor_user_id=u.id ORDER BY a.id DESC LIMIT 80").fetchall()"""
new_activity = """@app.route('/admin/activity')
@admin_required
def admin_activity_page():
    page = int(request.args.get('page', 1) or 1)
    logs = admin_paginate("SELECT a.*, u.name AS actor_name, u.email AS actor_email FROM activity_logs a LEFT JOIN users u ON a.actor_user_id=u.id ORDER BY a.id DESC", page=page, per_page=20)"""
code = code.replace(old_activity, new_activity)

with open('app.py', 'w', encoding='utf-8') as f:
    f.write(code)
print("Updated app.py")
