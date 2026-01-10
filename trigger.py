#!/usr/bin/env python3
"""
IPC client for triggering Whisper GUI Wrapper.

Usage:
    trigger.py [command]

Commands:
    toggle  - Toggle recording (default)
    cancel  - Cancel current recording
    status  - Get current status

This script is designed to be bound to a system hotkey.
"""

import sys
import time

# IPC socket name (must match app)
IPC_SOCKET_NAME = "whisper-wrapper-ipc"


def send_command(command: str = "toggle", retries: int = 3) -> tuple[bool, str]:
    """
    Send command to running Whisper app via IPC.

    Args:
        command: Command to send (toggle/cancel/status)
        retries: Number of retry attempts

    Returns:
        Tuple of (success, response)
    """
    try:
        from PyQt6.QtNetwork import QLocalSocket
        from PyQt6.QtCore import QCoreApplication

        # Need QCoreApplication for Qt networking
        app = QCoreApplication.instance()
        if app is None:
            app = QCoreApplication(sys.argv)

        for attempt in range(retries):
            socket = QLocalSocket()
            socket.connectToServer(IPC_SOCKET_NAME)

            if socket.waitForConnected(1000):
                socket.write(command.encode())
                socket.flush()

                if socket.waitForReadyRead(2000):
                    response = socket.readAll().data().decode("utf-8")
                    socket.disconnectFromServer()
                    return True, response

                socket.disconnectFromServer()
                return True, "ok"

            # Retry with backoff
            if attempt < retries - 1:
                time.sleep(0.1 * (attempt + 1))

        return False, "Could not connect to Whisper app"

    except ImportError:
        # Fallback to pure Python socket if PyQt6 not available
        return send_command_socket(command)


def send_command_socket(command: str = "toggle") -> tuple[bool, str]:
    """Fallback using Unix socket directly."""
    import socket
    import os

    # Try common socket locations
    socket_paths = [
        f"/tmp/{IPC_SOCKET_NAME}",
        f"/run/user/{os.getuid()}/{IPC_SOCKET_NAME}",
        os.path.expanduser(f"~/.cache/{IPC_SOCKET_NAME}"),
    ]

    # QLocalServer creates sockets in XDG_RUNTIME_DIR or /tmp
    runtime_dir = os.environ.get("XDG_RUNTIME_DIR", "/tmp")
    socket_paths.insert(0, f"{runtime_dir}/{IPC_SOCKET_NAME}")

    for socket_path in socket_paths:
        if os.path.exists(socket_path):
            try:
                sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
                sock.settimeout(2)
                sock.connect(socket_path)
                sock.send(command.encode())
                response = sock.recv(1024).decode("utf-8")
                sock.close()
                return True, response
            except Exception:
                continue

    return False, "Could not connect to Whisper app"


def main():
    """Main entry point."""
    command = sys.argv[1] if len(sys.argv) > 1 else "toggle"

    if command in ("-h", "--help"):
        print(__doc__)
        return 0

    if command not in ("toggle", "cancel", "status"):
        print(f"Unknown command: {command}")
        print("Use: toggle, cancel, or status")
        return 1

    success, response = send_command(command)

    if success:
        if command == "status":
            print(response)
        return 0
    else:
        print(f"Error: {response}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
