
import sqlite3
from pathlib import Path

from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.checkpoint.sqlite import SqliteSaver

from langchain_core.messages import HumanMessage
from typing import Annotated, TypedDict


DB_PATH = Path("outputs/helpdesk_memory.sqlite3")
DB_PATH.parent.mkdir(parents=True, exist_ok=True)


class MemoryState(TypedDict):
    messages: Annotated[list, add_messages]


def remember_message(state: MemoryState):
    return {"messages": []}


def build_graph(checkpointer):
    builder = StateGraph(MemoryState)

    builder.add_node("remember", remember_message)

    builder.add_edge(START, "remember")
    builder.add_edge("remember", END)

    return builder.compile(checkpointer=checkpointer)


def main():
    connection = sqlite3.connect(
        str(DB_PATH),
        check_same_thread=False,
    )

    try:
        checkpointer = SqliteSaver(connection)
        checkpointer.setup()

        graph = build_graph(checkpointer)

        config = {
            "configurable": {
                "thread_id": "s10-demo"
            }
        }

        print("=== FIRST MESSAGE ===")

        graph.invoke(
            {
                "messages": [
                    HumanMessage(
                        content=(
                            "My Wi-Fi is not working. "
                            "I enabled Wi-Fi and tried reconnecting."
                        )
                    )
                ]
            },
            config=config,
        )

        print("Message saved.")

        print("\n=== SAVED CONVERSATION ===")

        saved_state = graph.get_state(config)

        for message in saved_state.values["messages"]:
            print(
                message.type.upper(),
                ":",
                message.content,
            )

        print("\nSQLite checkpoint OK")

    finally:
        connection.close()


if __name__ == "__main__":
    main()
