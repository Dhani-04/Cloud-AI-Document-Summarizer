import streamlit as st

st.set_page_config(
    page_title="Cloud AI Document Summarizer",
    page_icon="📄",
    layout="wide",
)

import cloud  # noqa: E402
from config import MAX_CHUNKS  # noqa: E402
from pdf_utils import extract_pdf_text  # noqa: E402
from summarizer import LENGTH_PRESETS, summarize_document  # noqa: E402

DEFAULTS = {
    "document_text": "",
    "summary": "",
    "file_name": "",
    "page_count": 0,
    "pdf_bytes": None,
    "chunk_count": 0,
    "truncated": False,
}
for key, value in DEFAULTS.items():
    st.session_state.setdefault(key, value)


# ---------------------------------------------------------------- sidebar
def render_sidebar():
    """Show account controls. Returns the signed-in user, or None."""
    with st.sidebar:
        st.header("Account")

        if not cloud.is_configured():
            st.info(
                "Demo mode: cloud accounts and history are off because "
                "Supabase is not configured. Summaries still work."
            )
            return None

        user = st.session_state.get("user")
        if user:
            st.success(f"Signed in as {user.email}")
            if st.button("Sign out"):
                cloud.sign_out()
                st.rerun()
            return user

        sign_in_tab, sign_up_tab = st.tabs(["Sign in", "Sign up"])

        with sign_in_tab:
            with st.form("sign_in_form"):
                email = st.text_input("Email", key="si_email")
                password = st.text_input("Password", type="password", key="si_pw")
                submitted = st.form_submit_button("Sign in")
            if submitted:
                ok = False
                try:
                    cloud.sign_in(email, password)
                    ok = True
                except Exception as exc:
                    st.error(f"Sign-in failed: {exc}")
                if ok:
                    st.rerun()

        with sign_up_tab:
            with st.form("sign_up_form"):
                email = st.text_input("Email", key="su_email")
                password = st.text_input("Password (min 6 characters)", type="password", key="su_pw")
                submitted = st.form_submit_button("Create account")
            if submitted:
                signed_in, error = False, None
                try:
                    signed_in = cloud.sign_up(email, password)
                except Exception as exc:
                    error = exc
                if error:
                    st.error(f"Sign-up failed: {error}")
                elif signed_in:
                    st.rerun()
                else:
                    st.success("Account created. Check your email to confirm it, then sign in.")
    return None


# ------------------------------------------------------------- summarizer
def render_summarizer(user):
    st.write("Upload a PDF and generate a concise AI-powered summary.")
    uploaded_file = st.file_uploader("Choose a PDF document", type=["pdf"])

    if uploaded_file:
        st.success(f"Selected: {uploaded_file.name}")

        if st.button("Extract PDF Text"):
            try:
                pdf_bytes = uploaded_file.getvalue()
                with st.spinner("Extracting text from PDF..."):
                    text, page_count = extract_pdf_text(pdf_bytes)

                if not text:
                    st.warning(
                        "No selectable text was found. This may be a scanned PDF. "
                        "OCR support is not included in this version."
                    )
                    st.session_state.document_text = ""
                else:
                    st.session_state.document_text = text
                    st.session_state.pdf_bytes = pdf_bytes
                    st.session_state.file_name = uploaded_file.name
                    st.session_state.page_count = page_count
                    st.success(f"Extracted text from {page_count} page(s).")
                st.session_state.summary = ""
            except Exception as exc:
                st.error(f"Could not read this PDF: {exc}")

    text = st.session_state.document_text
    if text:
        st.subheader("Extracted document text")
        st.caption(
            f"File: {st.session_state.file_name} · "
            f"Pages: {st.session_state.page_count} · "
            f"Characters: {len(text):,}"
        )
        with st.expander("Preview extracted text"):
            st.text(text[:8000] + ("..." if len(text) > 8000 else ""))

        col1, col2 = st.columns([1, 2])
        with col1:
            preset = st.select_slider("Summary detail", list(LENGTH_PRESETS), value="Medium")
        with col2:
            keep_pdf = False
            if user:
                keep_pdf = st.checkbox("Also store the original PDF in my private cloud storage")

        if st.button("✨ Generate AI Summary", type="primary"):
            try:
                progress = st.progress(0, text="Summarizing document...")

                def on_progress(done, total):
                    progress.progress(done / total, text=f"Summarized section {done} of {total}")

                with st.spinner("The AI model is generating your summary..."):
                    summary, chunks, truncated = summarize_document(text, preset, on_progress)
                progress.empty()

                st.session_state.summary = summary
                st.session_state.chunk_count = chunks
                st.session_state.truncated = truncated

                if user:
                    try:
                        cloud.save_summary(
                            user.id,
                            st.session_state.file_name,
                            st.session_state.page_count,
                            summary,
                            st.session_state.pdf_bytes if keep_pdf else None,
                        )
                        st.toast("Saved to your history ☁️")
                    except Exception as exc:
                        st.warning(f"Summary created, but saving to the cloud failed: {exc}")
            except Exception as exc:
                st.error(f"Summarization failed: {exc}")

    if st.session_state.summary:
        st.subheader("AI-generated summary")
        st.write(st.session_state.summary)
        st.caption(f"Processed in {st.session_state.chunk_count} text section(s).")
        if st.session_state.truncated:
            st.warning(
                f"This document is long, so only the first {MAX_CHUNKS} sections were summarized."
            )
        st.download_button(
            "⬇️ Download summary",
            data=st.session_state.summary,
            file_name="summary.txt",
            mime="text/plain",
        )


# ---------------------------------------------------------------- history
def render_history():
    try:
        rows = cloud.list_summaries()
    except Exception as exc:
        st.error(f"Could not load history: {exc}")
        return

    if not rows:
        st.info("No saved summaries yet. Generate one and it will appear here.")
        return

    for row in rows:
        when = row["created_at"][:16].replace("T", " ")
        with st.expander(f"📄 {row['file_name']} · {when} UTC"):
            st.write(row["summary"])
            c1, c2, c3 = st.columns(3)
            c1.download_button(
                "⬇️ Summary (.txt)",
                row["summary"],
                file_name=f"{row['file_name']}-summary.txt",
                key=f"dl_{row['id']}",
            )
            if row.get("storage_path") and c2.button("🔗 Original PDF link", key=f"url_{row['id']}"):
                try:
                    url = cloud.get_pdf_url(row["storage_path"])
                    st.link_button("Open PDF (link valid 1 hour)", url)
                except Exception as exc:
                    st.error(f"Could not create link: {exc}")
            if c3.button("🗑️ Delete", key=f"del_{row['id']}"):
                try:
                    cloud.delete_summary(row)
                except Exception as exc:
                    st.error(f"Delete failed: {exc}")
                else:
                    st.rerun()


# -------------------------------------------------------------------- main
user = render_sidebar()

st.title("📄 Cloud-Based AI Document Summarizer")

if cloud.is_configured() and not user:
    st.info("👈 Sign in or create an account from the sidebar to get started.")
    st.stop()

if user:
    summarize_tab, history_tab = st.tabs(["Summarize", "History"])
    with summarize_tab:
        render_summarizer(user)
    with history_tab:
        render_history()
else:
    render_summarizer(None)

st.divider()
st.caption("Cloud Computing Project | Python | Streamlit | Hugging Face | Supabase | Docker")
