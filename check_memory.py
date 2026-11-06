
import sqlite3
from langgraph.checkpoint.sqlite import SqliteSaver

DB_PATH = "outputs/helpdesk_memory.sqlite3"

connection = sqlite3.connect(
    DB_PATH,
    check_same_thread=False,
)

try:
    checkpointer = SqliteSaver(connection)

    config = {
        "configurable": {
            "thread_id": "s10-demo"
        }
    }

    checkpoint = checkpointer.get(config)

    if checkpoint is None:
        print("FAIL: No saved checkpoint found.")
    else:
        print("PASS: Saved checkpoint found after restart.")
        print("Checkpoint ID:", checkpoint["id"])

finally:
    connection.close()
