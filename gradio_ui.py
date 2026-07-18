import os
import gradio as gr
from app import get_answer

# --------------------------------------------------
# Chat History
# --------------------------------------------------

chat_sessions = []


def get_history_html():

    if not chat_sessions:
        return """
        <p style="color:#94a3b8;padding:10px;">
        No conversations yet...
        </p>
        """

    items = ""

    for q in reversed(chat_sessions[-10:]):

        items += f"""
        <div style="
            padding:8px;
            margin:5px 0;
            background:#1e293b;
            border-radius:8px;
            color:#e2e8f0;
            font-size:13px;">
            💬 {q}
        </div>
        """

    return items


# --------------------------------------------------
# Chat Function
# --------------------------------------------------

def respond(message, history):

    history = history or []

    if not message.strip():
        return "", history, get_history_html()

    answer = get_answer(message)

    chat_sessions.append(message)

    history.append(
        {
            "role": "user",
            "content": message,
        }
    )

    history.append(
        {
            "role": "assistant",
            "content": answer,
        }
    )

    return "", history, get_history_html()


# --------------------------------------------------
# Clear Chat
# --------------------------------------------------

def clear_chat():

    chat_sessions.clear()

    return [], get_history_html()


# --------------------------------------------------
# UI
# --------------------------------------------------

with gr.Blocks(
    title="EduMind AI",
    theme=gr.themes.Soft(),
) as demo:

    gr.Markdown("""
# 🎓 EduMind AI

### Intelligent School Data Assistant

Ask questions about students, attendance, marks,
classes, sections and more.
""")

    with gr.Row():

        # ---------------- Sidebar ----------------

        with gr.Column(scale=1, min_width=240):

            gr.Markdown("## 📋 Recent Questions")

            history_html = gr.HTML(
                value=get_history_html()
            )

            gr.Markdown("""
### 💡 Example Questions

- Total students
- Top students
- Highest percentage
- Attendance below 85%
- Computer Science students
- 12th Section A
- Roll Number
- Student Name
""")

        # ---------------- Chat ----------------

        with gr.Column(scale=3):

            chatbot = gr.Chatbot(
                type="messages",
                height=500,
                show_label=False,
            )

            with gr.Row():

                textbox = gr.Textbox(
                    placeholder="Ask anything about students...",
                    show_label=False,
                    scale=8,
                )

                send_btn = gr.Button(
                    "Send 🚀",
                    variant="primary",
                )

                clear_btn = gr.Button(
                    "Clear 🗑️"
                )

            gr.Examples(

                examples=[

                    "How many students are there?",

                    "List all 12th standard Section A students",

                    "Who has the highest percentage?",

                    "Top 10 students",

                    "Show Computer Science students",

                    "Students with attendance below 85%",

                    "Show Roll Number 1005",

                    "Find student Arun"

                ],

                inputs=textbox,

            )

    gr.Markdown("""
---

### ⚡ EduMind AI

Powered by

- 🔥 Firebase Firestore
- 🤗 Hugging Face Embeddings
- 🦙 LlamaIndex
- 🚀 Groq Llama 3.1
- 🎨 Gradio

""")

    send_btn.click(
        respond,
        inputs=[textbox, chatbot],
        outputs=[textbox, chatbot, history_html],
    )

    textbox.submit(
        respond,
        inputs=[textbox, chatbot],
        outputs=[textbox, chatbot, history_html],
    )

    clear_btn.click(
        clear_chat,
        outputs=[chatbot, history_html],
    )


# --------------------------------------------------
# Launch
# --------------------------------------------------

if __name__ == "__main__":

    port = int(os.environ.get("PORT", 7860))

    demo.launch(
        server_name="0.0.0.0",
        server_port=port,
        share=False,
        show_error=True,
    )