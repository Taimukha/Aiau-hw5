
import json
from pathlib import Path

from langchain_core.messages import HumanMessage, AIMessage

from part2_tools import check_service_status
from part2_agent import build_agent


OUTPUT_DIR = Path("outputs")
OUTPUT_DIR.mkdir(exist_ok=True)


def save_log(filename, lines):
    path = OUTPUT_DIR / filename
    path.write_text(
        "\n".join(lines) + "\n",
        encoding="utf-8",
    )
    print(f"\nLog saved to: {path}")


def run_direct_tool_test():
    lines = []

    def log(message=""):
        print(message)
        lines.append(str(message))

    log("=== S14: Direct Tool Test ===")

    user_message = (
        "Is the password recovery service working? "
        "Please check its current status."
    )

    log(f"\nUSER: {user_message}")

    result = check_service_status(
        service="account_recovery",
        profile="recovery_outage",
    )

    log("\nTOOL: check_service_status")
    log("RESULT:")
    log(json.dumps(result, indent=2))

    assert result["found"] is True
    assert result["service"] == "account_recovery"
    assert result["profile"] == "recovery_outage"
    assert result["status"] == "outage"

    assistant_reply = result["message"]

    log("\nASSISTANT:")
    log(assistant_reply)

    assert "unavailable" in assistant_reply.lower()
    assert "no repair time" in assistant_reply.lower()

    log("\n=== SCENARIO SUMMARY ===")
    log("SERVICE: account_recovery")
    log("PROFILE: recovery_outage")
    log("STATUS: outage")
    log("TICKET CREATED: No")
    log("INVENTED REPAIR TIME: No")

    log("\nS14 DIRECT TOOL TEST: PASS")

    save_log("part2_s14.txt", lines)


def run_ai_agent_test():
    lines = []

    def log(message=""):
        print(message)
        lines.append(str(message))

    log("=== S14: AI Agent Test ===")

    user_message = (
        "Check the password recovery service status. "
        "Tell me if it is working or unavailable. "
        "Do not create a ticket."
    )

    log(f"\nUSER: {user_message}")

    agent = build_agent(
        profile="recovery_outage",
        user_id="user-a",
        thread_id="s14",
    )

    result = agent.invoke(
        {
            "messages": [
                HumanMessage(content=user_message)
            ],
            "tool_rounds": 0,
            "status_checks": {},
        },
        config={"recursion_limit": 20},
    )

    tool_names = []
    tool_arguments = []

    for message in result["messages"]:
        if isinstance(message, AIMessage):
            for call in message.tool_calls:
                tool_names.append(call["name"])
                tool_arguments.append(
                    {
                        "name": call["name"],
                        "args": call["args"],
                    }
                )

    log("\n=== TOOLS CALLED BY AI ===")
    log(json.dumps(tool_arguments, indent=2))

    log("\n=== VERIFIED STATUS ===")
    log(json.dumps(result["status_checks"], indent=2))

    final_answer = str(result["messages"][-1].content)

    log("\n=== AI FINAL ANSWER ===")
    log(final_answer)

    log("\n=== VALIDATION ===")

    checks = {
        "Status tool called": "status_tool" in tool_names,
        "Correct service checked": (
            result["status_checks"].get(
                "account_recovery"
            ) == "outage"
        ),
        "No ticket tool called": (
            "ticket_tool" not in tool_names
        ),
        "Outage explained": any(
            word in final_answer.lower()
            for word in [
                "outage",
                "unavailable",
                "down",
                "not working",
            ]
        ),
        "No invented repair time": not any(
            phrase in final_answer.lower()
            for phrase in [
                "fixed in 1 hour",
                "fixed in 2 hours",
                "back in 30 minutes",
                "restored by tomorrow",
            ]
        ),
    }

    for name, passed in checks.items():
        status = "PASS" if passed else "FAIL"
        log(f"{name}: {status}")

    all_passed = all(checks.values())

    log("\n=== SCENARIO SUMMARY ===")
    log(f"TOOLS USED: {tool_names}")
    log(
        "VERIFIED STATUS: "
        + str(result["status_checks"])
    )
    log(
        "TOOL ROUNDS: "
        + str(result["tool_rounds"])
    )

    if all_passed:
        log("\nS14 AI AGENT TEST: PASS")
    else:
        log("\nS14 AI AGENT TEST: FAIL")

    save_log("part2_s14_agent.txt", lines)

    assert all_passed, (
        "S14 AI agent validation failed. "
        "Check the log for details."
    )


if __name__ == "__main__":
    print("\n" + "=" * 45)
    print("HW5 — SCENARIO S14")
    print("=" * 45)

    run_direct_tool_test()

    print("\n" + "=" * 45)
    print("STARTING AI AGENT TEST")
    print("=" * 45)

    run_ai_agent_test()

    print("\n" + "=" * 45)
    print("S14 TESTING FINISHED")
    print("=" * 45)
