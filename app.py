"""Gradio query interface for The Unofficial Guide (FIU campus dining).

Input: a plain-language question. Output: grounded answer + the source documents it drew from.
Run: python app.py  ->  http://localhost:7860
"""
import gradio as gr

from rag import ask


def handle_query(question):
    if not question.strip():
        return "Please enter a question.", ""
    result = ask(question)
    sources = "\n".join(f"• {s}" for s in result["sources"])
    return result["answer"], sources


with gr.Blocks(title="The Unofficial Guide — FIU Dining") as demo:
    gr.Markdown("# The Unofficial Guide: FIU Campus Dining\n"
                "Ask anything about eating at/around FIU — answers come only from "
                "collected student documents, with sources cited.")
    inp = gr.Textbox(label="Your question",
                     placeholder="e.g., Is the meal plan worth it?")
    btn = gr.Button("Ask")
    answer = gr.Textbox(label="Answer", lines=6)
    sources = gr.Textbox(label="Retrieved from", lines=4)
    btn.click(handle_query, inputs=inp, outputs=[answer, sources])
    inp.submit(handle_query, inputs=inp, outputs=[answer, sources])

if __name__ == "__main__":
    demo.launch()
