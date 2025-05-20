# Standardbibliotheken
import os

async def environment_retriever():
    """
    Sammelt asynchron umgebungsbezogene Informationen für den LLM-Kontext.
    Gibt ein Dict mit relevanten Systeminformationen zurück.
    """
    # Ermittelt die Shell des Benutzers oder gibt "unknown" zurück
    shell = os.environ.get('SHELL', 'unknown')
    # Ermittelt das aktuelle Arbeitsverzeichnis
    cwd = os.getcwd()
    # Ermittelt den Benutzernamen oder gibt "unknown" zurück
    user = os.environ.get('USER', 'unknown')
    # Ermittelt den Hostnamen, wenn os.uname() verfügbar ist, sonst "unknown"
    hostname = os.uname().nodename if hasattr(os, "uname") else "unknown"

    # Gibt ein Wörterbuch mit den gesammelten Umgebungsinformationen zurück
    return {
        "shell": shell,
        "root_directory": "/",
        "current_working_directory": cwd,
        "user": user,
        "hostname": hostname
    }