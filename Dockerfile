FROM python:3.13-slim

# System dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libssl-dev \
    libffi-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -v -r requirements.txt

# Copy application source
COPY . .

# Set up a non-root user for Hugging Face Spaces/Security
RUN useradd -m -u 1000 user
USER user
ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH

# Pre-download models at build time so they're cached in the image
# (Using python -c to trigger the download/cache)
RUN python3 -c "\
    from sentence_transformers import SentenceTransformer, CrossEncoder; \
    SentenceTransformer('all-MiniLM-L6-v2'); \
    CrossEncoder('cross-encoder/ms-marco-MiniLM-L-6-v2'); \
    print('Models cached.')"

EXPOSE 8000

CMD ["python3", "main.py"]
