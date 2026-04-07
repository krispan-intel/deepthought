from scripts.cleanup_kernel_source_noise import classify_noise


def test_classify_noise_matches_commit_blob_with_hash_label() -> None:
    content = (
        "COMMIT: 0828ed4d9b2d AUTHOR: Sam Edwards DATE: 2024-12-18 03:39:21 "
        "FILES CHANGED: 1 MESSAGE: dt-bindings: arm64: bcmbca: Add Zyxel EX3510-B"
    )
    metadata = {"file_path": "data/raw/repos/linux/commits.jsonl"}

    matched, reasons, label = classify_noise(
        doc_id="8f8b2d04638648937891158c9580da58",
        content=content,
        metadata=metadata,
    )

    assert matched is True
    assert "hash_label" in reasons
    assert "commit_message_blob" in reasons
    assert "missing_semantic_metadata" in reasons
    assert label == "data/raw/repos/linux/commits.jsonl"


def test_classify_noise_does_not_match_regular_kernel_function() -> None:
    content = "static inline int vlan_insert_tag(struct sk_buff *skb) { return 0; }"
    metadata = {
        "file_path": "include/linux/if_vlan.h",
        "function_name": "vlan_insert_tag",
        "start_line": 458,
    }

    matched, reasons, label = classify_noise(
        doc_id="abc123",
        content=content,
        metadata=metadata,
    )

    assert matched is False
    assert "commit_message_blob" not in reasons
    assert "hash_label" not in reasons
    assert label == "vlan_insert_tag"
