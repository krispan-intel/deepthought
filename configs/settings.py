"""
configs/settings.py

Global configuration for DeepThought.
Loaded from .env file via pydantic-settings.
"""

from pathlib import Path
from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ── Internal LLM ─────────────────────────────────────────────
    internal_llm_base_url: str = Field(
        default="http://10.67.114.161:3001/v1",
        validation_alias=AliasChoices("OPENAI_API_BASE", "INTERNAL_LLM_BASE_URL"),
    )
    internal_llm_api_key: str = Field(
        default="sk-xxx",
        validation_alias=AliasChoices("OPENAI_API_KEY", "INTERNAL_LLM_API_KEY"),
    )
    llm_request_timeout_seconds: int = Field(
        default=180
    )
    llm_request_max_attempts: int = Field(
        default=3
    )
    llm_request_backoff_seconds: float = Field(
        default=2.0
    )
    llm_backend: str = Field(
        default="openai"
    )
    copilot_cli_command: str = Field(
        default="gh copilot"
    )
    copilot_cli_timeout_seconds: int = Field(
        default=420
    )
    copilot_prompt_max_chars: int = Field(
        default=12000
    )
    llm_fallback_models: str = Field(
        default="DCAI_GAUDI2_DeepSeek-R1-671B,qwen3-coder-480b-a35b-instruct-fp8,IT_DCAI_GAUDI2_Qwen3-32B"
    )

    # ── Service Mode ────────────────────────────────────────────
    service_loop_interval_seconds: int = Field(default=300)

    # ── Notifications (SMTP) ────────────────────────────────────
    smtp_host: str = Field(default="")
    smtp_port: int = Field(default=587)
    smtp_username: str = Field(default="")
    smtp_password: str = Field(default="")
    smtp_use_tls: bool = Field(default=True)
    smtp_from: str = Field(default="")
    tid_notify_to: str = Field(default="")
    tid_email_notifications_enabled: bool = Field(default=False)

    # ── Models ───────────────────────────────────────────────────
    maverick_model: str = Field(
        default="DCAI_GAUDI2_DeepSeek-R1-671B"
    )
    debate_deep_thinker_model: str = Field(
        default="DCAI_GAUDI2_DeepSeek-R1-671B"
    )
    debate_code_expert_model: str = Field(
        default="qwen3-coder-480b-a35b-instruct-fp8"
    )
    debate_judge_model: str = Field(
        default="DCAI_GAUDI2_DeepSeek-R1-671B"
    )
    tid_formatter_model: str = Field(
        default="DCAI_GAUDI2_DeepSeek-R1-671B"
    )
    embedding_model: str = Field(
        default="IKT-Qwen3-Embedding-8B"
    )

    # ── Claude (Reality Checker) ──────────────────────────────────
    anthropic_api_key: str = Field(default="")
    reality_checker_model: str = Field(
        default="DCAI_GAUDI2_DeepSeek-R1-671B"
    )

    # ── Vector DB ────────────────────────────────────────────────
    vectordb_type: str = Field(default="chroma")
    vectordb_path: Path = Field(
        default=Path("./data/vectorstore")
    )
    sparse_index_path: Path = Field(
        default=Path("./data/vectorstore/sparse_sidecar.sqlite3")
    )
    qdrant_url: str = Field(
        default="http://localhost:6333"
    )

    # ── Data Paths ───────────────────────────────────────────────
    data_raw_path: Path = Field(
        default=Path("./data/raw")
    )
    data_processed_path: Path = Field(
        default=Path("./data/processed")
    )
    github_token: str = Field(default="")

    # ── Pipeline ─────────────────────────────────────────────────
    lambda_mmr: float = Field(default=0.7)
    triad_domain_threshold: float = Field(
        default=0.42,
        description="Domain cohesion threshold for void detection (lowered 7% from 0.45 to reduce 'No voids found' rate)"
    )
    triad_initial_candidate_pool_size: int = Field(default=300)
    triad_max_filtered_candidates: int = Field(default=220)
    max_revision_iterations: int = Field(default=5)
    min_confidence_score: float = Field(default=0.75)
    max_debate_rounds: int = Field(default=3)
    export_only_approved_tid: bool = Field(default=True)
    reject_on_stage_failure: bool = Field(default=True)
    patent_api_enabled: bool = Field(default=False)
    semantic_scholar_api_url: str = Field(
        default="https://api.semanticscholar.org/graph/v1/paper/search"
    )
    patent_shield_timeout_seconds: int = Field(default=8)
    patent_shield_max_results: int = Field(default=3)
    patent_conflict_threshold: float = Field(default=0.72)
    human_review_checkpoint_enabled: bool = Field(default=False)
    human_review_auto_approve: bool = Field(default=False)
    human_review_decisions_path: Path = Field(
        default=Path("./data/processed/human_review_decisions.jsonl")
    )

    # ── Target Generation ────────────────────────────────────────
    target_generation_mode: str = Field(
        default="cartesian",
        description="Target generation strategy: 'cartesian' (stable matrix) or 'random_walk' (LLM mutation)"
    )

    # ── Parallelism ──────────────────────────────────────────────
    pipeline_parallel_mode: bool = Field(default=False)
    maverick_workers: int = Field(default=2)
    max_maverick_queue_depth: int = Field(
        default=10,
        description="Maximum parallel Maverick tasks (caps n_drafts to prevent resource exhaustion)"
    )
    max_debate_queue_depth: int = Field(
        default=4,
        description="Maximum parallel debate panel reviewers (hard limit for 4 specialists)"
    )

    # ── Hybrid Triad Scoring ─────────────────────────────────────
    # Weight for marginality-fit bonus in hybrid_score.
    # Rewards pairs whose pairwise similarity lands in the centre of
    # the calibrated marginality band [τ_low, τ_high].
    marginality_fit_weight: float = Field(default=0.25)
    # Additive bias applied to every hybrid score so that all
    # qualifying pairs score > 0 (domain filter guarantees
    # relevance >= triad_domain_threshold).
    hybrid_score_bias: float = Field(default=0.10)

    # ── Logging ──────────────────────────────────────────────────
    log_level: str = Field(default="INFO")
    log_path: Path = Field(default=Path("./logs"))
    audit_log_enabled: bool = Field(default=True)
    audit_log_path: Path = Field(default=Path("./logs/audit/pipeline_audit.jsonl"))
    void_tracking_enabled: bool = Field(default=True)
    void_tracking_path: Path = Field(default=Path("./data/processed/void_history.jsonl"))


# Global singleton
settings = Settings()