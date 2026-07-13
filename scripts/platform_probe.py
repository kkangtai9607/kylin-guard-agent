from __future__ import annotations

import json
import platform
import shutil
from pathlib import Path


def main() -> None:
    os_release = Path("/etc/os-release")
    result = {
        "system": platform.system(),
        "release": platform.release(),
        "architecture": platform.machine(),
        "kylin_release_detected": os_release.exists()
        and "kylin" in os_release.read_text(errors="replace").lower(),
        "commands": {
            name: shutil.which(name)
            for name in (
                "dnf",
                "yum",
                "apt",
                "ss",
                "netstat",
                "lsof",
                "iostat",
                "journalctl",
                "systemctl",
            )
        },
        "verification_level": "CURRENT_HOST_VERIFIED",
        "loongarch_verified": platform.machine().lower() == "loongarch64",
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
