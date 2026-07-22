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
