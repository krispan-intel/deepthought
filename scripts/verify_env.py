# scripts/verify_env.py

def verify():
    checks = []
    
    # LangGraph
    try:
        import langgraph
        from langgraph import __version__ as lg_version
        checks.append(("LangGraph", "✅", lg_version))
    except (ImportError, ImportError):
        try:
            import langgraph.graph
            checks.append(("LangGraph", "✅", "installed"))
        except ImportError as e:
            checks.append(("LangGraph", "❌", str(e)))
    
    # Tree-sitter
    try:
        import tree_sitter_c
        from tree_sitter import Language, Parser
        checks.append(("Tree-sitter C", "✅", "OK"))
    except ImportError as e:
        checks.append(("Tree-sitter C", "❌", str(e)))
    
    # ChromaDB
    try:
        import chromadb
        checks.append(("ChromaDB", "✅", chromadb.__version__))
    except ImportError as e:
        checks.append(("ChromaDB", "❌", str(e)))
    
    # Anthropic
    try:
        import anthropic
        checks.append(("Anthropic", "✅", anthropic.__version__))
    except ImportError as e:
        checks.append(("Anthropic", "❌", str(e)))
    
    # Internal LLM
    try:
        from openai import OpenAI
        from configs.settings import settings
        client = OpenAI(
            base_url=settings.internal_llm_base_url,
            api_key=settings.internal_llm_api_key
        )
        models = client.models.list()
        checks.append(("Internal LLM", "✅", 
                       f"{len(models.data)} models"))
    except Exception as e:
        checks.append(("Internal LLM", "❌", str(e)))
    
    # 輸出結果
    print("\n🔍 Environment Verification")
    print("─" * 40)
    for name, status, info in checks:
        print(f"  {status} {name}: {info}")
    print("─" * 40)
    
    all_ok = all(s == "✅" for _, s, _ in checks)
    print(f"\n{'✅ All systems GO!' if all_ok else '❌ Fix issues above'}")
    return all_ok

if __name__ == "__main__":
    verify()
