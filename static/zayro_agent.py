"""
ZayroAgent — OS-level remote control agent for ZayroDesk
Run this on the HOST machine alongside ZayroDesk browser session.

Install deps:  pip install requests pyautogui
Run:           python zayro_agent.py
"""

import sys, time, threading
try:
    import requests
except ImportError:
    print("ERROR: 'requests' not installed. Run: pip install requests pyautogui")
    sys.exit(1)
try:
    import pyautogui
except ImportError:
    print("ERROR: 'pyautogui' not installed. Run: pip install requests pyautogui")
    sys.exit(1)

import pyautogui
pyautogui.FAILSAFE = False
pyautogui.PAUSE = 0

BASE = "https://zayroplay.com/tools"
POLL_MS = 60   # poll every 60ms

SW, SH = pyautogui.size()

def abs_x(rx): return int(rx * SW)
def abs_y(ry): return int(ry * SH)


def execute(cmd):
    t = cmd.get('type')
    try:
        if t == 'move':
            pyautogui.moveTo(abs_x(cmd['x']), abs_y(cmd['y']), duration=0)

        elif t == 'click':
            btn = 'right' if cmd.get('button') == 2 else 'left'
            pyautogui.click(abs_x(cmd['x']), abs_y(cmd['y']), button=btn)

        elif t == 'dblclick':
            pyautogui.doubleClick(abs_x(cmd['x']), abs_y(cmd['y']))

        elif t == 'scroll':
            dx = cmd.get('dx', 0)
            dy = cmd.get('dy', 0)
            if abs(dy) > abs(dx):
                pyautogui.scroll(int(-dy / 30))
            else:
                pyautogui.hscroll(int(-dx / 30))

        elif t == 'keydown':
            key = cmd.get('key', '')
            ctrl = cmd.get('ctrl', False)
            alt  = cmd.get('alt', False)
            shift= cmd.get('shift', False)
            mods = []
            if ctrl:  mods.append('ctrl')
            if alt:   mods.append('alt')
            if shift: mods.append('shift')
            mapped = _map_key(key)
            if mapped:
                if mods:
                    pyautogui.hotkey(*mods, mapped)
                else:
                    pyautogui.keyDown(mapped)

        elif t == 'keyup':
            mapped = _map_key(cmd.get('key', ''))
            if mapped:
                pyautogui.keyUp(mapped)

        elif t == 'touch':
            pyautogui.moveTo(abs_x(cmd['x']), abs_y(cmd['y']), duration=0)

    except Exception as e:
        pass   # silently ignore bad commands


def _map_key(k):
    """Map browser KeyboardEvent.key to pyautogui key name."""
    special = {
        'Enter': 'enter', 'Backspace': 'backspace', 'Delete': 'delete',
        'Tab': 'tab', 'Escape': 'esc', 'ArrowUp': 'up', 'ArrowDown': 'down',
        'ArrowLeft': 'left', 'ArrowRight': 'right',
        'Home': 'home', 'End': 'end', 'PageUp': 'pageup', 'PageDown': 'pagedown',
        'F1':'f1','F2':'f2','F3':'f3','F4':'f4','F5':'f5','F6':'f6',
        'F7':'f7','F8':'f8','F9':'f9','F10':'f10','F11':'f11','F12':'f12',
        'Control': None, 'Alt': None, 'Shift': None, 'Meta': None,
        ' ': 'space', 'CapsLock': 'capslock', 'Insert': 'insert',
    }
    if k in special:
        return special[k]
    if len(k) == 1:
        return k
    return None


def poll_loop(code, session):
    url = f"{BASE}/api/desk/agent/?code={code}"
    print(f"  Polling: {url}")
    consecutive_errors = 0
    while True:
        try:
            r = session.get(url, timeout=5)
            if r.status_code == 200:
                d = r.json()
                if d.get('closed'):
                    print("\n[ZayroAgent] Session closed by viewer. Exiting.")
                    sys.exit(0)
                for cmd in d.get('commands', []):
                    execute(cmd)
                consecutive_errors = 0
            else:
                consecutive_errors += 1
        except Exception as e:
            consecutive_errors += 1
            if consecutive_errors > 10:
                print(f"\n[ZayroAgent] Connection lost ({e}). Retrying...")
                consecutive_errors = 0
        time.sleep(POLL_MS / 1000)


def main():
    print("=" * 50)
    print("  ZayroAgent — ZayroDesk OS Control Agent")
    print("=" * 50)
    print(f"  Screen: {SW}x{SH}")
    print()
    print("  Steps:")
    print("  1. Open zayroplay.com/tools/zayrodesk/ in your browser")
    print("  2. Click 'Start Sharing' and share your screen")
    print("  3. Copy the 9-digit session code shown")
    print("  4. Paste it below")
    print()

    code = input("  Enter session code (e.g. 123-456-789): ").strip().replace('-', '')
    if len(code) != 9 or not code.isdigit():
        print("  ERROR: Invalid code. Must be 9 digits.")
        sys.exit(1)

    print()
    print(f"  Connecting to session {code[:3]}-{code[3:6]}-{code[6:]}...")

    session = requests.Session()
    # Verify session exists
    try:
        r = session.get(f"{BASE}/api/desk/agent/?code={code}", timeout=8)
        if r.status_code == 404:
            print("  ERROR: Session not found. Make sure you started sharing in the browser first.")
            sys.exit(1)
        print("  Connected! Waiting for viewer to join...")
        print("  Move to UPPER-LEFT CORNER of screen to emergency-stop.")
        print()
    except Exception as e:
        print(f"  ERROR: Cannot reach server ({e})")
        sys.exit(1)

    poll_loop(code, session)


if __name__ == '__main__':
    main()
