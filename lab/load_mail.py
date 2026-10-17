import json
import sys
from pathlib import Path

from lab import mail_client


def load_dir(directory):
    """Nap moi file .json trong thu muc vao hop thu NOI BO theo thu tu ten file."""
    files = sorted(Path(directory).glob("*.json"))
    for f in files:
        d = json.loads(f.read_text(encoding="utf-8"))
        mail_client.deliver_to_inbox(d["from"], d["subject"], d["body_text"], d.get("body_html"))
    return len(files)


if __name__ == "__main__":
    folder = sys.argv[1] if len(sys.argv) > 1 else "attacks/benign"
    print("Da nap", load_dir(folder), "thu tu", folder)