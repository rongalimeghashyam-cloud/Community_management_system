from crewai.tools import tool

@tool("query_community_info")
def query_community_info(query: str) -> str:
    """
    Queries the Greenwood Village community database for general info, resident rules, 
    amenities, pool hours, maintenance schedules, security contacts, or HOA details.
    """
    q = query.lower()
    if "pool" in q:
        return "Pool Hours: 6:00 AM - 10:00 PM daily. Maintenance scheduled on Aug 22. Lifeguard on duty weekends 10am-6pm."
    elif "bbq" in q or "event" in q:
        return "Upcoming events: Summer BBQ on Aug 15 at Rec Center, HOA General Meeting on Aug 20 in Main Hall."
    elif "contact" in q or "manager" in q or "phone" in q:
        return "Community Manager: Sarah Jenkins (sarah.j@example.com), Emergency Security Gate: (555) 019-2834."
    elif "parking" in q or "car" in q:
        return "Visitor parking requires a guest pass from the management office. Max 48 hrs consecutively."
    elif "maintenance" in q or "fix" in q:
        return "Routine maintenance works are handled weekdays 8am - 5pm. Emergency plumbing/electrical is 24/7."
    else:
        return "Greenwood Village HOA: 1,428 active residents, 4 residential towers (A, B, C, D), 24/7 security patrol, active rec center and pool facilities."

@tool("check_database_for_duplicates")
def check_database_for_duplicates(category: str) -> str:
    """
    Queries the city database to check for existing open complaints 
    matching a specific infrastructure category.
    """
    existing_records = {
        "roads": "Ticket #1024: Massive pothole reported on Main Street. Status: Open.",
        "utilities": "No open tickets found for this category.",
        "sanitation": "Ticket #0988: Trash missed on Elm St. Status: Resolved.",
        "plumbing": "Ticket #402: Leaking pipe reported in Bldg B. Status: Open."
    }
    
    lookup_key = category.lower().strip()
    return existing_records.get(lookup_key, "No matching historical issues found in database.")

@tool("raise_ticket")
def raise_ticket(department: str, title: str, location: str, priority: str) -> str:
    """
    Creates a new ticket in the system for the respective department.
    Args:
        department: 'maintenance' or 'security'
        title: The description of the issue or event
        location: Where it happened
        priority: 'High', 'Medium', 'Low' for maintenance; 'Critical', 'Warning', 'Info' for security
    """
    import time
    
    department = department.lower().strip()
    if department not in ['maintenance', 'security']:
        department = 'maintenance' # default fallback
        
    now_str = time.strftime("%Y-%m-%d %I:%M %p")
    
    if department == 'security':
        ticket_id = f"S{int(time.time())}"
        ticket_data = {
            "id": ticket_id,
            "event": title,
            "time": now_str,
            "location": location,
            "level": priority,
            "status": "Open"
        }
    else:
        ticket_id = f"{int(time.time())}"
        ticket_data = {
            "id": ticket_id,
            "title": title,
            "date": now_str,
            "location": location,
            "priority": priority,
            "status": "Open"
        }
        
    from database import save_ticket
    save_ticket(department, ticket_data)
        
    return f"Successfully created ticket {ticket_id} in {department} department."

