import os
import re
import sqlite3

# Update Database Schema directly to avoid any app.py startup issues
db = sqlite3.connect('probob.db')
columns = [col[1] for col in db.execute("PRAGMA table_info(portfolio_items)").fetchall()]
if "cover_image" not in columns:
    db.execute("ALTER TABLE portfolio_items ADD COLUMN cover_image TEXT")
db.commit()
db.close()

APP_PY_PATH = 'app.py'
with open(APP_PY_PATH, 'r', encoding='utf-8') as f:
    app_py_content = f.read()

# 1. Update ensure schema in app.py just in case
schema_patch = """        if "cover_image" not in column_names:
            db.execute("ALTER TABLE portfolio_items ADD COLUMN cover_image TEXT")"""
app_py_content = re.sub(
    r'(if "created_at" not in column_names:\s*db\.execute\("ALTER TABLE portfolio_items ADD COLUMN created_at TEXT"\))',
    r'\1\n' + schema_patch,
    app_py_content
)

# 2. Update admin_create_portfolio
create_find = """@app.route('/admin/work/portfolio/create', methods=['POST'])
@admin_required
def admin_create_portfolio():
    get_db().execute('INSERT INTO portfolio_items (title,description,category,emoji,featured) VALUES (?,?,?,?,?)',
                     (request.form.get('title'), request.form.get('description'), request.form.get('category'),
                      request.form.get('emoji'), 1 if request.form.get('featured') else 0))"""
create_replace = """@app.route('/admin/work/portfolio/create', methods=['POST'])
@admin_required
def admin_create_portfolio():
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

    get_db().execute('INSERT INTO portfolio_items (title,description,category,emoji,featured,cover_image) VALUES (?,?,?,?,?,?)',
                     (request.form.get('title'), request.form.get('description'), request.form.get('category'),
                      request.form.get('emoji'), 1 if request.form.get('featured') else 0, cover_image))"""
if create_find in app_py_content:
    app_py_content = app_py_content.replace(create_find, create_replace)

# 3. Update admin_edit_portfolio
edit_find = """@app.route('/admin/work/portfolio/<int:item_id>/edit', methods=['GET', 'POST'])
@admin_required
def admin_edit_portfolio(item_id):
    db = get_db()
    if request.method == 'POST':
        db.execute('UPDATE portfolio_items SET title=?, description=?, category=?, emoji=?, featured=? WHERE id=?',
                   (request.form.get('title'), request.form.get('description'), request.form.get('category'),
                    request.form.get('emoji'), 1 if request.form.get('featured') else 0, item_id))"""
edit_replace = """@app.route('/admin/work/portfolio/<int:item_id>/edit', methods=['GET', 'POST'])
@admin_required
def admin_edit_portfolio(item_id):
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
                db.execute('UPDATE portfolio_items SET cover_image=? WHERE id=?', (cover_image, item_id))

        db.execute('UPDATE portfolio_items SET title=?, description=?, category=?, emoji=?, featured=? WHERE id=?',
                   (request.form.get('title'), request.form.get('description'), request.form.get('category'),
                    request.form.get('emoji'), 1 if request.form.get('featured') else 0, item_id))"""
if edit_find in app_py_content:
    app_py_content = app_py_content.replace(edit_find, edit_replace)

with open(APP_PY_PATH, 'w', encoding='utf-8') as f:
    f.write(app_py_content)
print("Updated app.py")


# Update admin_portfolio.html template
ADMIN_PORTFOLIO_PATH = 'templates/admin_portfolio.html'
with open(ADMIN_PORTFOLIO_PATH, 'r', encoding='utf-8') as f:
    admin_portfolio_content = f.read()

# Add enctype to form
admin_portfolio_content = admin_portfolio_content.replace('<form method="POST"', '<form method="POST" enctype="multipart/form-data"')

# Add image input
image_input_html = """      <div class="form-group">
        <label>Cover Image</label>
        <input type="file" name="image" accept="image/*">
        {% if edit_item and edit_item.cover_image %}
          <small style="color: var(--gold); display: block; margin-top: 5px;">Current image: <a href="{{ url_for('static', filename='uploads/' + edit_item.cover_image) }}" target="_blank" style="color: var(--gold); text-decoration: underline;">{{ edit_item.cover_image }}</a></small>
        {% endif %}
      </div>"""

admin_portfolio_content = admin_portfolio_content.replace(
    '<div class="form-group">\n        <label>Description',
    image_input_html + '\n      <div class="form-group">\n        <label>Description'
)

# Also show image in list
admin_portfolio_content = admin_portfolio_content.replace('<th>Title</th>', '<th>Image</th>\n                <th>Title</th>')
table_data_replace = """                <td>
                  {% if item.cover_image %}
                    <img src="{{ url_for('static', filename='uploads/' + item.cover_image) }}" style="width: 50px; height: 50px; object-fit: cover; border-radius: 8px;">
                  {% else %}
                    <div style="width: 50px; height: 50px; background: rgba(255,255,255,0.1); border-radius: 8px; display: flex; align-items: center; justify-content: center;">📝</div>
                  {% endif %}
                </td>
                <td>"""
admin_portfolio_content = admin_portfolio_content.replace('<td><strong>{{ item.title }}</strong>', table_data_replace + '<strong>{{ item.title }}</strong>')


with open(ADMIN_PORTFOLIO_PATH, 'w', encoding='utf-8') as f:
    f.write(admin_portfolio_content)
print("Updated templates/admin_portfolio.html")
