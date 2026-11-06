
import os
import json
import sys
from typing import Annotated, TypedDict, List, Optional

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.messages import (
    HumanMessage,
    SystemMessage,
    AIMessage,
    ToolMessage,
)
from langchain_core.tools import tool
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages

from part2_tools import (
    find_instructions,
    check_service_status,
    prepare_ticket,
)

load_dotenv()

MAX_TOOL_ROUNDS = 5

CATEGORY_ALIASES = {
    "wifi": "wifi",
    "wi-fi": "wifi",
    "wireless": "wifi",
    "network": "wifi",
    "password": "password",
    "account_recovery": "password",
    "account recovery": "password",
    "recovery": "password",
}


def normalize_category(value: str) -> Optional[str]:
    return CATEGORY_ALIASES.get(value.lower().strip())


class AgentState(TypedDict):
    messages: Annotated[list, add_messages]
    tool_rounds: int
    status_checks: dict


SYSTEM_PROMPT = """
You are a fictional university IT helpdesk assistant.

You have three tools:
1. instructions_tool: find troubleshooting instructions.
2. status_tool: check fictional service status.
3. ticket_tool: prepare a local ticket draft.

Rules:

1. Call instructions_tool when the user requests instructions.

2. Call status_tool when the user asks about service status
   or when ticket creation depends on service status.

3. When a ticket is conditional on the service being
   operational, check the status before creating the ticket.

4. If the user requests a ticket but has not described the
   issue, ask for the missing details. Do not create a ticket.

5. If the user previously requested a ticket and later
   provides the issue and troubleshooting steps, remember
   the earlier request. Check service status and prepare
   a ticket if the service is operational.

6. Reuse facts from earlier conversation messages.
   Do not ask the user to repeat information already given.

7. Supported ticket categories are wifi and password.
   Use "wifi" for Wi-Fi, wireless, or network issues.
   Use "password" for password or account recovery issues.

8. Never invent troubleshooting steps or service status.
   Include only steps explicitly reported by the user.
   Do not confuse recommended steps with completed steps.

9. Do not prepare a conditional ticket when the service
   status is outage or unknown.

10. Never request passwords or recovery codes.

11. Tickets are local drafts only.
    Never claim they were submitted to a real helpdesk.

12. Keep responses short and clear.
"""


def build_agent(profile: str, user_id: str, thread_id: str):
    """
    Create a separate LangGraph agent for one scenario.
    Each agent maintains its own verified service status.
    """

    verified_status = {}

    # TOOL 1: Instructions
    @tool
    def instructions_tool(topic: str) -> dict:
        """Find local Wi-Fi or password troubleshooting instructions."""
        return find_instructions(topic)

    # TOOL 2: Service status
    @tool
    def status_tool(service: str) -> dict:
        """Check fictional Wi-Fi or account recovery service status."""

        result = check_service_status(
            service=service,
            profile=profile,
        )

        if result.get("found"):
            verified_status[result["service"]] = result["status"]

        return result

    # TOOL 3: Ticket
    @tool
    def ticket_tool(
        category: str,
        summary: str,
        steps_tried: List[str],
        reference_ids: Optional[List[str]] = None,
    ) -> dict:
        """Prepare a local support ticket draft; never submit it."""

        normalized = normalize_category(category)

        if normalized is None:
            return {
                "created": False,
                "submitted": False,
                "message": "Unsupported ticket category.",
            }

        service = (
            "wifi"
            if normalized == "wifi"
            else "account_recovery"
        )

        actual_status = verified_status.get(service)

        if actual_status is None:
            return {
                "created": False,
                "submitted": False,
                "message": (
                    "Service status must be checked "
                    "before preparing a ticket."
                ),
            }

        if actual_status != "operational":
            return {
                "created": False,
                "submitted": False,
                "service_status": actual_status,
                "message": (
                    "Ticket not prepared because the service "
                    "is not confirmed operational."
                ),
            }

        if not summary or not summary.strip():
            return {
                "created": False,
                "submitted": False,
                "missing_fields": ["summary"],
                "message": "Please describe the problem.",
            }

        if not steps_tried:
            return {
                "created": False,
                "submitted": False,
                "missing_fields": ["steps_tried"],
                "message": (
                    "Please describe the troubleshooting "
                    "steps already attempted."
                ),
            }

        return prepare_ticket(
            user_id=user_id,
            thread_id=thread_id,
            category=normalized,
            summary=summary.strip(),
            steps_tried=steps_tried,
            service_status=actual_status,
            status_profile=profile,
            reference_ids=reference_ids or [],
        )

    tools = [
        instructions_tool,
        status_tool,
        ticket_tool,
    ]

    tool_map = {
        item.name: item
        for item in tools
    }

    api_key = os.getenv("OPENROUTER_API_KEY")

    if not api_key:
        raise RuntimeError(
            "OPENROUTER_API_KEY is missing from .env"
        )

    model_name = os.getenv(
        "OPENROUTER_MODEL",
        "deepseek/deepseek-chat",
    )

    model = ChatOpenAI(
        model=model_name,
        api_key=api_key,
        base_url="https://openrouter.ai/api/v1",
        temperature=0,
    ).bind_tools(tools)

    # NODE 1: Call model
    def call_model(state: AgentState):
        response = model.invoke(
            [SystemMessage(content=SYSTEM_PROMPT)]
            + state["messages"]
        )

        return {"messages": [response]}

    # NODE 2: Execute tools
    def run_tools(state: AgentState):
        last_message = state["messages"][-1]
        results = []

        for call in last_message.tool_calls:
            name = call["name"]
            args = call["args"]

            print("\nTOOL:", name)
            print(
                "ARGS:",
                json.dumps(args, ensure_ascii=False),
            )

            try:
                if name not in tool_map:
                    result = {
                        "error": "Unknown tool."
                    }
                else:
                    result = tool_map[name].invoke(args)

            except Exception as error:
                result = {
                    "error": str(error)
                }

            print(
                "RESULT:",
                json.dumps(result, ensure_ascii=False),
            )

            results.append(
                ToolMessage(
                    content=json.dumps(
                        result,
                        ensure_ascii=False,
                    ),
                    tool_call_id=call["id"],
                )
            )

        return {
            "messages": results,
            "tool_rounds": state["tool_rounds"] + 1,
            "status_checks": dict(verified_status),
        }

    # Conditional routing
    def choose_next(state: AgentState):
        last_message = state["messages"][-1]

        if not last_message.tool_calls:
            return "end"

        if state["tool_rounds"] >= MAX_TOOL_ROUNDS:
            return "limit"

        return "tools"

    # Tool execution limit
    def limit_response(state: AgentState):
        return {
            "messages": [
                AIMessage(
                    content=(
                        "I reached the tool execution limit. "
                        "Please try a simpler request."
                    )
                )
            ]
        }

    # Build LangGraph
    builder = StateGraph(AgentState)

    builder.add_node("model", call_model)
    builder.add_node("tools", run_tools)
    builder.add_node("limit", limit_response)

    builder.add_edge(START, "model")

    builder.add_conditional_edges(
        "model",
        choose_next,
        {
            "tools": "tools",
            "limit": "limit",
            "end": END,
        },
    )

    builder.add_edge("tools", "model")
    builder.add_edge("limit", END)

    return builder.compile()


def run_scenario(scenario_id: str, profile: str):
    print("SCENARIO:", scenario_id)
    print(
        "MODEL:",
        os.getenv(
            "OPENROUTER_MODEL",
            "deepseek/deepseek-chat",
        ),
    )
    print("PROFILE:", profile)

    agent = build_agent(
        profile=profile,
        user_id="demo-user-a",
        thread_id=scenario_id.lower(),
    )

    # Select scenario messages
    if scenario_id == "S08":
        messages = [
            (
                "Check the Wi-Fi service status. "
                "If the service is operational, prepare a ticket "
                "for my Wi-Fi connection problem. "
                "I enabled Wi-Fi and tried reconnecting, "
                "but it still does not work."
            )
        ]

    elif scenario_id == "S09":
        messages = [
            "Prepare a support ticket.",
            (
                "The issue is Wi-Fi. "
                "I enabled it and tried reconnecting, "
                "but it still fails."
            ),
        ]

    else:
        # S06 and S07
        messages = [
            "Show me the Wi-Fi troubleshooting steps.",
            (
                "I enabled Wi-Fi and forgot the saved network, "
                "but Campus-Demo still will not connect. "
                "Check whether Wi-Fi is down. "
                "If it is operating, prepare a ticket "
                "about this problem."
            ),
        ]

    conversation = []
    all_tool_calls = []

    for number, message in enumerate(messages, start=1):
        print(f"\n=== MESSAGE {number} ===")
        print("USER:", message)

        conversation.append(
            HumanMessage(content=message)
        )

        previous_length = len(conversation)

        result = agent.invoke(
            {
                "messages": conversation,
                "tool_rounds": 0,
                "status_checks": {},
            },
            config={"recursion_limit": 20},
        )

        new_messages = result["messages"][previous_length:]

        for item in new_messages:
            if isinstance(item, AIMessage):
                for call in item.tool_calls:
                    all_tool_calls.append(call["name"])

        conversation = result["messages"]

        print("\nFINAL ANSWER:")
        print(conversation[-1].content)

        print(
            "TOOL ROUNDS:",
            result["tool_rounds"],
        )

        print(
            "VERIFIED STATUS:",
            result["status_checks"],
        )

    print("\n=== SCENARIO SUMMARY ===")
    print("TOOLS USED:", all_tool_calls)

    if scenario_id == "S06":
        print(
            "EXPECTED: status operational, "
            "ticket draft created."
        )

    elif scenario_id == "S07":
        print(
            "EXPECTED: status outage, "
            "no conditional ticket draft."
        )

    elif scenario_id == "S08":
        print(
            "EXPECTED: status unknown, "
            "no conditional ticket draft."
        )

    elif scenario_id == "S09":
        print(
            "EXPECTED: ask for missing details first, "
            "then check status and prepare a draft ticket."
        )


if __name__ == "__main__":
    scenario = (
        sys.argv[1].upper()
        if len(sys.argv) > 1
        else "S06"
    )

    profiles = {
        "S06": "normal",
        "S07": "wifi_outage",
        "S08": "status_unavailable",
        "S09": "normal",
    }

    if scenario not in profiles:
        raise ValueError(
            "Supported scenarios: S06, S07, S08, S09"
        )

    run_scenario(
        scenario_id=scenario,
        profile=profiles[scenario],
    )
