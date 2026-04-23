import re

with open('templates/admin_base.html', 'r', encoding='utf-8') as f:
    content = f.read()

# Replace {% if key != 'search' and key != 'page' %}
# with {% if key != 'search' and 'page' not in key %}
old_condition = "{% if key != 'search' and key != 'page' %}"
new_condition = "{% if key != 'search' and 'page' not in key %}"

content = content.replace(old_condition, new_condition)

with open('templates/admin_base.html', 'w', encoding='utf-8') as f:
    f.write(content)
print("Updated admin_base.html to reset all page counters on search")
