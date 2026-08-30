import re
import subprocess
import sys
from pathlib import Path


# ==========================================================
# Paths
# ==========================================================

BASE_DIR = Path(__file__).resolve().parent.parent
SIP_FILE = BASE_DIR / "secretary" / "sip.py"


# ==========================================================
# Startup
# ==========================================================

print()
print("[MONITOR] =========================================")
print("[MONITOR] Secretary SIP monitor")
print("[MONITOR] =========================================")
print(f"[MONITOR] Starting: {SIP_FILE}")
print()


# ==========================================================
# SIP URI extraction
# ==========================================================

def extract_uri(value):
    """
    Extract the user/number from a SIP URI.

    Examples:

        <sip:3792731833@79.98.45.133>
        <sip:0873210201@sip.vivavox.it>

    Returns:

        3792731833
        0873210201
    """

    if not value:
        return "Unknown"

    match = re.search(
        r"sip:([^@;>]+)",
        value,
        re.IGNORECASE
    )

    if match:
        return match.group(1)

    return value.strip()


# ==========================================================
# Process one complete SIP INVITE
# ==========================================================

def process_invite(message):
    """
    Inspect a complete SIP INVITE message and display
    the caller and called number.
    """

    from_value = None
    to_value = None
    call_id = None

    for line in message.splitlines():

        line = line.strip()

        if line.lower().startswith("from:"):
            from_value = line[5:].strip()

        elif line.lower().startswith("to:"):
            to_value = line[3:].strip()

        elif line.lower().startswith("call-id:"):
            call_id = line[8:].strip()

    caller = extract_uri(from_value)
    called = extract_uri(to_value)

    print()
    print("[MONITOR] =========================================")
    print("[MONITOR] INCOMING CALL DETECTED")
    print("[MONITOR] =========================================")
    print(f"[MONITOR] Caller : {caller}")
    print(f"[MONITOR] Called : {called}")

    if call_id:
        print(f"[MONITOR] Call-ID: {call_id}")

    print("[MONITOR] =========================================")
    print()


# ==========================================================
# Start sip.py
# ==========================================================

process = None

try:

    process = subprocess.Popen(
        [
            sys.executable,
            "-u",
            str(SIP_FILE)
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1
    )

    # ======================================================
    # SIP message collection
    # ======================================================

    collecting_invite = False
    invite_lines = []

    # ======================================================
    # Read sip.py continuously
    # ======================================================

    while True:

        line = process.stdout.readline()

        # --------------------------------------------------
        # sip.py has terminated
        # --------------------------------------------------

        if line == "":

            if process.poll() is not None:

                print()
                print(
                    f"[MONITOR] sip.py terminated "
                    f"with exit code {process.returncode}"
                )

                break

            continue

        # --------------------------------------------------
        # Always display original sip.py output
        # --------------------------------------------------

        print(
            line,
            end="",
            flush=True
        )

        # ==================================================
        # Look for beginning of an incoming SIP INVITE
        # ==================================================

        if "Request msg INVITE" in line:

            collecting_invite = True

            invite_lines = [line]

            continue

        # ==================================================
        # Collect the rest of the INVITE
        # ==================================================

        if collecting_invite:

            invite_lines.append(line)

            # ------------------------------------------------
            # PJSIP prints this after the complete SIP message
            # ------------------------------------------------

            if "--end msg--" in line:

                message = "".join(invite_lines)

                process_invite(message)

                collecting_invite = False
                invite_lines = []


except KeyboardInterrupt:

    print()
    print("[MONITOR] Stopping...")


except Exception as e:

    print()
    print(
        f"[MONITOR] Error: "
        f"{type(e).__name__}: {e}"
    )


finally:

    # ======================================================
    # Stop sip.py
    # ======================================================

    if process is not None:

        if process.poll() is None:

            print()
            print("[MONITOR] Terminating sip.py...")

            try:

                process.terminate()
                process.wait(timeout=3)

            except subprocess.TimeoutExpired:

                print("[MONITOR] sip.py did not stop cleanly.")

                try:
                    process.kill()
                    process.wait(timeout=3)
                except Exception:
                    pass

            except Exception as e:

                print(
                    f"[MONITOR] Process cleanup error: "
                    f"{e}"
                )

    print()
    print("[MONITOR] Stopped.")