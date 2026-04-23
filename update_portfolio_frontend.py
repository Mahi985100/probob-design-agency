import re

PORTFOLIO_PATH = 'templates/portfolio.html'
with open(PORTFOLIO_PATH, 'r', encoding='utf-8') as f:
    content = f.read()

# Extract the portfolio-gallery-grid
start_marker = '<div class="portfolio-gallery-grid" id="portfolioGallery">'
end_marker = '</div><!-- /grid -->'

start_idx = content.find(start_marker)
end_idx = content.find(end_marker)

if start_idx != -1 and end_idx != -1:
    before = content[:start_idx + len(start_marker)]
    after = content[end_idx:]
    
    # Jinja loop to replace the hardcoded articles
    jinja_loop = """
        {% for item in items %}
        <article class="portfolio-photo-card {% if loop.index > 9 %}hidden-card{% else %}visible{% endif %}">
          <div class="portfolio-photo-media">
            {% if item.cover_image %}
              <img src="{{ url_for('static', filename='uploads/' ~ item.cover_image) }}" alt="{{ item.title }}">
            {% else %}
              <img src="{{ url_for('static', filename='images/' ~ (((loop.index0) % 21) + 1) ~ '.png') }}" alt="{{ item.title }}">
            {% endif %}
            <div class="card-sheen"></div>
            <div class="portfolio-photo-overlay">
              <span>{{ item.category }}</span>
              <h3>{{ item.title }}</h3>
            </div>
          </div>
        </article>
        {% endfor %}
      """
    
    new_content = before + jinja_loop + after
    with open(PORTFOLIO_PATH, 'w', encoding='utf-8') as f:
        f.write(new_content)
    print("Successfully replaced hardcoded portfolio cards with Jinja loop")
else:
    print("Failed to find portfolio grid markers")
