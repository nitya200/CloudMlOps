# Design patterns

Each pattern below is in the codebase because it solved a concrete problem, not to tick a
box. The problem is stated first.

---

## 1. Repository

**Problem.** If services build their own queries, ownership checks get duplicated and
occasionally forgotten, and every service needs a database to test.

**Implementation.** `app/repositories/` — a generic `BaseRepository[ModelT]` plus one
repository per aggregate. Services receive a `Session` and construct repositories; they never
write SQL.

```python
class SummaryRepository(BaseRepository[Summary]):
    model = Summary

    def get_for_user(self, summary_id, user_id) -> Summary | None:
        """Ownership is enforced in SQL, not after the fact in Python."""
        stmt = (
            self._with_request()
            .join(SummaryRequest, Summary.request_id == SummaryRequest.id)
            .where(Summary.id == summary_id, SummaryRequest.user_id == user_id)
        )
        return self.db.execute(stmt).unique().scalar_one_or_none()
```

**What it buys.** The ownership predicate is part of the query, so there is no code path that
loads a row and forgets to check who owns it. `HistoryService`, `FeedbackService` and
`SummarizationService` all reuse this one method, which is why "user A cannot touch user B's
summary" holds uniformly.

**Where to look:** `repositories/base.py`, `summary_repository.py`, `user_repository.py`.

---

## 2. Factory — document extraction

**Problem.** Three file formats need three parsers, and callers should not grow an
`if/elif` chain that has to be edited every time a format is added.

**Implementation.** `app/services/extraction_service.py`. `TextExtractor` defines the
contract, three subclasses implement `_parse`, and `DocumentExtractorFactory` maps a
`FileType` to a class through a registry.

```python
class DocumentExtractorFactory:
    _registry: dict[FileType, type[TextExtractor]] = {
        FileType.PDF: PdfExtractor,
        FileType.DOCX: DocxExtractor,
        FileType.TXT: TxtExtractor,
    }

    @classmethod
    def register(cls, file_type, extractor) -> None:
        cls._registry[file_type] = extractor

    @classmethod
    def create(cls, file_type) -> TextExtractor:
        ...
```

**What it buys.** Supporting HTML or RTF is one new class plus one `register` call —
`DocumentService` does not change. The base class also centralizes the parts every parser
needs: exception wrapping into `ExtractionError`, whitespace normalization, and the
"no readable text" check that catches scanned PDFs. Subclasses only implement parsing.

**Where to look:** `services/extraction_service.py`, tested in `tests/test_extraction.py`.

---

## 3. Strategy — summary length

**Problem.** "Short", "medium" and "long" differ in three ways at once: the instruction given
to the model, the decoder parameters, and the chunk size. Encoding that as scattered
conditionals inside the summarizer would entangle prompt design with inference code.

**Implementation.** `app/ai/prompts.py`. Each length is a class owning all three concerns.

```python
class ShortSummaryStrategy(SummaryLengthStrategy):
    length = SummaryLength.SHORT
    target_words = 55
    chunk_max_words = 350

    @property
    def params(self) -> GenerationParams:
        return GenerationParams(max_new_tokens=90, min_new_tokens=25, length_penalty=0.9)

    def instruction(self) -> str:
        return (
            "Summarize the following document in 2 to 3 sentences. "
            "Capture only the most important idea and outcome."
        )
```

**What it buys.** Two things beyond tidiness. First, both summarizer backends consume the
same strategy interface — `FlanT5Summarizer` reads `params` and `build_prompt`, while
`ExtractiveSummarizer` reads `target_words` — so a new length automatically works on both.
Second, prompt engineering becomes a local edit to one class instead of a change to the
generation loop.

**Where to look:** `ai/prompts.py`, consumed by `ai/flan_t5.py` and `ai/extractive.py`.

---

## 4. Strategy + Factory — summarizer backends

**Problem.** torch is a 200 MB dependency. Requiring it would make CI slow and would stop the
app running on a machine that cannot host the model — but the application must not grow two
parallel code paths.

**Implementation.** `Summarizer` (`ai/base.py`) is the abstraction; `FlanT5Summarizer` and
`ExtractiveSummarizer` implement it; `ai/factory.py` resolves and caches the choice.

```python
def resolve_backend(requested=None) -> str:
    choice = requested or settings.ai_backend
    if choice == "extractive":
        return "extractive"
    if choice == "flan-t5":
        if not transformers_available():
            raise SummarizationError("AI_BACKEND=flan-t5 requires transformers and torch")
        return "flan-t5"
    return "flan-t5" if transformers_available() else "extractive"
```

**What it buys.** `SummarizationService` depends only on `Summarizer`, so the same service
code serves production (FLAN-T5), CI (a deterministic stub) and constrained environments
(extractive). `AI_BACKEND=flan-t5` turns the graceful degradation into a hard failure for
deployments where a silent downgrade would be unacceptable — the default is convenient, but
the strict option exists.

**Where to look:** `ai/base.py`, `ai/factory.py`, `ai/flan_t5.py`, `ai/extractive.py`.

---

## 5. Singleton — model loader

**Problem.** Loading FLAN-T5 costs seconds of CPU and hundreds of megabytes. Doing it per
request would be unusable; doing it per thread would exhaust memory.

**Implementation.** `app/ai/model_loader.py` holds one instance per process, guarded by two
locks — one for instance creation, one for the load itself — because FastAPI serves
synchronous endpoints from a thread pool.

```python
def load(self) -> LoadedModel:
    if self._loaded is not None:
        return self._loaded
    with self._lock:
        if self._loaded is not None:  # another thread won the race
            return self._loaded
        self._loaded = self._do_load()
    return self._loaded
```

The double-checked lock avoids paying for the lock on the common path while still preventing
two threads from both loading the weights. `reset()` exists so tests can clear the cache.

**Where to look:** `ai/model_loader.py`, warmed up during the FastAPI lifespan in `main.py`.

---

## 6. Dependency injection

**Problem.** Tests need to swap the database session and the summarizer without patching
module globals.

**Implementation.** Two levels. FastAPI's `Depends` provides the session, the current user
and pagination:

```python
CurrentUser = Annotated[User, Depends(get_current_user)]
CurrentAdmin = Annotated[User, Depends(get_current_admin)]
Pagination   = Annotated[PaginationParams, Depends(pagination_params)]
```

…and services accept their collaborators as optional constructor arguments:

```python
class SummarizationService:
    def __init__(self, db: Session, summarizer: Summarizer | None = None) -> None:
        self._summarizer = summarizer  # injected in tests, resolved from the factory otherwise
```

**What it buys.** `tests/conftest.py` overrides `get_db` with the test session and calls
`set_summarizer(StubSummarizer())`. That is the whole reason 133 tests run in about three
seconds against real HTTP routes with no database container and no model download.

---

## 7. Template Method

**Problem.** Every extractor needs the same surrounding behaviour — wrap third-party
exceptions, normalize whitespace, reject empty output — and duplicating it three times means
one copy will eventually drift.

**Implementation.** `TextExtractor.extract` is the template; `_parse` is the hook.

```python
def extract(self, data: bytes) -> ExtractionResult:
    try:
        result = self._parse(data)          # the varying step
    except ExtractionError:
        raise
    except Exception as exc:                 # third-party parsers raise a wide range
        raise ExtractionError("Could not read the file …") from exc

    text = normalize_text(result.text)       # invariant post-processing
    if not text.strip():
        raise ExtractionError("No readable text was found …")
    return ExtractionResult(text=text, page_count=result.page_count)
```

**What it buys.** A new extractor cannot forget the error contract or the empty-text check,
because the base class owns them.

---

## 8. Data Transfer Objects

**Problem.** Returning ORM entities from endpoints leaks the schema — including
`password_hash` — and couples the API contract to the database.

**Implementation.** `app/schemas/` holds Pydantic models for every request and response.
`UserResponse` exposes only `id`, `name`, `email`, `role`, `is_active` and `created_at`; the
password hash has no way to reach a client. The generic `Page[ItemT]` envelope gives every
list endpoint the same shape, and `ErrorResponse` does the same for every failure.

---

## Patterns deliberately not used

Worth stating, because "no pattern" is also a decision:

- **Unit of Work** — SQLAlchemy's `Session` already is one. Wrapping it would add a layer
  that only forwards calls.
- **Observer / event bus** for usage metrics — the metric writes are synchronous and belong in
  the same transaction as the business change, precisely so the dashboard cannot disagree with
  the data. An event bus would trade that guarantee for indirection.
- **Abstract factory** over the repositories — there is one persistence technology. A factory
  producing repository families would be speculative generality.
