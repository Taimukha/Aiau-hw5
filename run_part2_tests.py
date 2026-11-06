
import subprocess
import sys
from pathlib import Path

OUTPUT_DIR = Path("outputs")
OUTPUT_DIR.mkdir(exist_ok=True)

SCENARIOS = {
    "S06": {
        "required": ['"status": "operational"', '"created": true'],
        "forbidden": [],
    },
    "S07": {
        "required": ['"status": "outage"'],
        "forbidden": ['"created": true'],
    },
    "S08": {
        "required": ['"status": "unknown"'],
        "forbidden": ['"created": true'],
    },
    "S09": {
        "required": [
            "=== MESSAGE 2 ===",
            '"status": "operational"',
            '"created": true',
        ],
        "forbidden": [],
    },
}


def main():
    passed = 0

    for scenario_id, checks in SCENARIOS.items():
        print(f"\nRunning {scenario_id}...")

        result = subprocess.run(
            [sys.executable, "part2_agent.py", scenario_id],
            capture_output=True,
            text=True,
        )

        log_path = OUTPUT_DIR / f"part2_{scenario_id.lower()}.txt"
        log_path.write_text(
            result.stdout + "\n" + result.stderr,
            encoding="utf-8",
        )

        output = result.stdout

        missing = [
            value for value in checks["required"]
            if value not in output
        ]

        unexpected = [
            value for value in checks["forbidden"]
            if value in output
        ]

        if result.returncode == 0 and not missing and not unexpected:
            print(f"{scenario_id}: PASS")
            passed += 1
        else:
            print(f"{scenario_id}: FAIL")
            print("Missing:", missing)
            print("Unexpected:", unexpected)
            print("Exit code:", result.returncode)
            print("See log:", log_path)

    print(f"\nRESULT: {passed}/{len(SCENARIOS)} passed")


if __name__ == "__main__":
    main()
