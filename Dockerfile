FROM buchfink/diamond:latest

# Upstream image sets ENTRYPOINT ["diamond"]; override so we can run a web server.
ENTRYPOINT []

RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 python3-pip python3-venv \
  && rm -rf /var/lib/apt/lists/*

# Create and use a virtual environment to avoid PEP 668 "externally managed" error
RUN python3 -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

WORKDIR /app
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# Copy API code
COPY main.py /app/main.py

# Copy your FASTA database and build a DIAMOND .dmnd database inside the image
COPY Supplementary_data2.faa /data/Supplementary_data2.faa
RUN diamond makedb --in /data/Supplementary_data2.faa -d /data/mydb

ENV DB_PATH=/data/mydb.dmnd
ENV DIAMOND_THREADS=1
ENV TIMEOUT_SECONDS=20
ENV MAX_FASTA_CHARS=200000

# Cloud Run uses PORT=8080 by default
ENV PORT=8080
CMD ["uvicorn", "main:app", "--host=0.0.0.0", "--port=8080"]
