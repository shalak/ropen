#!/usr/bin/env python3
"""
This script listens for SMB URLs sent over TCP (on localhost:5555), mounts the corresponding
SMB share if needed (on macOS), and opens the target file or folder.

Expected input format:
    smb://hostname/share/path/to/file

Key Features:
- Parses SMB URLs into host/share/path components
- Mounts the SMB share using AppleScript if it's not already mounted
- Opens the resolved local path using `open`

Intended to be run in the background as a receiver.
"""

import socket
import subprocess
import urllib.parse
from pathlib import Path
from datetime import datetime

LISTEN_PORT = 5555

def log(msg: str) -> None:
    """Log a timestamped message to stdout."""
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {msg}")

def parse_smb_url(url: str) -> tuple[str, str, str]:
    """
    Parse smb://host/share/path into components.

    Args:
        url (str): An SMB URL.

    Returns:
        tuple: (host, share, relative_path)

    Raises:
        ValueError: If URL scheme is not smb.
    """
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme != "smb":
        raise ValueError("Invalid scheme")

    parts = parsed.path.strip("/").split("/", 1)
    share = parts[0]
    path = parts[1] if len(parts) > 1 else ""
    return parsed.hostname, share, path

def mount_share(host: str, share: str) -> Path | None:
    """
    Mount the SMB share to /Volumes/share using AppleScript (macOS).

    Args:
        host (str): SMB host
        share (str): Share name

    Returns:
        Path or None: Mount point path if successful, else None.
    """
    mount_point = Path(f"/Volumes/{share}")
    if not mount_point.exists():
        log(f"Mounting //{host}/{share} to {mount_point}")
        try:
            subprocess.run([
                "osascript", "-e",
                f'mount volume "smb://{host}/{share}"'
            ], check=True)
        except subprocess.CalledProcessError as e:
            log(f"Failed to mount share: {e}")
            return None
    return mount_point

def open_local_path(mount_point: Path, rel_path: Path) -> None:
    """
    Open a file/folder under a mounted share.

    Args:
        mount_point (Path): Mount point under /Volumes
        rel_path (Path): Relative path within the share
    """
    target = mount_point / rel_path
    if target.exists():
        log(f"Opening {target}")
        subprocess.run(["open", str(target)])
    else:
        log(f"Path does not exist: {target}")

def handle_smb_url(url: str) -> None:
    """
    Handle a received SMB URL: parse, mount, and open path.

    Args:
        url (str): SMB URL
    """
    try:
        host, share, rel_path = parse_smb_url(url)
        mount_point = mount_share(host, share)
        if mount_point:
            open_local_path(mount_point, Path(rel_path))
    except Exception as e:
        log(f"Error handling URL: {e}")

def main() -> None:
    """
    Main listener loop. Accepts a single connection at a time
    and responds to smb:// URLs.
    """
    log(f"Listening on port {LISTEN_PORT}...")
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
        server.bind(("127.0.0.1", LISTEN_PORT))
        server.listen(1)
        try:
            while True:
                conn, _ = server.accept()
                with conn:
                    data = conn.recv(2048).decode("utf-8").strip()
                    if data:
                        log(f"Received: {data}")
                        if data.startswith("smb://"):
                            handle_smb_url(data)
                        else:
                            log("Ignoring non-smb request")
        except KeyboardInterrupt:
            log("\nListener stopped by user.")

if __name__ == "__main__":
    main()
