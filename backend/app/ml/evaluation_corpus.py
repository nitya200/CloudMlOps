"""Fixed holdout pairs for offline ROUGE evaluation."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class EvaluationSample:
    source_text: str
    reference_summary: str


EVALUATION_SAMPLES: tuple[EvaluationSample, ...] = (
    EvaluationSample(
        source_text=(
            "Cloud computing lets teams deploy web applications without buying physical servers. "
            "Containers package the application and its dependencies so the same image runs in "
            "development and production. Continuous integration runs automated tests on every change, "
            "and continuous delivery publishes approved builds to managed platforms such as AWS App Runner."
        ),
        reference_summary=(
            "Cloud platforms and containers help teams ship web apps without owning hardware, "
            "while CI/CD automates testing and deployment to services like App Runner."
        ),
    ),
    EvaluationSample(
        source_text=(
            "Abstractive summarization models generate new sentences rather than copying phrases "
            "from the source document. FLAN-T5-small is an instruction-tuned seq2seq model that "
            "works well for short inputs but needs chunking for long reports. Administrators track "
            "quality with user ratings and offline ROUGE scores before promoting a new model version."
        ),
        reference_summary=(
            "Abstractive models like FLAN-T5 rewrite documents in new words; long inputs require "
            "chunking, and admins use ratings plus ROUGE before approving model releases."
        ),
    ),
    EvaluationSample(
        source_text=(
            "PostgreSQL stores users, documents, summary requests, and feedback in normalized tables. "
            "Alembic migrations version the schema so production databases evolve safely. "
            "Secrets such as database URLs and JWT signing keys live in AWS Secrets Manager rather "
            "than in source control."
        ),
        reference_summary=(
            "The app persists data in normalized PostgreSQL tables with Alembic migrations, "
            "keeping secrets in AWS Secrets Manager instead of the repository."
        ),
    ),
)
