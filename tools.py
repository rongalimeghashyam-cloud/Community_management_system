from crewai.tools import tool

@tool("check_database_for_duplicates")
def check_database_for_duplicates(category: str) -> str:
    """
    Queries the city database to check for existing open complaints 
    matching a specific infrastructure category.
    """
    existing_records = {
        "roads": "Ticket #1024: Massive pothole reported on Main Street. Status: Open.",
        "utilities": "No open tickets found for this category.",
        "sanitation": "Ticket #0988: Trash missed on Elm St. Status: Resolved."
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
    import json
    import os
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
            "level": priority
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
