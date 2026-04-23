import re

with open('templates/admin_base.html', 'r', encoding='utf-8') as f:
    content = f.read()

# Replace the search div with a form
search_div = """          <div class="admin-search-wrap">
            <span class="admin-search-icon">⌕</span>
            <input type="search" id="adminPageSearch" class="admin-search-input" placeholder="Search this page..." autocomplete="off">
          </div>"""

search_form = """          <form method="GET" class="admin-search-wrap" action="">
            {% for key, val in request.args.items() %}
              {% if key != 'search' and key != 'page' %}
                <input type="hidden" name="{{ key }}" value="{{ val }}">
              {% endif %}
            {% endfor %}
            <span class="admin-search-icon">⌕</span>
            <input type="search" name="search" class="admin-search-input" placeholder="Search records..." value="{{ request.args.get('search', '') }}" autocomplete="off">
          </form>"""

content = content.replace(search_div, search_form)

# Remove the javascript
js_code = """<script>
document.addEventListener('DOMContentLoaded', function () {
  const searchInput = document.getElementById('adminPageSearch');
  if (!searchInput) return;

  const searchTargets = Array.from(document.querySelectorAll(
    '.admin-table tbody tr, .metric-row > div, .calendar-day, .portfolio-grid > *, .crud-list > *, .admin-list > *, .glass-card.admin-section > *'
  )).filter((node) => {
    if (!node) return false;
    if (node.closest('.admin-topbar')) return false;
    if (node.matches('style, script')) return false;
    const text = (node.innerText || '').replace(/\\s+/g, ' ').trim();
    return text.length > 0;
  });

  if (!searchTargets.length) return;

  let emptyState = document.getElementById('adminSearchEmptyState');
  if (!emptyState) {
    emptyState = document.createElement('div');
    emptyState.id = 'adminSearchEmptyState';
    emptyState.className = 'admin-search-empty';
    emptyState.textContent = 'No matching results found on this page.';
    emptyState.style.display = 'none';
    const topbar = document.querySelector('.admin-topbar');
    if (topbar && topbar.parentNode) topbar.parentNode.insertBefore(emptyState, topbar.nextSibling);
  }

  searchInput.addEventListener('input', function () {
    const query = searchInput.value.toLowerCase().trim();
    let visibleCount = 0;

    searchTargets.forEach((node) => {
      const text = (node.innerText || '').replace(/\\s+/g, ' ').trim().toLowerCase();
      const match = !query || text.includes(query);
      node.style.display = match ? '' : 'none';
      if (match) visibleCount += 1;
    });

    emptyState.style.display = query && visibleCount === 0 ? 'block' : 'none';
  });
});
</script>"""

content = content.replace(js_code, "")

with open('templates/admin_base.html', 'w', encoding='utf-8') as f:
    f.write(content)
print("Updated admin_base.html")
