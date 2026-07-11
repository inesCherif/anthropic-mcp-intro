import os
import asyncio
from dotenv import load_dotenv
import streamlit as st

from mcp_client import MCPClient
from core.claude import Claude
from core.cli_chat import CliChat

load_dotenv()

CLAUDE_MODEL = os.getenv("CLAUDE_MODEL", "")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")

assert CLAUDE_MODEL, "Error: CLAUDE_MODEL cannot be empty. Update .env"
assert ANTHROPIC_API_KEY, "Error: ANTHROPIC_API_KEY cannot be empty. Update .env"


def get_mcp_command():
    if os.getenv("USE_UV", "0") == "1":
        return "uv", ["run", "mcp_server.py"]
    return "python", ["mcp_server.py"]


async def create_clients():
    command, args = get_mcp_command()
    doc_client = MCPClient(command=command, args=args)
    await doc_client.connect()
    clients = {"doc_client": doc_client}
    return clients, doc_client


def initialize_app():
    if "initialized" not in st.session_state:
        clients, doc_client = asyncio.run(create_clients())
        st.session_state.clients = clients
        st.session_state.doc_client = doc_client
        st.session_state.chat = CliChat(
            doc_client=doc_client,
            clients=clients,
            claude_service=Claude(model=CLAUDE_MODEL),
        )
        st.session_state.history = []
        st.session_state.initialized = True


def get_doc_list():
    try:
        return asyncio.run(st.session_state.chat.list_docs_ids())
    except Exception:
        return []


def run_query(query: str):
    if not query:
        return ""
    response = asyncio.run(st.session_state.chat.run(query))
    st.session_state.history.append({"user": query, "assistant": response})
    return response


def main():
    st.set_page_config(page_title="MCP Streamlit Chat", page_icon="💬")
    st.title("MCP Streamlit Chat")
    st.write("A simple Streamlit interface for the Anthropic + MCP chat app.")

    initialize_app()

    with st.sidebar:
        st.header("Instructions")
        st.write(
            "Enter a question, mention documents with @doc_id, or use MCP commands like `/format plan.md`."
        )
        st.markdown("---")
        st.subheader("Available documents")
        docs = get_doc_list()
        if docs:
            for doc_id in docs:
                st.write(f"- {doc_id}")
        else:
            st.write("No documents available.")

    query = st.text_area(
        "Your question",
        height=140,
        placeholder="Ask about @report.pdf or use /format plan.md",
    )

    if st.button("Send"):
        if query.strip():
            with st.spinner("Processing your question..."):
                run_query(query.strip())
            st.experimental_rerun()

    if st.session_state.history:
        st.subheader("Conversation")
        for entry in reversed(st.session_state.history):
            st.markdown(f"**You:** {entry['user']}")
            st.markdown(f"**Assistant:** {entry['assistant']}")


if __name__ == "__main__":
    main()
