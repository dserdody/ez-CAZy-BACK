import os
import tempfile
import subprocess
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import PlainTextResponse
from fastapi.middleware.cors import CORSMiddleware

APP_NAME = "diamond-web-api"
DB_PATH = os.getenv("DB_PATH", "/data/mydb.dmnd")
DIAMOND_THREADS = str(os.getenv("DIAMOND_THREADS", "1"))
TIMEOUT_SECONDS = int(os.getenv("TIMEOUT_SECONDS", "20"))
MAX_FASTA_CHARS = int(os.getenv("MAX_FASTA_CHARS", "200000"))  # 200 KB default

app = FastAPI(title=APP_NAME)

# CORS: set ALLOWED_ORIGINS to your GitHub Pages origin, e.g. https://USERNAME.github.io
allowed = os.getenv("ALLOWED_ORIGINS", "*")
origins = ["*"] if allowed.strip() == "*" else [o.strip() for o in allowed.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=False,
    allow_methods=["POST", "OPTIONS"],
    allow_headers=["*"],
)

def _write_query_fasta(fasta_text: str) -> str:
    fasta_text = (fasta_text or "").strip()
    if not fasta_text:
        raise HTTPException(status_code=400, detail="No FASTA provided.")
    if len(fasta_text) > MAX_FASTA_CHARS:
        raise HTTPException(status_code=413, detail="FASTA too large.")
    if not fasta_text.startswith(">"):
        raise HTTPException(status_code=400, detail="FASTA should start with '>' header line.")
    fd, path = tempfile.mkstemp(prefix="query_", suffix=".fasta")
    os.close(fd)
    with open(path, "w", encoding="utf-8") as f:
        f.write(fasta_text + "\n")
    return path

def _run_diamond(mode: str, query_path: str) -> str:
    # Keep outputs modest and predictable; tabular output is easiest for a first version.
    cmd = [
        "diamond", mode,
        "--db", DB_PATH,
        "--query", query_path,
        "--threads", DIAMOND_THREADS,
        "--outfmt", "6",
        "--max-target-seqs", "25",
        "--header",
    ]
    try:
        completed = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=TIMEOUT_SECONDS,
            check=False,
        )
    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=504, detail="Search timed out.")

    if completed.returncode != 0:
        raise HTTPException(
            status_code=500,
            detail=f"DIAMOND failed (code {completed.returncode}): {completed.stderr[-1500:]}"
        )
    return completed.stdout

async def _get_fasta_from_request(fasta: str | None, file: UploadFile | None) -> str:
    if file is not None:
        content = await file.read()
        try:
            return content.decode("utf-8", errors="strict")
        except UnicodeDecodeError:
            raise HTTPException(status_code=400, detail="Uploaded file must be UTF-8 text FASTA.")
    return fasta or ""

@app.post("/api/blastp", response_class=PlainTextResponse)
async def blastp(fasta: str | None = Form(None), file: UploadFile | None = File(None)):
    fasta_text = await _get_fasta_from_request(fasta, file)
    qpath = _write_query_fasta(fasta_text)
    try:
        out = _run_diamond("blastp", qpath)
        return out
    finally:
        try:
            os.remove(qpath)
        except OSError:
            pass

@app.post("/api/blastx", response_class=PlainTextResponse)
async def blastx(fasta: str | None = Form(None), file: UploadFile | None = File(None)):
    fasta_text = await _get_fasta_from_request(fasta, file)
    qpath = _write_query_fasta(fasta_text)
    try:
        out = _run_diamond("blastx", qpath)
        return out
    finally:
        try:
            os.remove(qpath)
        except OSError:
            pass
