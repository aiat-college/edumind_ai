"""
EDUMIND AI — FRONTEND (gradio_ui.py)
Gradio UI only

This file handles:
1. Chat interface (UI)
2. Chat history sidebar
3. Example questions

This is FRONTEND only — no Firebase, no LlamaIndex, no Groq here.
It imports get_answer() from app.py (backend).

HOW TO RUN:
    python3 gradio_ui.py
"""

import gradio as gr
from app import get_answer  

# ---------------------------------------------------------------
# CHAT HISTORY (in-memory store)
# ---------------------------------------------------------------
chat_sessions = []

# ---------------------------------------------------------------
# HISTORY HTML GENERATOR
# ---------------------------------------------------------------
def get_history_html():
    """Generates HTML for the chat history sidebar."""
    if not chat_sessions:
        return "<p style='color:#94a3b8; padding:10px;'>No conversations yet...</p>"
    items = "".join(
        f"<div style='padding:8px 10px; margin:5px 0; background:#1e293b; "
        f"border-radius:8px; color:#e2e8f0; font-size:13px;'>💬 {q}</div>"
        for q in reversed(chat_sessions[-10:])
    )
    return f"<div>{items}</div>"

# ---------------------------------------------------------------
# RESPOND FUNCTION (called on every user message)
# ---------------------------------------------------------------
def respond(message, history):
    """
    message : user's question
    history : list of previous messages
    Returns : cleared textbox, updated chat, updated history sidebar
    """
    if not message.strip():
        return "", history, get_history_html()

    # Call backend to get answer
    answer = get_answer(message)

    # Save short version to history sidebar
    short_q = message[:40] + "..." if len(message) > 40 else message
    chat_sessions.append(short_q)

    # Add to chat (Gradio 6.0 messages format)
    history.append({"role": "user", "content": message})
    history.append({"role": "assistant", "content": answer})

    return "", history, get_history_html()

# ---------------------------------------------------------------
# GRADIO UI
# ---------------------------------------------------------------
with gr.Blocks(title="EduMind AI") as demo:

    # HEADER
    gr.Markdown("""
    # 🎓 EduMind AI
    ### Intelligent School Data Assistant — Powered by AI
    ---
    """)

    # MAIN LAYOUT
    with gr.Row():

        # LEFT — Chat History Sidebar
        with gr.Column(scale=1, min_width=220):
            gr.Markdown("### 📋 Chat History")
            history_html = gr.HTML(
                value="<p style='color:#94a3b8; padding:10px;'>No conversations yet...</p>"
            )
            gr.Markdown("---")
            gr.Markdown("""
**Quick Tips:**
- Ask by class/section
- Ask for marks/percentage
- Ask for attendance
- Ask for subject/group
            """)

        # RIGHT — Chat Area
        with gr.Column(scale=3):
            chatbot = gr.Chatbot(
                height=450,
                placeholder="👋 Hello! Ask me anything about the students...",
                show_label=False,
            )

            with gr.Row():
                textbox = gr.Textbox(
                    placeholder="Type your question here...",
                    show_label=False,
                    scale=8,
                    container=False,
                )
                send_btn = gr.Button("Send 🚀", variant="primary", scale=1)
                clear_btn = gr.Button("Clear 🗑️", variant="secondary", scale=1)

            gr.Examples(
                examples=[
                    "List all 12th standard Section A students",
                    "Who has the highest percentage in the school?",
                    "How many students are in 10th standard?",
                    "Which students are in Computer Science group?",
                    "Show students with attendance below 85%",
                ],
                inputs=textbox,
                label="💡 Example Questions (click to use)",
            )

    # FOOTER
    gr.Markdown("""
    ---
    **EduMind AI** | Firebase 🔥 | LlamaIndex 🦙 | Groq ⚡ | Gradio 🎨
    """)

    # EVENT HANDLERS
    send_btn.click(
        fn=respond,
        inputs=[textbox, chatbot],
        outputs=[textbox, chatbot, history_html],
    )

    textbox.submit(
        fn=respond,
        inputs=[textbox, chatbot],
        outputs=[textbox, chatbot, history_html],
    )

    clear_btn.click(
        fn=lambda: ([], "<p style='color:#94a3b8;'>Cleared!</p>"),
        outputs=[chatbot, history_html],
    )

# ---------------------------------------------------------------
# LAUNCH
# ---------------------------------------------------------------
if __name__ == "__main__":
    demo.launch(
        server_name="0.0.0.0",
        server_port=7860,
        share=False,
        show_error=True,
    )
