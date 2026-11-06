
import json
from pathlib import Path
from typing import TypedDict
from langgraph.graph import StateGraph, START, END


# 1. LOAD JSON DATA

DATA_PATH = Path(__file__).parent / "data" / "helpdesk.json"

with open(DATA_PATH, "r", encoding="utf-8") as file:
    helpdesk_data = json.load(file)


# 2. DEFINE STATE

class HelpdeskState(TypedDict):
    message: str
    category: str
    reply: str


# 3. DEFINE NODES

def read_request(state: HelpdeskState):
    message = state["message"].lower()

    has_wifi = "wifi" in message or "wi-fi" in message
    has_password = "password" in message

    # New rule: detect both topics first
    if has_wifi and has_password:
        category = "clarify"
    elif has_wifi:
        category = "wifi"
    elif has_password:
        category = "password"
    else:
        category = "other"

    return {"category": category}


def choose_route(state: HelpdeskState):
    return state["category"]


def wifi_help(state: HelpdeskState):
    guide = helpdesk_data["instructions"]["wifi"]

    steps = "\n".join(
        f"{i}. {step}"
        for i, step in enumerate(guide["steps"], start=1)
    )

    return {
        "reply": f"{guide['title']}\n{steps}"
    }


def password_help(state: HelpdeskState):
    guide = helpdesk_data["instructions"]["password"]

    steps = "\n".join(
        f"{i}. {step}"
        for i, step in enumerate(guide["steps"], start=1)
    )

    return {
        "reply": f"{guide['title']}\n{steps}"
    }


def other_help(state: HelpdeskState):
    return {
        "reply": "Is your problem related to Wi-Fi or a password?"
    }


# NEW NODE
def clarify_problem(state: HelpdeskState):
    return {
        "reply": (
            "Are you having trouble connecting to Wi-Fi, "
            "or recovering your account password?"
        )
    }


# 4. BUILD GRAPH

builder = StateGraph(HelpdeskState)

builder.add_node("read_request", read_request)
builder.add_node("wifi_help", wifi_help)
builder.add_node("password_help", password_help)
builder.add_node("other_help", other_help)
builder.add_node("clarify_problem", clarify_problem)

builder.add_edge(START, "read_request")

builder.add_conditional_edges(
    "read_request",
    choose_route,
    {
        "wifi": "wifi_help",
        "password": "password_help",
        "other": "other_help",
        "clarify": "clarify_problem",
    }
)

builder.add_edge("wifi_help", END)
builder.add_edge("password_help", END)
builder.add_edge("other_help", END)
builder.add_edge("clarify_problem", END)

app = builder.compile()


# 5. TEST WITH EXECUTION TRACES

if __name__ == "__main__":

    test_messages = [
        "I cannot connect to Wi-Fi.",
        "I forgot my PASSWORD.",
        "My laptop screen is broken.",
        "My Wi-Fi password does not work."
    ]

    expected_categories = [
        "wifi",
        "password",
        "other",
        "clarify"
    ]

    for number, (message, expected) in enumerate(
        zip(test_messages, expected_categories),
        start=1
    ):
        print(f"\n{'=' * 50}")
        print(f"TEST {number}: {message}")
        print(f"{'=' * 50}")

        state = {
            "message": message,
            "category": "",
            "reply": ""
        }

        print("\nINITIAL STATE:")
        print(json.dumps(state, indent=2, ensure_ascii=False))

        execution_order = []

        for event in app.stream(state, stream_mode="updates"):
            for node_name, update in event.items():
                execution_order.append(node_name)
                state.update(update)

                print(f"\nNODE: {node_name}")
                print("UPDATE:")
                print(json.dumps(update, indent=2, ensure_ascii=False))

                print("STATE AFTER NODE:")
                print(json.dumps(state, indent=2, ensure_ascii=False))

        print("\nEXECUTION ORDER:")
        print(
            "START -> "
            + " -> ".join(execution_order)
            + " -> END"
        )

        print("\nExpected category:", expected)
        print("Actual category:", state["category"])

        if state["category"] == expected:
            print("RESULT: PASS")
        else:
            print("RESULT: FAIL")
