# ropen + smb_listener

A helper toolset for macOS + Linux users working with SMB shares on a remote NAS via SSH.
It allows you to "open" a path on the remote system and have it appear locally via the mounted SMB share.

## Components

### `ropen`
- Executed on the **remote** (NAS/server) system.
- Detects which SMB share a given path belongs to (based on `/etc/samba/smb.conf`).
- Sends a corresponding `smb://hostname/share/path` URL back to your SSH client over TCP.

### `smb_listener.py`
- Runs on your **local** (macOS) system.
- Listens for incoming SMB URLs on `localhost:5555`.
- Mounts the SMB share using AppleScript (if not already mounted).
- Opens the specified file/folder using `open`.

## Usage

### Manual
1. On macOS: start the listener
   ```bash
   python3 ~/bin/smb_listener.py
   ```

2. On NAS (SSH session): run
   ```bash
   ./ropen /path/to/some/file_or_dir
   ```

---

### Recommended: Automatic Integration via SSH Wrapper

You can automatically launch and stop the listener by wrapping your `ssh` function in your local shell config (`~/.zshrc` or `~/.bashrc`):

```bash
ssh() {
    if [[ "$1" == YOUR_NAS_HOSTNAME* ]]; then
        if [[ "$#" -eq 1 ]]; then
            if ! lsof -iTCP:5555 -sTCP:LISTEN -n 2>/dev/null | grep -q LISTEN; then
                log_file="/tmp/smb_listener.log"
                listener_path="$HOME/bin/smb_listener.py"

                echo "[ropen] Starting SMB listener (log: $log_file)"
                PYTHONUNBUFFERED=1 python3 "$listener_path" >> "$log_file" 2>&1 &
                listener_pid=$!
            fi
        fi
        command ssh "$@"

        if [[ -n "$listener_pid" ]]; then
            echo "[ropen] SSH ended, killing SMB listener (PID $listener_pid)"
            kill "$listener_pid" 2>/dev/null
            unset listener_pid
        fi
    else
        command ssh "$@"
    fi
}
```

---

### Optional: Run `smb_listener.py` as a Service

To avoid needing to start it manually each time, you can run it as a background service via `launchd`, `brew services`, or a persistent shell script.

---

### SSH Configuration

To allow the remote NAS to send TCP data back to your macOS client, add the following to your `~/.ssh/config`:

```ssh
Host YOUR_NAS_HOSTNAME
    RemoteForward 5555 localhost:5555
```

---

## Dependencies

- Python 3
- macOS (for `smb_listener.py`; relies on `osascript` and `open`)
- Samba server (`/etc/samba/smb.conf`) on the remote system

