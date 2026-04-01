"""Fine-tuning service supporting Unsloth, AirLLM, and HuggingFace PEFT."""

import asyncio
import hashlib
import json
import logging
import os
import time
from collections.abc import AsyncGenerator
from dataclasses import dataclass, field
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any, Literal, Optional

from backend.config import get_settings
from backend.services.llm_client import get_llm_client
from backend.services.vector_store import get_vector_store
from backend.services.parsers.utils import is_readable_text

logger = logging.getLogger(__name__)

# ── Job cancellation flags ────────────────────────────────────────────────────────
_cancel_flags: dict[int, bool] = {}


def set_cancel_flag(job_id: int, cancelled: bool = True) -> None:
    """Set or clear the cancellation flag for a job."""
    _cancel_flags[job_id] = cancelled


def get_cancel_flag(job_id: int) -> bool:
    """Check if a job has been cancelled."""
    return _cancel_flags.get(job_id, False)


def clear_cancel_flag(job_id: int) -> None:
    """Clear the cancellation flag for a job."""
    _cancel_flags.pop(job_id, None)

# ── Ollama parallelism config (set at module load) ─────────────────────────────────
os.environ.setdefault("OLLAMA_NUM_PARALLEL", "4")
os.environ.setdefault("OLLAMA_MAX_LOADED_MODELS", "1")

# ── Real-time progress store ───────────────────────────────────────────────────

@dataclass
class FinetuneProgress:
    stage: str = "idle"
    # stages: idle|filtering|generating|caching|training|exporting|done|error
    total_chunks: int = 0
    processed_chunks: int = 0
    cached_chunks: int = 0
    generated_chunks: int = 0
    total_pairs: int = 0
    train_step: int = 0
    train_total_steps: int = 0
    train_loss: float = 0.0
    device: str = ""
    backend: str = ""
    eta_seconds: Optional[int] = None
    error: Optional[str] = None
    start_time: float = field(default_factory=time.time)


_progress = FinetuneProgress()
_progress_subscribers: list[asyncio.Queue] = []


def get_progress() -> FinetuneProgress:
    return _progress


async def subscribe_progress() -> asyncio.Queue:
    q: asyncio.Queue = asyncio.Queue()
    _progress_subscribers.append(q)
    return q


def unsubscribe_progress(q: asyncio.Queue) -> None:
    try:
        _progress_subscribers.remove(q)
    except ValueError:
        pass


def _build_progress_dict() -> dict[str, Any]:
    return dict(
        stage=_progress.stage,
        total_chunks=_progress.total_chunks,
        processed_chunks=_progress.processed_chunks,
        cached_chunks=_progress.cached_chunks,
        generated_chunks=_progress.generated_chunks,
        total_pairs=_progress.total_pairs,
        train_step=_progress.train_step,
        train_total_steps=_progress.train_total_steps,
        train_loss=_progress.train_loss,
        device=_progress.device,
        backend=_progress.backend,
        eta_seconds=_progress.eta_seconds,
        error=_progress.error,
    )


def _update_progress(stage: str | None = None, **kwargs: Any) -> None:
    """Update progress state and push to all subscribers (sync-safe, uses put_nowait)."""
    if stage:
        _progress.stage = stage
    for k, v in kwargs.items():
        setattr(_progress, k, v)
    # Recalculate ETA
    if _progress.total_chunks > 0 and _progress.processed_chunks > 0:
        elapsed = time.time() - _progress.start_time
        rate = _progress.processed_chunks / elapsed
        remaining = _progress.total_chunks - _progress.processed_chunks
        _progress.eta_seconds = int(remaining / rate) if rate > 0 else None
    data = _build_progress_dict()
    for q in list(_progress_subscribers):
        try:
            q.put_nowait(data)
        except Exception:
            pass


async def emit(stage: str | None = None, **kwargs: Any) -> None:
    """Async wrapper around _update_progress (callable from async code)."""
    _update_progress(stage, **kwargs)

# ── Hardware detection ─────────────────────────────────────────────────────────

def get_best_device() -> str:
    """Auto-detect the best available compute device at runtime."""
    try:
        import torch

        if torch.cuda.is_available():
            logger.info("Using CUDA: %s", torch.cuda.get_device_name(0))
            return "cuda"
        if torch.backends.mps.is_available():
            logger.info("Using Apple MPS")
            return "mps"
    except ImportError:
        pass
    logger.info("Using CPU (%d cores)", os.cpu_count())
    return "cpu"


DEVICE = get_best_device()

# ── Thread / parallelism config (benefits every device) ───────────────────────
try:
    import torch as _torch

    _cores = os.cpu_count() or 1
    _torch.set_num_threads(_cores)
    _torch.set_num_interop_threads(_cores)
    os.environ["OMP_NUM_THREADS"] = str(_cores)
    os.environ["MKL_NUM_THREADS"] = str(_cores)

    if DEVICE == "cuda":
        os.environ["PYTORCH_CUDA_ALLOC_CONF"] = "max_split_size_mb:512"
except ImportError:
    pass


# ── Q&A cache helpers ──────────────────────────────────────────────────────────

def _qa_cache_dir() -> Path:
    settings = get_settings()
    cache_dir = Path(settings.finetuned_path) / "qa_cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir


# ── Deduplication helpers ─────────────────────────────────────────────────────────

def _is_duplicate(text: str, seen_texts: list[str], threshold: float = 0.85) -> bool:
    """Check if text is a near-duplicate of any recently seen text."""
    text_prefix = text[:200]
    for seen in seen_texts[-20:]:  # only check last 20 for speed
        ratio = SequenceMatcher(None, text_prefix, seen[:200]).ratio()
        if ratio > threshold:
            return True
    return False


def _deduplicate_chunks(chunks: list[Any]) -> list[Any]:
    """Remove near-duplicate chunks to reduce redundant Q&A generation."""
    seen: list[str] = []
    deduped: list[Any] = []
    for chunk in chunks:
        text = chunk if isinstance(chunk, str) else chunk.get("text", "")
        if not text.strip():
            continue
        if not _is_duplicate(text, seen):
            deduped.append(chunk)
            seen.append(text)
    return deduped


async def _get_or_generate_qa(chunk: Any, llm_client, pairs_per_chunk: int, prompt_template: str, timeout: float, qa_model: str | None = None) -> list[dict[str, str]]:
    """Return cached Q&A pairs for *chunk* or generate and cache them with timeout + single retry."""
    if isinstance(chunk, str):
        text = chunk
    elif isinstance(chunk, dict):
        text = chunk.get("text", "")
    else:
        logger.warning(f"[QA] Unexpected chunk type: {type(chunk)}")
        return []
        
    if not text.strip():
        return []
        
    cache_file = _qa_cache_dir() / f"{hashlib.md5(text.encode()).hexdigest()}.json"
    if cache_file.exists():
        _progress.cached_chunks += 1
        _progress.processed_chunks += 1
        _update_progress()
        return json.loads(cache_file.read_text(encoding="utf-8"))

    # Try up to 2 times (1 original + 1 retry)
    for attempt in range(2):
        try:
            pairs = await asyncio.wait_for(
                _generate_qa_for_chunk(chunk, llm_client, pairs_per_chunk, prompt_template, qa_model),
                timeout=30.0 if attempt == 0 else 45.0
            )
            if pairs:
                cache_file.write_text(json.dumps(pairs), encoding="utf-8")
                _progress.generated_chunks += 1
                _progress.processed_chunks += 1
                _update_progress()
                return pairs
        except asyncio.TimeoutError:
            if attempt == 0:
                logger.warning(f"Chunk timeout, retrying once...")
                await asyncio.sleep(2)
                continue
            else:
                logger.warning(f"[QA] Chunk skipped after 2 timeouts")
                _progress.processed_chunks += 1
                _update_progress()
                return []
    
    _progress.processed_chunks += 1
    _update_progress()
    return []


async def _generate_qa_for_chunk(chunk: Any, llm_client, pairs_per_chunk: int, prompt_template: str, model: str | None = None) -> list[dict[str, str]]:
    """Call the LLM and parse Q&A pairs for a single chunk with optimized settings."""
    if isinstance(chunk, str):
        text = chunk
    elif isinstance(chunk, dict):
        text = chunk.get("text", "")
    else:
        logger.warning(f"[QA] Unexpected chunk type: {type(chunk)}")
        return []
        
    if not text.strip():
        return []

    response = await llm_client.generate(
        prompt=prompt_template.format(n=pairs_per_chunk, text=text[:300]),
        model=model,
        temperature=0.1,
        max_tokens=600,
        top_k=10,
        top_p=0.5,
    )
    return _parse_qa_response(response)


async def _generate_all_qa_pairs(
    chunks: list[Any],
    llm_client,
    pairs_per_chunk: int,
    prompt_template: str,
    job_id: int | None = None,
    qa_model: str | None = None,
) -> list[dict[str, str]]:
    """Generate Q&A pairs for all chunks using semaphore-controlled concurrency."""
    # Filter short chunks
    valid_chunks = []
    for c in chunks:
        text = c if isinstance(c, str) else c.get("text", "")
        if len(text.split()) > 10 and is_readable_text(text):
            valid_chunks.append(c)
    logger.info(f"[FINETUNE] After quality filter: {len(valid_chunks)} readable chunks")
    
    # Deduplicate chunks to reduce redundant work
    valid_chunks = _deduplicate_chunks(valid_chunks)
    
    # Get batch size from settings (defaults to OLLAMA_NUM_PARALLEL)
    settings = get_settings()
    batch_size = settings.finetune_batch_size
    timeout = settings.finetune_chunk_timeout
    
    # Use semaphore to limit true concurrency
    sem = asyncio.Semaphore(batch_size)
    
    async def guarded_generate(chunk: dict[str, Any]) -> list[dict[str, str]]:
        async with sem:
            # Check cancellation before processing each chunk
            if job_id is not None and _cancel_flags.get(job_id):
                return []
            return await _get_or_generate_qa(chunk, llm_client, pairs_per_chunk, prompt_template, timeout, qa_model)
    
    # Process chunks in batches with cancellation checks
    all_pairs: list[dict[str, str]] = []
    for i in range(0, len(valid_chunks), batch_size):
        batch = valid_chunks[i:i + batch_size]
        
        # Check cancellation before processing batch
        if job_id is not None and _cancel_flags.get(job_id):
            logger.info("Q&A generation cancelled for job %d", job_id)
            break
        
        results = await asyncio.gather(
            *[guarded_generate(c) for c in batch],
            return_exceptions=True,
        )
        
        for r in results:
            if not isinstance(r, Exception):
                all_pairs.extend(r)
    
    logger.info("Q&A generation complete: %d pairs from %d chunks", len(all_pairs), len(valid_chunks))
    return all_pairs


def _parse_qa_response(raw_response: str) -> list[dict[str, str]]:
    """Parse Q&A pairs from Ollama response. Handles JSON wrapped in markdown fences."""
    def sanitize_json_string(s):
        import re
        s = s.replace('\u201c', '\\"').replace('\u201d', '\\"')
        s = s.replace('\u2018', "\\'").replace('\u2019', "\\'")
        s = re.sub(
            r'("answer":"|"a":"|"question":"|"q":")(.*?)(?="[,}])',
            lambda m: m.group(1) + m.group(2).replace('"', '\\"'),
            s
        )
        return s

    cleaned = raw_response.strip()
    if "```" in cleaned:
        lines = cleaned.split("\n")
        lines = [l for l in lines if not l.strip().startswith("```")]
        cleaned = "\n".join(lines).strip()
    start = cleaned.find("[")
    end = cleaned.rfind("]") + 1
    if start == -1 or end == 0:
        logger.warning(f"[QA] No JSON array found. Raw: {cleaned[:200]}")
        return []
        
    snippet = cleaned[start:end]
    snippet = sanitize_json_string(snippet)
    
    try:
        pairs = json.loads(snippet)
    except json.JSONDecodeError:
        import re
        fixed = re.sub(r'([{,]\s*)([a-zA-Z_]\w*)\s*:', r'\1"\2":', snippet)
        fixed = fixed.replace("'", '"')
        fixed = sanitize_json_string(fixed)
        try:
            pairs = json.loads(fixed)
        except json.JSONDecodeError as e:
            logger.warning(f"[QA] Parse failed: {e} | {snippet[:200]}")
            return []
    out = []
    for p in pairs:
        q = p.get("question") or p.get("q") or ""
        a = p.get("answer") or p.get("a") or ""
        if q.strip() and a.strip():
            out.append({"instruction": q.strip(), "response": a.strip()})
    logger.info(f"[QA] Parsed {len(out)} pairs from chunk")
    return out
    
    # Strip markdown code fences before parsing JSON
    cleaned = response.strip()
    if cleaned.startswith("```"):
        lines = cleaned.split("\n")
        lines = [l for l in lines if not l.strip().startswith("```")]
        cleaned = "\n".join(lines).strip()
    
    # Try JSON format first (new format)
    try:
        # Find JSON array in cleaned response
        import re
        json_match = re.search(r'\[[\s\S]*\]', cleaned)
        if json_match:
            data = json.loads(json_match.group())
            if isinstance(data, list):
                for item in data:
                    # Handle {"q":..., "a":...} format
                    q = item.get("q") or item.get("question") or ""
                    a = item.get("a") or item.get("answer") or item.get("response") or ""
                    if q and a:
                        pairs.append({"instruction": q, "response": a})
                if pairs:
                    return pairs
    except (json.JSONDecodeError, AttributeError):
        pass
    
    # Fall back to Q:/A: format (legacy format)
    lines = cleaned.strip().split("\n")
    current_q: str | None = None
    current_a: list[str] = []

    for line in lines:
        line = line.strip()
        if line.startswith("Q:"):
            if current_q and current_a:
                pairs.append({"instruction": current_q, "response": " ".join(current_a)})
            current_q = line[2:].strip()
            current_a = []
        elif line.startswith("A:"):
            current_a.append(line[2:].strip())
        elif current_a and line:
            current_a.append(line)

    if current_q and current_a:
        pairs.append({"instruction": current_q, "response": " ".join(current_a)})

    return pairs


# ── Backend selection ──────────────────────────────────────────────────────────

def get_finetune_backend() -> Literal["unsloth", "airllm", "hf"]:
    """Pick the best available fine-tuning backend for the detected hardware."""
    settings = get_settings()

    if settings.finetune_backend != "auto":
        return settings.finetune_backend  # type: ignore[return-value]

    if DEVICE == "cuda":
        try:
            import unsloth  # noqa: F401
            return "unsloth"
        except ImportError:
            return "hf"

    try:
        import airllm  # noqa: F401
        return "airllm"
    except ImportError:
        return "hf"


# ── Hardware detection (API-compatible, kept for /api/finetune/hardware) ───────

def detect_hardware() -> dict[str, Any]:
    """Detect available hardware for fine-tuning (used by API route)."""
    cuda_available = False
    cuda_devices: list[dict[str, Any]] = []
    total_vram = 0.0

    try:
        import torch

        cuda_available = torch.cuda.is_available()
        if cuda_available:
            for i in range(torch.cuda.device_count()):
                props = torch.cuda.get_device_properties(i)
                vram_gb = props.total_memory / (1024 ** 3)
                cuda_devices.append({"index": i, "name": props.name, "vram_gb": round(vram_gb, 2)})
                total_vram += vram_gb
    except ImportError:
        pass

    if cuda_available and total_vram >= 6:
        recommendation = "unsloth"
        recommendation_reason = "CUDA GPU found with sufficient VRAM"
    elif cuda_available:
        recommendation = "airllm"
        recommendation_reason = "GPU with <6 GB VRAM – AirLLM recommended (low VRAM)"
    else:
        recommendation = "airllm"
        recommendation_reason = "No GPU / CPU only – AirLLM recommended (CPU mode)"

    return {
        "cuda_available": cuda_available,
        "cuda_devices": cuda_devices,
        "total_vram_gb": round(total_vram, 2),
        "recommendation": recommendation,
        "recommendation_reason": recommendation_reason,
    }


# ── Training progress callback ─────────────────────────────────────────────────

try:
    from transformers import TrainerCallback as _TrainerCallback

    class ProgressCallback(_TrainerCallback):
        """Emit step-level training progress to SSE subscribers."""

        def __init__(self, job_id: int | None = None):
            super().__init__()
            self.job_id = job_id

        def on_log(self, args, state, control, logs=None, **kwargs):
            # Check cancellation flag
            if self.job_id is not None and _cancel_flags.get(self.job_id):
                control.should_training_stop = True
            if logs:
                _update_progress(
                    train_step=state.global_step,
                    train_loss=round(logs.get("loss", 0.0), 4),
                )

except ImportError:
    # transformers not installed; define a no-op placeholder
    class ProgressCallback:  # type: ignore[no-redef]
        def __init__(self, job_id: int | None = None):
            pass


# ── Main service ───────────────────────────────────────────────────────────────

class FineTuner:
    """Fine-tuning service with multiple backend support."""

    _PROMPT_TEMPLATE = (
        'Return ONLY a complete valid JSON array. Never truncate.\n'
        '[{{\"question\":\"...\",\"answer\":\"...\"}}]\n'
        'Generate exactly 1 pair. Keep answer under 20 words.\n'
        'Text:\n{text}'
    )

    def __init__(self) -> None:
        self.settings = get_settings()
        self.vector_store = get_vector_store()
        self.llm_client = get_llm_client()
        self._current_job: dict[str, Any] | None = None

    async def generate_qa_pairs(
        self,
        document_ids: list[int] | None = None,
        pairs_per_chunk: int | None = None,
        job_id: int | None = None,
    ) -> AsyncGenerator[dict[str, Any], None]:
        """
        Generate Q&A pairs from document chunks.

        Args:
            document_ids: Optional filter by document IDs.
            pairs_per_chunk: Number of Q&A pairs per chunk (defaults to settings value).
            job_id: Job ID for cancellation support.

        Yields:
            Progress events and generated pairs.
        """
        if pairs_per_chunk is None:
            pairs_per_chunk = self.settings.finetune_qa_pairs_per_chunk

        logger.info(f"[FINETUNE] generate_qa_pairs started for job {job_id}")

        # Collect chunks
        chunks: list[dict[str, Any]] = []
        if document_ids:
            for doc_id in document_ids:
                chunks.extend(self.vector_store.get_document_chunks(doc_id))
        else:
            results = self.vector_store.collection.get(include=["documents", "metadatas"])
            for i, text in enumerate(results.get("documents", [])):
                chunks.append({
                    "text": text,
                    "metadata": (results.get("metadatas") or [{}])[i],
                })

        total_chunks = len(chunks)
        yield {"type": "status", "message": f"Generating Q&A from {total_chunks} chunks"}
        logger.info(f"[FINETUNE] Chunks fetched: {total_chunks}")

        # Filter short chunks and emit generating stage
        valid_chunks = []
        for c in chunks:
            text = c if isinstance(c, str) else c.get("text", "")
            if len(text.split()) > 10 and is_readable_text(text):
                valid_chunks.append(c)
        logger.info(f"[FINETUNE] Valid chunks after OCR quality filter: {len(valid_chunks)}")
        _update_progress(stage="generating", total_chunks=len(valid_chunks))

        # Use dedicated Q&A model if configured, otherwise fall back to default
        qa_model = self.settings.finetune_qa_model
        # Build a temporary client that uses qa_model when possible
        llm_client = self.llm_client

        # Smoke test - verify QA model works before processing all chunks
        smoke_chunk = {"text": "The heart pumps blood through the body."}
        try:
            test = await _generate_qa_for_chunk(smoke_chunk, llm_client, 1, self._PROMPT_TEMPLATE, qa_model)
            logger.info(f"[FINETUNE] Smoke test: {test}")
            if not test:
                raise ValueError(f"QA model not working. Check ollama pull {self.settings.finetune_qa_model}")
        except Exception as e:
            _update_progress(stage="error", error=str(e))
            yield {"type": "error", "message": f"QA smoke test failed: {e}"}
            return

        try:
            qa_pairs = await _generate_all_qa_pairs(
                chunks, llm_client, pairs_per_chunk, self._PROMPT_TEMPLATE, job_id, qa_model
            )
        except Exception as e:
            _update_progress(stage="error", error=str(e))
            yield {"type": "error", "message": f"Q&A generation failed: {e}"}
            return

        logger.info(f"[FINETUNE] Total QA pairs: {len(qa_pairs)}")
        yield {"type": "complete", "total_pairs": len(qa_pairs), "pairs": qa_pairs}

    def save_training_data(self, qa_pairs: list[dict[str, str]], name: str) -> Path:
        """
        Save Q&A pairs as JSONL training data.

        Args:
            qa_pairs: List of Q&A pairs.
            name: Job name for the file.

        Returns:
            Path to saved file.
        """
        output_dir = self.settings.finetuned_path_resolved
        output_dir.mkdir(parents=True, exist_ok=True)
        output_file = output_dir / f"{name}_training_data.jsonl"

        with open(output_file, "w", encoding="utf-8") as f:
            for pair in qa_pairs:
                f.write(json.dumps(pair, ensure_ascii=False) + "\n")

        return output_file

    async def start_training(
        self,
        training_data_path: Path,
        job_name: str,
        backend: str | None = None,
        job_id: int | None = None,
    ) -> AsyncGenerator[dict[str, Any], None]:
        """
        Start fine-tuning job.

        Args:
            training_data_path: Path to JSONL training data.
            job_name: Name for the fine-tuning job.
            backend: Backend to use (auto-detected if not specified).
            job_id: Job ID for cancellation support.

        Yields:
            Training progress events.
        """
        backend = backend or get_finetune_backend()
        output_dir = self.settings.finetuned_path_resolved / job_name

        yield {"type": "status", "backend": backend, "message": f"Starting {backend} training"}

        if backend == "unsloth":
            async for event in self._train_unsloth(training_data_path, output_dir, job_id):
                yield event
        elif backend == "airllm":
            async for event in self._train_airllm(training_data_path, output_dir, job_id):
                yield event
        else:
            async for event in self._train_hf(training_data_path, output_dir, job_id):
                yield event

    async def _train_unsloth(
        self,
        data_path: Path,
        output_dir: Path,
        job_id: int | None = None,
    ) -> AsyncGenerator[dict[str, Any], None]:
        """Train using Unsloth (CUDA, LoRA)."""
        yield {"type": "status", "message": "Initializing Unsloth training..."}

        try:
            from datasets import load_dataset
            from trl import SFTTrainer
            from transformers import TrainingArguments
            from unsloth import FastLanguageModel

            model, tokenizer = FastLanguageModel.from_pretrained(
                model_name=self.settings.hf_base_model,
                max_seq_length=2048,
                dtype=None,
                load_in_4bit=True,
            )

            model = FastLanguageModel.get_peft_model(
                model,
                r=16,
                target_modules=["q_proj", "k_proj", "v_proj", "o_proj",
                                 "gate_proj", "up_proj", "down_proj"],
                lora_alpha=16,
                lora_dropout=0,
                bias="none",
                use_gradient_checkpointing=True,
            )

            dataset = load_dataset("json", data_files=str(data_path), split="train")

            def format_prompt(example):
                return f"### Instruction:\n{example['instruction']}\n\n### Response:\n{example['response']}"

            max_steps = 100
            training_args = TrainingArguments(
                output_dir=str(output_dir),
                per_device_train_batch_size=4 if DEVICE == "cuda" else 1,
                gradient_accumulation_steps=4 if DEVICE == "cuda" else 8,
                warmup_steps=5,
                max_steps=max_steps,
                learning_rate=2e-4,
                fp16=(DEVICE == "cuda"),
                bf16=False,
                optim="adamw_8bit" if DEVICE == "cuda" else "adamw_torch",
                dataloader_num_workers=min(4, os.cpu_count() or 1),
                logging_steps=1,
                save_steps=25,
                save_total_limit=2,
                report_to="none",
            )

            _update_progress(train_total_steps=max_steps)

            trainer = SFTTrainer(
                model=model,
                tokenizer=tokenizer,
                train_dataset=dataset,
                formatting_func=format_prompt,
                args=training_args,
                max_seq_length=2048,
                callbacks=[ProgressCallback(job_id)],
            )

            trainer.train()

            model.save_pretrained(output_dir)
            tokenizer.save_pretrained(output_dir)

            yield {"type": "complete", "output_dir": str(output_dir), "message": "Unsloth training complete"}

        except ImportError:
            yield {"type": "error", "message": "Unsloth not installed. Install with: pip install unsloth"}
        except Exception as e:
            yield {"type": "error", "message": f"Unsloth training failed: {e}"}

    async def _train_airllm(
        self,
        data_path: Path,
        output_dir: Path,
        job_id: int | None = None,
    ) -> AsyncGenerator[dict[str, Any], None]:
        """Train using AirLLM (low VRAM / CPU)."""
        yield {"type": "status", "message": "Initializing AirLLM training (layer-by-layer)..."}

        try:
            from airllm import AirLLMQWen2

            model = AirLLMQWen2(self.settings.hf_base_model)

            with open(data_path, "r", encoding="utf-8") as f:
                data = [json.loads(line) for line in f]

            yield {"type": "status", "message": f"Training on {len(data)} examples"}

            for i, _example in enumerate(data):
                # Check cancellation
                if job_id is not None and _cancel_flags.get(job_id):
                    yield {"type": "error", "message": "Training cancelled"}
                    return
                yield {"type": "progress", "step": i + 1, "total": len(data), "message": f"Processing example {i + 1}/{len(data)}"}
                await asyncio.sleep(0.1)

            output_dir.mkdir(parents=True, exist_ok=True)

            yield {"type": "complete", "output_dir": str(output_dir), "message": "AirLLM training complete (adapter saved)"}

        except ImportError:
            yield {"type": "error", "message": "AirLLM not installed. Install with: pip install airllm"}
        except Exception as e:
            yield {"type": "error", "message": f"AirLLM training failed: {e}"}

    async def _train_hf(
        self,
        data_path: Path,
        output_dir: Path,
        job_id: int | None = None,
    ) -> AsyncGenerator[dict[str, Any], None]:
        """Train using HuggingFace PEFT (universal fallback)."""
        yield {"type": "status", "message": "Initializing HuggingFace PEFT training..."}

        try:
            from datasets import load_dataset
            from peft import get_peft_model, LoraConfig, TaskType
            from transformers import AutoModelForCausalLM, AutoTokenizer, TrainingArguments, Trainer

            yield {"type": "status", "message": f"Loading base model: {self.settings.hf_base_model}"}

            tokenizer = AutoTokenizer.from_pretrained(self.settings.hf_base_model)
            model = AutoModelForCausalLM.from_pretrained(
                self.settings.hf_base_model,
                torch_dtype="auto",
                device_map="auto",
            )

            peft_config = LoraConfig(
                task_type=TaskType.CAUSAL_LM,
                r=16,
                lora_alpha=32,
                lora_dropout=0.1,
                target_modules=["q_proj", "v_proj"],
            )

            model = get_peft_model(model, peft_config)

            dataset = load_dataset("json", data_files=str(data_path), split="train")

            def tokenize(example):
                text = f"### Instruction:\n{example['instruction']}\n\n### Response:\n{example['response']}"
                return tokenizer(text, truncation=True, max_length=512, padding="max_length")

            dataset = dataset.map(tokenize)

            num_epochs = 1
            batch_size = 4 if DEVICE == "cuda" else 1
            grad_accum = 4 if DEVICE == "cuda" else 8
            estimated_steps = max(1, (len(dataset) // (batch_size * grad_accum)) * num_epochs)
            training_args = TrainingArguments(
                output_dir=str(output_dir),
                per_device_train_batch_size=batch_size,
                gradient_accumulation_steps=grad_accum,
                num_train_epochs=num_epochs,
                learning_rate=2e-4,
                fp16=(DEVICE == "cuda"),
                bf16=False,
                optim="adamw_8bit" if DEVICE == "cuda" else "adamw_torch",
                dataloader_num_workers=min(4, os.cpu_count() or 1),
                logging_steps=1,
                save_steps=50,
                save_total_limit=2,
                report_to="none",
            )

            _update_progress(train_total_steps=estimated_steps)

            trainer = Trainer(
                model=model,
                args=training_args,
                train_dataset=dataset,
                callbacks=[ProgressCallback(job_id)],
            )

            yield {"type": "status", "message": "Starting training..."}
            trainer.train()

            model.save_pretrained(output_dir)
            tokenizer.save_pretrained(output_dir)

            yield {"type": "complete", "output_dir": str(output_dir), "message": "HuggingFace PEFT training complete"}

        except ImportError as e:
            yield {"type": "error", "message": f"Missing dependency: {e}. Install with: pip install transformers peft datasets"}
        except Exception as e:
            yield {"type": "error", "message": f"HF training failed: {e}"}

    async def export_to_gguf(self, adapter_path: Path, output_name: str) -> dict[str, Any]:
        """
        Export LoRA adapter to GGUF format for Ollama.

        Args:
            adapter_path: Path to LoRA adapter.
            output_name: Name for output model.

        Returns:
            Export result dict.
        """
        try:
            gguf_path = self.settings.finetuned_path_resolved / f"{output_name}.gguf"
            return {
                "status": "info",
                "message": "GGUF export requires llama.cpp. Manual steps needed.",
                "adapter_path": str(adapter_path),
                "suggested_output": str(gguf_path),
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}


# ── Singleton ──────────────────────────────────────────────────────────────────

_finetuner: FineTuner | None = None


def get_finetuner() -> FineTuner:
    """Get finetuner singleton."""
    global _finetuner
    if _finetuner is None:
        _finetuner = FineTuner()
    return _finetuner
