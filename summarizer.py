from typing import Callable, Optional

import streamlit as st
import torch
from transformers import pipeline

from config import MAX_CHUNKS, MODEL_NAME

# Output-length presets: per-section and final-pass token limits.
LENGTH_PRESETS = {
    "Short": {"chunk_max": 80, "chunk_min": 20, "final_max": 100, "final_min": 25},
    "Medium": {"chunk_max": 120, "chunk_min": 25, "final_max": 150, "final_min": 30},
    "Detailed": {"chunk_max": 180, "chunk_min": 40, "final_max": 220, "final_min": 50},
}


@st.cache_resource(show_spinner="Loading the AI model... This may take a few minutes the first time.")
def load_summarizer():
    device = 0 if torch.cuda.is_available() else -1
    return pipeline("summarization", model=MODEL_NAME, device=device)


def split_into_chunks(text: str, tokenizer, max_tokens: int = 850) -> list[str]:
    """Split text into chunks that fit the model's input limit."""
    words = text.split()
    if not words:
        return []

    # One batched tokenizer call is far faster than encoding word by word.
    token_ids = tokenizer(words, add_special_tokens=False)["input_ids"]

    chunks, current, current_tokens = [], [], 0
    for word, ids in zip(words, token_ids):
        word_tokens = len(ids)
        if current and current_tokens + word_tokens > max_tokens:
            chunks.append(" ".join(current))
            current, current_tokens = [], 0
        current.append(word)
        current_tokens += word_tokens
    if current:
        chunks.append(" ".join(current))
    return chunks


def _summarize(summarizer, text: str, max_length: int, min_length: int) -> str:
    result = summarizer(
        text,
        max_length=max_length,
        min_length=min_length,
        do_sample=False,
        truncation=True,
    )
    return result[0]["summary_text"]


def summarize_document(
    text: str,
    preset: str = "Medium",
    on_progress: Optional[Callable[[int, int], None]] = None,
) -> tuple[str, int, bool]:
    """Summarize a document section by section, then merge.

    Returns (summary, sections_processed, was_truncated).
    """
    cfg = LENGTH_PRESETS[preset]
    summarizer = load_summarizer()
    chunks = split_into_chunks(text, summarizer.tokenizer)

    truncated = len(chunks) > MAX_CHUNKS
    chunks = chunks[:MAX_CHUNKS]

    summaries = []
    for index, chunk in enumerate(chunks, start=1):
        summaries.append(_summarize(summarizer, chunk, cfg["chunk_max"], cfg["chunk_min"]))
        if on_progress:
            on_progress(index, len(chunks))

    combined = " ".join(summaries)
    if len(summaries) > 1:
        parts = [
            _summarize(summarizer, chunk, cfg["final_max"], cfg["final_min"])
            for chunk in split_into_chunks(combined, summarizer.tokenizer)
        ]
        combined = " ".join(parts)

    return combined, len(chunks), truncated
