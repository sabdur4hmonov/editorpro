"""Mahalliy, faqat o'qiydigan MCP stdio server (2025-11-25; stdlib)."""
from __future__ import annotations

import argparse
from contextlib import redirect_stdout
import io
import json
import sys

import handoff
import sync_skills

GUIDES = {
    "rules": "AGENTS.md", "playbook": "docs/PLAYBOOK.md",
    "sample_style": "docs/NAMUNA_USLUBI.md", "quality": "docs/EDIT_QUALITY.md",
    "memory": "docs/AGENT_MEMORY.md", "setup": "docs/AGENT_SETUP.md", "promo": "docs/PROMO.md", "takes": "docs/TAKES.md",
}
VERSIONS = ("2024-11-05", "2025-03-26", "2025-06-18", "2025-11-25")
TOOLS = [
    {"name": "project_state", "description": "HOLAT, band belgisi, oxirgi ishlar va git holatini o'qish.",
     "inputSchema": {"type": "object", "additionalProperties": False}},
    {"name": "read_guide", "description": "Umumiy qoida, montaj sifati yoki agent tajribasini o'qish.",
     "inputSchema": {"type": "object", "properties": {"guide": {"type": "string", "enum": list(GUIDES)}},
                     "required": ["guide"], "additionalProperties": False}},
    {"name": "skills_status", "description": "Claude/Codex skilllari manba bilan bir xilmi: faqat tekshiradi.",
     "inputSchema": {"type": "object", "additionalProperties": False}},
]
for tool in TOOLS:
    tool["annotations"] = {"readOnlyHint": True, "destructiveHint": False, "openWorldHint": False}


def call_tool(name: str, arguments: dict) -> str:
    if not isinstance(arguments, dict):
        raise ValueError("arguments object bo'lishi kerak")
    if name == "read_guide":
        if set(arguments) != {"guide"} or arguments["guide"] not in GUIDES:
            raise ValueError("Faqat ro'yxatdagi guide nomi qabul qilinadi")
        path = sync_skills.ROOT / GUIDES[arguments["guide"]]
        # Reject symlink/junction redirection outside the fixed project root.
        if path.resolve() != sync_skills.ROOT / GUIDES[arguments["guide"]]:
            raise ValueError("Yo'naltirilgan fayl o'qilmaydi")
        return path.read_text(encoding="utf-8")
    if arguments:
        raise ValueError("Bu tool argument qabul qilmaydi")
    if name == "project_state":
        buffer = io.StringIO()
        with redirect_stdout(buffer):
            handoff.show()
        return buffer.getvalue()
    if name == "skills_status":
        return json.dumps({"synced": not (changed := sync_skills.sync()), "outdated": changed}, ensure_ascii=False)
    raise ValueError("Noma'lum tool")


def response(request, initialized: bool):
    if not isinstance(request, dict) or request.get("jsonrpc") != "2.0" or not isinstance(request.get("method"), str):
        return {"jsonrpc": "2.0", "id": None, "error": {"code": -32600, "message": "Invalid Request"}}, initialized
    if "id" not in request:
        return None, initialized
    result = {"jsonrpc": "2.0", "id": request["id"]}
    method, params = request["method"], request.get("params", {})
    if not isinstance(params, dict):
        result["error"] = {"code": -32602, "message": "Invalid params"}
    elif method == "initialize":
        version = params.get("protocolVersion")
        result["result"] = {"protocolVersion": version if version in VERSIONS else VERSIONS[-1],
                            "capabilities": {"tools": {}},
                            "serverInfo": {"name": "montaj-project", "version": "1.0.0"}}
        initialized = True
    elif method == "ping":
        result["result"] = {}
    elif not initialized:
        result["error"] = {"code": -32000, "message": "Initialize first"}
    elif method == "tools/list":
        result["result"] = {"tools": TOOLS}
    elif method == "tools/call":
        if not isinstance(params.get("name"), str) or not any(tool["name"] == params["name"] for tool in TOOLS):
            result["error"] = {"code": -32602, "message": "Unknown tool"}
            return result, initialized
        try:
            text = call_tool(params.get("name"), params.get("arguments", {}))
            result["result"] = {"content": [{"type": "text", "text": text}], "isError": False}
        except (ValueError, OSError, TypeError) as error:
            result["result"] = {"content": [{"type": "text", "text": str(error)}], "isError": True}
    else:
        result["error"] = {"code": -32601, "message": "Method not found"}
    return result, initialized


def main() -> int:
    argparse.ArgumentParser(description=__doc__).parse_args()
    sys.stdin.reconfigure(encoding="utf-8")
    sys.stdout.reconfigure(encoding="utf-8")
    initialized = False
    for line in sys.stdin:
        try:
            reply, initialized = response(json.loads(line), initialized)
        except json.JSONDecodeError:
            reply = {"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": "Parse error"}}
        if reply is not None:
            print(json.dumps(reply, ensure_ascii=False), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
