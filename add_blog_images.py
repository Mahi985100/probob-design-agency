import os
import re

APP_PY_PATH = 'app.py'
with open(APP_PY_PATH, 'r', encoding='utf-8') as f:
    app_py_content = f.read()

# 1. Update ensure_blog_posts_schema
schema_patch = """        if "cover_image" not in column_names:
            db.execute("ALTER TABLE blog_posts ADD COLUMN cover_image TEXT")"""
app_py_content = re.sub(
    r'(if "slug" not in column_names:\s*db\.execute\("ALTER TABLE blog_posts ADD COLUMN slug TEXT"\))',
    r'\1\n' + schema_patch,
    app_py_content
)

# 2. Update admin_create_blog
create_patch_find = """@app.route('/admin/blog/create', methods=['POST'])
@admin_required
def admin_create_blog():
    get_db().execute('INSERT INTO blog_posts (title,excerpt,content,category,author,published_at,cover_emoji,tags) VALUES (?,?,?,?,?,?,?,?)',
                     (request.form.get('title'), request.form.get('excerpt'), request.form.get('content'),
                      request.form.get('category'), request.form.get('author'), request.form.get('published_at'),
                      request.form.get('cover_emoji'), request.form.get('tags')))"""

create_patch_replace = """@app.route('/admin/blog/create', methods=['POST'])
@admin_required
def admin_create_blog():
    cover_image = None
    if 'image' in request.files:
        file = request.files['image']
        if file.filename != '':
            from werkzeug.utils import secure_filename
            import os
            import time
            filename = str(int(time.time())) + '_' + secure_filename(file.filename)
            upload_folder = os.path.join(app.root_path, 'static', 'uploads')
            os.makedirs(upload_folder, exist_ok=True)
            file.save(os.path.join(upload_folder, filename))
            cover_image = filename

    get_db().execute('INSERT INTO blog_posts (title,excerpt,content,category,author,published_at,cover_emoji,tags,cover_image) VALUES (?,?,?,?,?,?,?,?,?)',
                     (request.form.get('title'), request.form.get('excerpt'), request.form.get('content'),
                      request.form.get('category'), request.form.get('author'), request.form.get('published_at'),
                      request.form.get('cover_emoji'), request.form.get('tags'), cover_image))"""

if create_patch_find in app_py_content:
    app_py_content = app_py_content.replace(create_patch_find, create_patch_replace)
else:
    print("WARNING: admin_create_blog patch failed")

# 3. Update admin_edit_blog
edit_patch_find = """@app.route('/admin/blog/<int:post_id>/edit', methods=['GET', 'POST'])
@admin_required
def admin_edit_blog(post_id):
    db = get_db()
    if request.method == 'POST':
        db.execute('UPDATE blog_posts SET title=?, excerpt=?, content=?, category=?, author=?, published_at=?, cover_emoji=?, tags=? WHERE id=?',
                   (request.form.get('title'), request.form.get('excerpt'), request.form.get('content'),
                    request.form.get('category'), request.form.get('author'), request.form.get('published_at'),
                    request.form.get('cover_emoji'), request.form.get('tags'), post_id))"""

edit_patch_replace = """@app.route('/admin/blog/<int:post_id>/edit', methods=['GET', 'POST'])
@admin_required
def admin_edit_blog(post_id):
    db = get_db()
    if request.method == 'POST':
        cover_image = None
        if 'image' in request.files:
            file = request.files['image']
            if file.filename != '':
                from werkzeug.utils import secure_filename
                import os
                import time
                filename = str(int(time.time())) + '_' + secure_filename(file.filename)
                upload_folder = os.path.join(app.root_path, 'static', 'uploads')
                os.makedirs(upload_folder, exist_ok=True)
                file.save(os.path.join(upload_folder, filename))
                cover_image = filename
                db.execute('UPDATE blog_posts SET cover_image=? WHERE id=?', (cover_image, post_id))

        db.execute('UPDATE blog_posts SET title=?, excerpt=?, content=?, category=?, author=?, published_at=?, cover_emoji=?, tags=? WHERE id=?',
                   (request.form.get('title'), request.form.get('excerpt'), request.form.get('content'),
                    request.form.get('category'), request.form.get('author'), request.form.get('published_at'),
                    request.form.get('cover_emoji'), request.form.get('tags'), post_id))"""

if edit_patch_find in app_py_content:
    app_py_content = app_py_content.replace(edit_patch_find, edit_patch_replace)
else:
    print("WARNING: admin_edit_blog patch failed")

with open(APP_PY_PATH, 'w', encoding='utf-8') as f:
    f.write(app_py_content)
print("Updated app.py")


# Update admin_blog.html template
ADMIN_BLOG_PATH = 'templates/admin_blog.html'
with open(ADMIN_BLOG_PATH, 'r', encoding='utf-8') as f:
    admin_blog_content = f.read()

# Add enctype to form
admin_blog_content = admin_blog_content.replace('<form method="POST"', '<form method="POST" enctype="multipart/form-data"')

# Add image input
image_input_html = """            <div class="form-group">
                <label>Cover Image</label>
                <input type="file" name="image" accept="image/*">
                {% if edit_item and edit_item.cover_image %}
                    <small style="color: var(--gold); display: block; margin-top: 5px;">Current image: {{ edit_item.cover_image }}</small>
                {% endif %}
            </div>"""

admin_blog_content = admin_blog_content.replace(
    '<div class="form-group">\n                <label>Excerpt',
    image_input_html + '\n            <div class="form-group">\n                <label>Excerpt'
)

# Also show image in list
admin_blog_content = admin_blog_content.replace('<th>Title</th>', '<th>Image</th>\n                <th>Title</th>')
table_data_replace = """                <td>
                    {% if post.cover_image %}
                        <img src="{{ url_for('static', filename='uploads/' + post.cover_image) }}" style="width: 50px; height: 50px; object-fit: cover; border-radius: 8px;">
                    {% else %}
                        <div style="width: 50px; height: 50px; background: rgba(255,255,255,0.1); border-radius: 8px; display: flex; align-items: center; justify-content: center;">📝</div>
                    {% endif %}
                </td>
                <td>"""
admin_blog_content = admin_blog_content.replace('<td>\n                    <strong>{{ post.title }}</strong>', table_data_replace + '\n                    <strong>{{ post.title }}</strong>')


with open(ADMIN_BLOG_PATH, 'w', encoding='utf-8') as f:
    f.write(admin_blog_content)
print("Updated templates/admin_blog.html")


# Update blog_react_exact.html template
BLOG_REACT_PATH = 'templates/blog_react_exact.html'
with open(BLOG_REACT_PATH, 'r', encoding='utf-8') as f:
    blog_react_content = f.read()

blog_react_replace = """    image: post.cover_image ? `/static/uploads/${post.cover_image}` : '{{ url_for("static", filename="images/1.png") }}',"""
blog_react_content = blog_react_content.replace("    image: '{{ url_for(\"static\", filename=\"images/1.png\") }}',", blog_react_replace)

with open(BLOG_REACT_PATH, 'w', encoding='utf-8') as f:
    f.write(blog_react_content)
print("Updated templates/blog_react_exact.html")

