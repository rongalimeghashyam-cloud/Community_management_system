import re

with open('templates/index.html', 'r', encoding='utf-8') as f:
    content = f.read()

# The content area starts at <div class="content">
# and ends right before </main>

# Find <div class="content">
start_idx = content.find('<div class="content">')
# Find </main>
end_idx = content.find('</main>')

# We will wrap the active link logic dynamically using Jinja2
# But for now let's just create base.html and index.html

header_and_above = content[:start_idx]
modal_and_below = content[end_idx:]

# Let's fix the sidebar links in header_and_above to use url_for
nav_replacements = {
    'class="nav-item active"': 'class="nav-item {% if request.endpoint == \'home\' %}active{% endif %}" href="{{ url_for(\'home\') }}"',
    'onclick="alert(\'Navigating to Residents\')"': 'class="nav-item {% if request.endpoint == \'residents\' %}active{% endif %}" href="{{ url_for(\'residents\') }}"',
    'onclick="alert(\'Navigating to Maintenance\')"': 'class="nav-item {% if request.endpoint == \'maintenance\' %}active{% endif %}" href="{{ url_for(\'maintenance\') }}"',
    'onclick="alert(\'Navigating to Events\')"': 'class="nav-item {% if request.endpoint == \'events\' %}active{% endif %}" href="{{ url_for(\'events\') }}"',
    'onclick="alert(\'Navigating to Security\')"': 'class="nav-item {% if request.endpoint == \'security\' %}active{% endif %}" href="{{ url_for(\'security\') }}"',
    'onclick="alert(\'Navigating to Settings\')"': 'class="nav-item {% if request.endpoint == \'settings\' %}active{% endif %}" href="{{ url_for(\'settings\') }}"',
}

for old, new in nav_replacements.items():
    # Remove href="javascript:void(0)" and the old class/onclick
    header_and_above = re.sub(r'href="javascript:void\(0\)"\s+' + re.escape(old), new, header_and_above)

base_html = header_and_above + "\n        {% block content %}{% endblock %}\n    " + modal_and_below

with open('templates/base.html', 'w', encoding='utf-8') as f:
    f.write(base_html)

# Now index.html
index_content = content[start_idx:end_idx]
new_index_html = "{% extends 'base.html' %}\n{% block content %}\n" + index_content + "\n{% endblock %}\n"

with open('templates/index.html', 'w', encoding='utf-8') as f:
    f.write(new_index_html)

print("Refactored into base.html and index.html successfully.")
