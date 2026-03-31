from pydantic_settings import BaseSettings
from pydantic import Field
from pathlib import Path

class Settings(BaseSettings):
    
    # ── Internal LLM ─────────────────────
    internal_llm_base_url: str = Field(
        default="http://10.67.116.243:3001/v1"
    )
    internal_llm_api_key: str = Field(
        default="sk-xxx"
    )
    
    # ── Models ───────────────────────────
    maverick_model: str = Field(
        default="FLEX_STG_DeepSeek-V3-0324-671B"
    )
    debate_deep_thinker_model: str = Field(
        default="DCAI_GAUDI2_DeepSeek-R1-671B"
    )
    debate_code_expert_model: str = Field(
        default="qwen3-coder-480b-a35b-instruct-fp8"
    )
    debate_judge_model: str = Field(
        default="IT_DCAI_GAUDI2_Qwen3-32B"
    )
    embedding_model: str = Field(
        default="IKT-Qwen3-Embedding-8B"
    )
    
    # ── Claude ───────────────────────────
    anthropic_api_key: str = Field(default="")
    reality_checker_model: str = Field(
        default="claude-sonnet-4-5"
    )
    
    # ── Vector DB ────────────────────────
    vectordb_type: str = Field(default="chroma")
    vectordb_path: Path = Field(
        default=Path("./data/vectorstore")
    )
    
    # ── Data Paths ───────────────────────
    data_raw_path: Path = Field(
        default=Path("./data/raw")
    )
    data_processed_path: Path = Field(
        default=Path("./data/processed")
    )
    
    # ── Pipeline ─────────────────────────
    lambda_mmr: float = Field(default=0.7)
    max_revision_iterations: int = Field(default=3)
    min_confidence_score: float = Field(default=0.75)
    max_debate_rounds: int = Field(default=3)
    
    # ── Logging ──────────────────────────
    log_level: str = Field(default="INFO")
    log_path: Path = Field(default=Path("./logs"))
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

# 全域單例
settings = Settings()
