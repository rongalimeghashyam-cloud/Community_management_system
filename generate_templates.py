import os

templates = {
    'residents.html': """{% extends 'base.html' %}
{% block content %}
<div class="content">
    <div class="page-header">
        <div class="page-title">
            <h1>Residents Directory</h1>
            <p>Manage community members and unit assignments.</p>
        </div>
        <button class="btn-export" onclick="alert('Adding resident...')">
            <i class="ph ph-user-plus"></i> Add Resident
        </button>
    </div>
    <div class="activity-card" style="padding: 20px;">
        <table style="width: 100%; border-collapse: collapse; text-align: left;">
            <thead>
                <tr style="border-bottom: 1px solid var(--border-color); color: var(--text-muted); font-size: 14px;">
                    <th style="padding: 12px 8px;">Name</th>
                    <th style="padding: 12px 8px;">Unit</th>
                    <th style="padding: 12px 8px;">Lease Status</th>
                    <th style="padding: 12px 8px;">Contact</th>
                </tr>
            </thead>
            <tbody>
                {% for resident in residents %}
                <tr style="border-bottom: 1px solid var(--border-color); font-size: 14px;">
                    <td style="padding: 16px 8px; font-weight: 500;">{{ resident.name }}</td>
                    <td style="padding: 16px 8px;">{{ resident.unit }}</td>
                    <td style="padding: 16px 8px;">
                        <span class="stat-badge {% if resident.status == 'Active' %}badge-blue{% else %}badge-red{% endif %}">{{ resident.status }}</span>
                    </td>
                    <td style="padding: 16px 8px; color: var(--text-muted);">{{ resident.contact }}</td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
    </div>
</div>
{% endblock %}
""",

    'maintenance.html': """{% extends 'base.html' %}
{% block content %}
<div class="content">
    <div class="page-header">
        <div class="page-title">
            <h1>Maintenance Tickets</h1>
            <p>Track and manage community infrastructure issues.</p>
        </div>
        <button class="btn-export" onclick="alert('Creating ticket...')">
            <i class="ph ph-plus"></i> New Ticket
        </button>
    </div>
    <div class="activity-card" style="padding: 20px;">
        <div class="activity-list">
            {% for ticket in tickets %}
            <div class="activity-item" style="align-items: center; justify-content: space-between; border-bottom: 1px solid var(--border-color); padding-bottom: 16px;">
                <div style="display: flex; gap: 16px; align-items: center;">
                    <div class="activity-icon" style="{% if ticket.priority == 'High' %}background: #FEE2E2; color: #DC2626;{% else %}background: #DBEAFE; color: #2563EB;{% endif %}">
                        <i class="ph ph-wrench"></i>
                    </div>
                    <div class="activity-content">
                        <p style="margin: 0; font-weight: 600;">{{ ticket.title }} <span style="font-size: 12px; color: var(--text-muted); font-weight: normal; margin-left: 8px;">#{{ ticket.id }}</span></p>
                        <div class="activity-meta" style="margin-top: 4px;">{{ ticket.location }} • Reported {{ ticket.date }}</div>
                    </div>
                </div>
                <div>
                    <span class="stat-badge {% if ticket.status == 'Open' %}badge-red{% else %}badge-gray{% endif %}">{{ ticket.status }}</span>
                </div>
            </div>
            {% endfor %}
        </div>
    </div>
</div>
{% endblock %}
""",

    'events.html': """{% extends 'base.html' %}
{% block content %}
<div class="content">
    <div class="page-header">
        <div class="page-title">
            <h1>Community Events</h1>
            <p>Upcoming activities and facility bookings.</p>
        </div>
        <button class="btn-export" onclick="alert('Scheduling event...')">
            <i class="ph ph-calendar-plus"></i> Schedule Event
        </button>
    </div>
    <div class="stats-grid">
        {% for event in events %}
        <div class="stat-card">
            <div class="stat-header">
                <div class="stat-icon icon-indigo"><i class="ph-fill ph-calendar-star"></i></div>
                <span class="stat-badge badge-blue">{{ event.date }}</span>
            </div>
            <div style="margin-top: 12px;">
                <div class="stat-title" style="color: var(--text-main); font-weight: 600; font-size: 16px;">{{ event.title }}</div>
                <div class="stat-value" style="font-size: 14px; color: var(--text-muted); font-weight: 400; margin-top: 4px;">{{ event.location }}</div>
            </div>
        </div>
        {% endfor %}
    </div>
</div>
{% endblock %}
""",

    'security.html': """{% extends 'base.html' %}
{% block content %}
<div class="content">
    <div class="page-header">
        <div class="page-title">
            <h1>Security Logs</h1>
            <p>Recent alerts and automated security reports.</p>
        </div>
    </div>
    <div class="activity-card" style="padding: 20px;">
        <div class="activity-list">
            {% for log in security_logs %}
            <div class="activity-item">
                <div class="activity-icon" style="{% if log.level == 'Warning' %}background: #FEF3C7; color: #D97706;{% elif log.level == 'Critical' %}background: #FEE2E2; color: #DC2626;{% else %}background: #E2E8F0; color: #475569;{% endif %}">
                    <i class="ph ph-shield-{% if log.level == 'Critical' %}warning{% else %}check{% endif %}"></i>
                </div>
                <div class="activity-content">
                    <p><strong>{{ log.event }}</strong></p>
                    <div class="activity-meta">{{ log.time }} • {{ log.location }}</div>
                </div>
            </div>
            {% endfor %}
        </div>
    </div>
</div>
{% endblock %}
""",

    'settings.html': """{% extends 'base.html' %}
{% block content %}
<div class="content">
    <div class="page-header">
        <div class="page-title">
            <h1>System Settings</h1>
            <p>Manage application configuration and API integrations.</p>
        </div>
    </div>
    
    <div class="bottom-grid">
        <div class="activity-card" style="padding: 32px;">
            <h3 style="margin-bottom: 24px; font-size: 18px;">AI Model Integration</h3>
            <p style="font-size: 14px; color: var(--text-muted); margin-bottom: 24px;">
                Enter your API keys below to enable the AI Analysis features. These will be securely stored and used by the community agents.
            </p>
            
            {% if success_msg %}
            <div style="background-color: #DEF7EC; border: 1px solid #31C48D; color: #03543F; padding: 12px; border-radius: 8px; margin-bottom: 24px; font-size: 14px; font-weight: 500;">
                {{ success_msg }}
            </div>
            {% endif %}

            <form action="{{ url_for('settings') }}" method="POST" style="display: flex; flex-direction: column; gap: 20px;">
                
                <div>
                    <label style="display: block; font-size: 14px; font-weight: 600; margin-bottom: 8px;">Gemini API Key</label>
                    <input type="password" name="gemini_api_key" value="{{ settings.get('gemini_api_key', '') }}" placeholder="AIzaSy..." style="width: 100%; padding: 12px; border-radius: 8px; border: 1px solid var(--border-color); font-size: 14px;">
                </div>

                <div>
                    <label style="display: block; font-size: 14px; font-weight: 600; margin-bottom: 8px;">OpenAI API Key</label>
                    <input type="password" name="openai_api_key" value="{{ settings.get('openai_api_key', '') }}" placeholder="sk-..." style="width: 100%; padding: 12px; border-radius: 8px; border: 1px solid var(--border-color); font-size: 14px;">
                </div>

                <button type="submit" style="background-color: var(--accent-blue); color: white; border: none; padding: 12px 24px; border-radius: 8px; font-weight: 600; font-size: 14px; cursor: pointer; align-self: flex-start; transition: opacity 0.2s;">
                    Save Settings
                </button>
            </form>
        </div>
    </div>
</div>
{% endblock %}
"""
}

for filename, html_content in templates.items():
    with open(f"templates/{filename}", "w", encoding="utf-8") as f:
        f.write(html_content)

print("Generated all template files.")
