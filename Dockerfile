FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    HOME=/home/user \
    HF_HOME=/home/user/.cache/huggingface

# Non-root user (required by Hugging Face Spaces, good practice everywhere)
RUN useradd -m -u 1000 user
WORKDIR /home/user/app

COPY requirements.txt .
# CPU-only PyTorch is ~1.5 GB smaller than the default CUDA build
RUN pip install torch --index-url https://download.pytorch.org/whl/cpu \
 && pip install -r requirements.txt

USER user

# Bake the model into the image so cold starts don't re-download it
RUN python -c "from transformers import pipeline; pipeline('summarization', model='sshleifer/distilbart-cnn-6-6')"

COPY --chown=user . .

EXPOSE 7860
# $PORT is set by Cloud Run / Render; Hugging Face Spaces uses 7860.
# CORS/XSRF protection is disabled because Spaces serves the app inside an
# iframe, which otherwise breaks file uploads (HTTP 403).
CMD streamlit run app.py \
    --server.port=${PORT:-7860} \
    --server.address=0.0.0.0 \
    --server.enableCORS=false \
    --server.enableXsrfProtection=false
