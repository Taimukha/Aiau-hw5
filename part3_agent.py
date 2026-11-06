
import os
import sys
import sqlite3
from pathlib import Path
from typing import Annotated, TypedDict

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.checkpoint.sqlite import SqliteSaver

from part3_preferences import save_language, get_language

load_dotenv()

DB_PATH = Path("outputs/part3_conversations.sqlite3")
DB_PATH.parent.mkdir(parents=True, exist_ok=True)


class AgentState(TypedDict):
    messages: Annotated[list, add_messages]


def build_graph(checkpointer, user_id):
    api_key = os.getenv("OPENROUTER_API_KEY")

    if not api_key:
        raise RuntimeError(
            "OPENROUTER_API_KEY is missing from .env"
        )

    model = ChatOpenAI(
        model=os.getenv(
            "OPENROUTER_MODEL",
            "deepseek/deepseek-chat",
        ),
        api_key=api_key,
        base_url="https://openrouter.ai/api/v1",
        temperature=0,
    )

    def assistant(state: AgentState):
        language = get_language(user_id)

        system_prompt = """
You are a fictional university IT helpdesk assistant.

Rules:
- Remember previous messages in the current conversation.
- Never invent previous conversation details.
- Never reveal another user's information.
- Never ask for passwords or recovery codes.
- Keep responses short and clear.
"""

        if language == "Kazakh":
            system_prompt += """
The user prefers Kazakh.
Always respond in Kazakh.
"""

        response = model.invoke(
            [SystemMessage(content=system_prompt)]
            + state["messages"]
        )

        return {"messages": [response]}

    builder = StateGraph(AgentState)

    builder.add_node("assistant", assistant)
    builder.add_edge(START, "assistant")
    builder.add_edge("assistant", END)

    return builder.compile(checkpointer=checkpointer)


def send_message(graph, user_id, thread_id, text):
    config = {
        "configurable": {
            "thread_id": user_id + "::" + thread_id
        }
    }

    if "respond in kazakh" in text.lower():
        save_language(user_id, "Kazakh")

    result = graph.invoke(
        {
            "messages": [
                HumanMessage(content=text)
            ]
        },
        config=config,
    )

    print("\nUSER:", text)
    print("AI:", result["messages"][-1].content)


def main():
    scenario = (
        sys.argv[1].upper()
        if len(sys.argv) > 1
        else "S12"
    )

    connection = sqlite3.connect(
        str(DB_PATH),
        check_same_thread=False,
    )

    try:
        checkpointer = SqliteSaver(connection)
        checkpointer.setup()

        if scenario == "S12":
            print("=== S12: Preference across threads ===")

            graph_a = build_graph(checkpointer, "user-a")

            send_message(
                graph_a,
                "user-a",
                "preference-a1",
                "Please respond in Kazakh.",
            )

            send_message(
                graph_a,
                "user-a",
                "preference-a2",
                "Which language did I request?",
            )

        elif scenario == "S13":
            print("=== S13: User isolation ===")

            graph_a = build_graph(checkpointer, "user-a")

            send_message(
                graph_a,
                "user-a",
                "isolation-a",
                (
                    "Please respond in Kazakh. "
                    "My Wi-Fi is not working."
                ),
            )

            graph_b = build_graph(checkpointer, "user-b")

            send_message(
                graph_b,
                "user-b",
                "isolation-b",
                (
                    "Did I specify a language preference "
                    "or report a problem earlier?"
                ),
            )

        else:
            raise ValueError("Use S12 or S13")

    finally:
        connection.close()


if __name__ == "__main__":
    main()
