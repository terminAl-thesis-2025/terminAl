import os
import subprocess
import asyncio

async def environment_retriever():
    """
    Asynchronously gathers environment-related information for LLM context.
    Returns a dict with relevant system info.
    """
    async def get_parent_process():
        try:
            process = await asyncio.create_subprocess_exec(
                "ps", "-p", str(os.getppid()), "-o", "comm=",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()
            if process.returncode == 0:
                return stdout.decode().strip()
            else:
                return "unknown"
        except Exception:
            return "unknown"

    shell = os.environ.get('SHELL', 'unknown')
    cwd = os.getcwd()
    user = os.environ.get('USER', 'unknown')
    home = os.environ.get('HOME', 'unknown')
    hostname = os.uname().nodename if hasattr(os, "uname") else "unknown"

    parent_process = await get_parent_process()

    return {
        "shell": shell,
        "parent_process": parent_process,
        "current_working_directory": cwd,
        "user": user,
        "home_directory": home,
        "hostname": hostname
    }
