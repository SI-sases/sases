"""Bundled WireGuard installation helpers for the SASES launcher."""
from __future__ import annotations

import glob
import os
import subprocess
import sys

WG_EXE = os.path.join(os.environ.get("ProgramFiles", r"C:\Program Files"), "WireGuard", "wireguard.exe")


def is_installed() -> bool:
    return os.path.isfile(WG_EXE)


def installer_path(root: str | None = None) -> str | None:
    root = root or os.getcwd()
    base = os.path.join(root, "wireguard")
    for pattern in ("wireguard-amd64-*.msi", "*.msi", "wireguard-installer.exe"):
        matches = glob.glob(os.path.join(base, pattern))
        if matches:
            return matches[0]
    return None


def _is_admin() -> bool:
    try:
        import ctypes
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


def install(root: str | None = None) -> bool:
    if is_installed():
        return True
    path = installer_path(root)
    if not path:
        raise FileNotFoundError("wireguard installer not bundled (wireguard/wireguard-installer.exe)")
    if path.lower().endswith(".msi"):
        if _is_admin():
            subprocess.run(["msiexec.exe", "/i", path, "/qn", "/norestart"], check=True)
        else:
            ps = (
                "Start-Process msiexec.exe -Verb RunAs -Wait -ArgumentList "
                f"'/i \"{path}\" /qn /norestart'"
            )
            subprocess.run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps], check=True)
    else:
        if _is_admin():
            subprocess.run([path, "/S"], check=True)
        else:
            subprocess.run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command",
                            f"Start-Process '{path}' -Verb RunAs -Wait -ArgumentList '/S'"], check=True)
    return is_installed()


def import_tunnel(config_path: str) -> bool:
    if not is_installed():
        raise RuntimeError("WireGuard is not installed")
    if not os.path.isfile(config_path):
        raise FileNotFoundError(config_path)
    if _is_admin():
        subprocess.run([WG_EXE, "/installtunnelservice", config_path], check=True)
    else:
        ps = (
            "Start-Process '" + WG_EXE + "' -Verb RunAs -Wait -ArgumentList "
            "@('/installtunnelservice','" + config_path + "')"
        )
        subprocess.run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps], check=True)
    return True


def ensure_wireguard(root: str | None = None, config_path: str | None = None) -> dict:
    if not is_installed():
        install(root)
    if config_path:
        import_tunnel(config_path)
    return {"installed": is_installed(), "config": bool(config_path)}
