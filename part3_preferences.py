
import json
import sqlite3
import sys
from pathlib import Path

DB_PATH = Path("outputs/user_preferences.sqlite3")
DB_PATH.parent.mkdir(parents=True, exist_ok=True)


def connect():
    connection = sqlite3.connect(str(DB_PATH))
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS user_preferences (
            user_id TEXT PRIMARY KEY,
            language TEXT NOT NULL
        )
        """
    )
    connection.commit()
    return connection


def save_language(user_id, language):
    with connect() as connection:
        connection.execute(
            """
            INSERT INTO user_preferences (user_id, language)
            VALUES (?, ?)
            ON CONFLICT(user_id)
            DO UPDATE SET language = excluded.language
            """,
            (user_id, language),
        )


def get_language(user_id):
    with connect() as connection:
        row = connection.execute(
            """
            SELECT language
            FROM user_preferences
            WHERE user_id = ?
            """,
            (user_id,),
        ).fetchone()

    return row[0] if row else None


def run_s12_save():
    print("=== S12: Save preference ===")

    save_language("user-a", "Kazakh")

    print("USER A: Please respond in Kazakh.")
    print("Saved language:", get_language("user-a"))


def run_s12_load():
    print("=== S12: Load preference after restart ===")

    language = get_language("user-a")

    print("USER A, NEW THREAD")
    print("Saved language:", language)

    assert language == "Kazakh"
    print("PASS: Preference survived process restart.")


def run_s13():
    print("=== S13: User isolation ===")

    save_language("user-a", "Kazakh")

    language_a = get_language("user-a")
    language_b = get_language("user-b")

    print("USER A language:", language_a)
    print("USER B language:", language_b)

    assert language_a == "Kazakh"
    assert language_b is None

    print("PASS: User B cannot access User A preference.")


if __name__ == "__main__":
    scenario = sys.argv[1].upper() if len(sys.argv) > 1 else "S12_SAVE"

    if scenario == "S12_SAVE":
        run_s12_save()
    elif scenario == "S12_LOAD":
        run_s12_load()
    elif scenario == "S13":
        run_s13()
    else:
        raise ValueError("Use S12_SAVE, S12_LOAD, or S13")
