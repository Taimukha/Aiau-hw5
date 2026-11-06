
from part2_tools import (
    find_instructions,
    check_service_status,
    prepare_ticket,
)


def test_wifi_instructions():
    result = find_instructions("wifi")

    assert result["found"] is True
    assert result["topic"] == "wifi"
    assert result["instruction_id"] == "GUIDE-WIFI"
    assert len(result["steps"]) > 0


def test_password_instructions():
    result = find_instructions("password")

    assert result["found"] is True
    assert result["topic"] == "password"
    assert result["instruction_id"] == "GUIDE-PASSWORD"


def test_unknown_instructions():
    result = find_instructions("screen")

    assert result["found"] is False


def test_normal_wifi_status():
    result = check_service_status("wifi", "normal")

    assert result["found"] is True
    assert result["status"] == "operational"


def test_wifi_outage():
    result = check_service_status("wifi", "wifi_outage")

    assert result["found"] is True
    assert result["status"] == "outage"


def test_unknown_status():
    result = check_service_status(
        "wifi",
        "status_unavailable"
    )

    assert result["found"] is True
    assert result["status"] == "unknown"


def test_recovery_outage():
    result = check_service_status(
        "account_recovery",
        "recovery_outage"
    )

    assert result["found"] is True
    assert result["status"] == "outage"


def test_ticket_draft():
    result = prepare_ticket(
        user_id="test-user",
        thread_id="test-thread",
        category="wifi",
        summary="Wi-Fi connection failed",
        steps_tried=[
            "Enabled Wi-Fi",
            "Tried reconnecting",
        ],
        service_status="operational",
        status_profile="normal",
        reference_ids=["GUIDE-WIFI"],
    )

    assert result["created"] is True
    assert result["submitted"] is False

    ticket = result["ticket"]

    assert ticket["status"] == "draft"
    assert ticket["category"] == "wifi"
    assert ticket["ticket_id"].startswith("DRAFT-")
    assert ticket["user_id"] == "test-user"
    assert ticket["thread_id"] == "test-thread"
    assert len(ticket["steps_tried"]) == 2
    assert ticket["service_status"] == "operational"


def test_missing_ticket_fields():
    result = prepare_ticket(
        user_id="test-user",
        thread_id="test-thread",
        category="",
        summary="",
        steps_tried=[],
        service_status="operational",
        status_profile="normal",
        reference_ids=[],
    )

    assert result["created"] is False
    assert result["submitted"] is False
    assert "category" in result["missing_fields"]
    assert "summary" in result["missing_fields"]
