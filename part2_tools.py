
import json
from pathlib import Path
from uuid import uuid4

DATA_DIR = Path(__file__).resolve().parent / "data"


# TOOL 1: FIND INSTRUCTIONS
def find_instructions(topic: str) -> dict:
    """Find helpdesk instructions for a topic."""

    path = DATA_DIR / "helpdesk.json"

    with open(path, "r", encoding="utf-8") as file:
        data = json.load(file)

    topic = topic.lower().strip()

    for category, aliases in data["topic_aliases"].items():
        if topic == category or topic in aliases:
            guide = data["instructions"][category]

            return {
                "found": True,
                "topic": category,
                "instruction_id": guide["instruction_id"],
                "title": guide["title"],
                "steps": guide["steps"]
            }

    return {
        "found": False,
        "topic": topic,
        "message": "No instructions found for this topic."
    }


# TOOL 2: CHECK SERVICE STATUS
def check_service_status(
    service: str,
    profile: str = "normal"
) -> dict:
    """Check a fictional service status snapshot."""

    path = DATA_DIR / "service_status.json"

    with open(path, "r", encoding="utf-8") as file:
        data = json.load(file)

    service = service.lower().strip()
    profile = profile.lower().strip()

    aliases = {
        "wifi": "wifi",
        "wi-fi": "wifi",
        "password": "account_recovery",
        "recovery": "account_recovery",
        "account_recovery": "account_recovery"
    }

    service = aliases.get(service, service)

    if profile not in data["profiles"]:
        return {
            "found": False,
            "error": "Unknown status profile."
        }

    services = data["profiles"][profile]

    if service not in services:
        return {
            "found": False,
            "error": "Unknown service."
        }

    result = services[service]

    return {
        "found": True,
        "service": service,
        "profile": profile,
        "status": result["status"],
        "message": result["message"]
    }


# TOOL 3: PREPARE LOCAL TICKET
def prepare_ticket(
    user_id: str,
    thread_id: str,
    category: str,
    summary: str,
    steps_tried: list,
    service_status: str,
    status_profile: str,
    reference_ids: list
) -> dict:
    """Prepare a local ticket draft without submitting it."""

    path = DATA_DIR / "ticket_template.json"

    with open(path, "r", encoding="utf-8") as file:
        template = json.load(file)

    # Validate required details
    missing = []

    if not category or not category.strip():
        missing.append("category")

    if not summary or not summary.strip():
        missing.append("summary")

    if missing:
        return {
            "created": False,
            "submitted": False,
            "missing_fields": missing,
            "message": "Please provide the missing ticket details."
        }

    # Create a fresh copy of the template
    ticket = template["ticket"].copy()

    ticket["ticket_id"] = "DRAFT-" + uuid4().hex[:8].upper()
    ticket["status"] = "draft"
    ticket["user_id"] = user_id
    ticket["thread_id"] = thread_id
    ticket["category"] = category
    ticket["summary"] = summary
    ticket["steps_tried"] = steps_tried
    ticket["service_status"] = service_status
    ticket["status_profile"] = status_profile
    ticket["reference_ids"] = reference_ids

    return {
        "created": True,
        "submitted": False,
        "ticket": ticket
    }


# TEST ALL THREE TOOLS
if __name__ == "__main__":

    print("=== TOOL 1: FIND INSTRUCTIONS ===")

    for topic in ["wifi", "password", "screen"]:
        result = find_instructions(topic)

        print(json.dumps(
            result,
            indent=2,
            ensure_ascii=False
        ))

    print("\n=== TOOL 2: CHECK SERVICE STATUS ===")

    tests = [
        ("wifi", "normal"),
        ("wifi", "wifi_outage"),
        ("wifi", "status_unavailable"),
        ("password", "recovery_outage")
    ]

    for service, profile in tests:
        result = check_service_status(service, profile)

        print(json.dumps(
            result,
            indent=2,
            ensure_ascii=False
        ))

    print("\n=== TOOL 3: PREPARE TICKET ===")

    ticket = prepare_ticket(
        user_id="demo-user-a",
        thread_id="s06",
        category="wifi",
        summary="Campus-Demo Wi-Fi does not connect.",
        steps_tried=[
            "Enabled Wi-Fi",
            "Forgot the saved network",
            "Tried reconnecting"
        ],
        service_status="operational",
        status_profile="normal",
        reference_ids=["GUIDE-WIFI"]
    )

    print(json.dumps(
        ticket,
        indent=2,
        ensure_ascii=False
    ))

    print("\n=== TOOL 3: MISSING DETAILS TEST ===")

    missing_ticket = prepare_ticket(
        user_id="demo-user-a",
        thread_id="s09",
        category="",
        summary="",
        steps_tried=[],
        service_status="operational",
        status_profile="normal",
        reference_ids=[]
    )

    print(json.dumps(
        missing_ticket,
        indent=2,
        ensure_ascii=False
    ))
