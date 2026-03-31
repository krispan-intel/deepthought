#!/usr/bin/env python3
"""
Tree-sitter 語言編譯腳本
"""
import subprocess
import sys
from pathlib import Path
from loguru import logger

def setup_treesitter():
    
    logger.info("🌳 Setting up Tree-sitter languages...")
    
    # tree-sitter >= 0.23 用新的 API
    # 直接 import 語言 binding
    try:
        import tree_sitter_c
        import tree_sitter_cpp
        import tree_sitter_rust
        import tree_sitter_java
        import tree_sitter_python
        
        from tree_sitter import Language
        
        # 驗證語言載入
        languages = {
            "c":      tree_sitter_c.language(),
            "cpp":    tree_sitter_cpp.language(),
            "rust":   tree_sitter_rust.language(),
            "java":   tree_sitter_java.language(),
            "python": tree_sitter_python.language(),
        }
        
        for lang_name, lang in languages.items():
            lang_obj = Language(lang)
            logger.info(f"  ✅ {lang_name}: OK")
        
        logger.info("✅ Tree-sitter setup complete!")
        return True
        
    except ImportError as e:
        logger.error(f"❌ Tree-sitter setup failed: {e}")
        logger.info("Run: pip install tree-sitter-c tree-sitter-cpp ...")
        return False

if __name__ == "__main__":
    success = setup_treesitter()
    sys.exit(0 if success else 1)
