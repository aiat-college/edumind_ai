import os
import gradio as gr
from app import get_answer

chat_sessions = []

def get_history_html():
    if not chat_sessions:
        return "<p style='color:#94a3b8;padding:10px;'>No conversations yet...</p>"
    items = "".join(
        f"<div style='padding:8px 10px;margin:5px 0;background:#1e293b;border-radius:8px;color:#e2e8f0;font-size:13px;'>💬 {q}</div>"
        for q in reversed(chat_sessions[-10:])
    )
    return f"<div>{items}</div>"

def respond(message, history):
    history = history or []

    if not message.strip():
        return "", history, get_history_html()

    answer = get_answer(message)
    chat_sessions.append(message)

    history.append({"role": "user", "content": message})
    history.append({"role": "assistant", "content": answer})

    return "", history, get_history_html()

def clear_chat():
    chat_sessions.clear()
    return [], get_history_html()

with gr.Blocks(title="EduMind AI") as demo:
    gr.Markdown("# 🎓 EduMind AI\n### Intelligent School Data Assistant")

    with gr.Row():
        with gr.Column(scale=1, min_width=220):
            gr.Markdown("### 📋 Chat History")
            history_html = gr.HTML(value=get_history_html())
            gr.Markdown("""
---
**Quick Tips**
- Ask by class
- Ask by section
- Ask attendance
- Ask marks
- Ask percentage
""")

        with gr.Column(scale=3):
            chatbot = gr.Chatbot(
                type="messages",
                height=450,
                show_label=False,
            )

            with gr.Row():
                textbox = gr.Textbox(
                    placeholder="Ask your question...",
                    show_label=False,
                    scale=8,
                )
                send_btn = gr.Button("Send 🚀", variant="primary")
                clear_btn = gr.Button("Clear 🗑️")

            gr.Examples(
                examples=[
                    "List all 12th standard Section A students",
                    "Who has the highest percentage?",
                    "How many students are in 10th standard?",
                    "Show Computer Science students",
                    "Students with attendance below 85%",
                ],
                inputs=textbox,
            )

    gr.Markdown("---\n**EduMind AI** | Firebase 🔥 | LlamaIndex 🦙 | Gemini ✨ | Gradio 🎨")

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

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 7860))
    demo.launch(
        server_name="0.0.0.0",
        server_port=port,
        share=True,
        show_error=True,
    )