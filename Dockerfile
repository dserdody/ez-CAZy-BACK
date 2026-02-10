FROM buchfink/diamond:latest

# The upstream image sets ENTRYPOINT ["diamond"]; override so we can run a web server.
ENTRYPOINT []

RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 python3-pip \
  && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt /app/requirements.txt
RUN pip3 install --no-cache-dir -r /app/requirements.txt

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
CMD ["python3", "-m", "uvicorn", "main:app", "--host=0.0.0.0", "--port=8080"]
