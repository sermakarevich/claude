"""agent-chat — human-in-the-loop question broker.

An MCP server (``agent_chat.server``) lets headless agents ask a human and block
for the answer; the ``agent-chat`` operator console (``agent_chat.cli``) and web
dashboard (``agent_chat.web``) answer them, all over one shared SQLite store
(``agent_chat.store``).
"""

__version__ = "0.2.0"
