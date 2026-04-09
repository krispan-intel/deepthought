"""
Tests for Cartesian Matrix target generation.
"""

from __future__ import annotations

from services.target_cartesian_matrix import (
    INTEL_KEYWORDS,
    LINUX_SUBSYSTEMS,
    generate_cartesian_target,
    get_matrix_size,
    list_all_targets,
)


def test_matrix_size():
    """Test that matrix size equals keyword count × subsystem count."""
    expected = len(INTEL_KEYWORDS) * len(LINUX_SUBSYSTEMS)
    assert get_matrix_size() == expected
    assert get_matrix_size() == 100  # 10 × 10


def test_generate_target_with_index():
    """Test that target generation is deterministic with index."""
    target_0 = generate_cartesian_target(index=0)
    target_0_again = generate_cartesian_target(index=0)
    assert target_0 == target_0_again

    target_1 = generate_cartesian_target(index=1)
    assert target_0 != target_1


def test_generate_target_random():
    """Test that random target generation works."""
    target = generate_cartesian_target()
    assert isinstance(target, str)
    assert len(target) > 0
    assert "Optimize Linux" in target
    assert "using x86" in target


def test_generate_target_wraps_around():
    """Test that index wraps around matrix size."""
    target_0 = generate_cartesian_target(index=0)
    target_100 = generate_cartesian_target(index=100)
    target_200 = generate_cartesian_target(index=200)
    assert target_0 == target_100 == target_200


def test_list_all_targets():
    """Test that all targets can be enumerated."""
    all_targets = list_all_targets()
    assert len(all_targets) == 100
    assert len(set(all_targets)) == 100  # All unique


def test_target_format():
    """Test that generated targets follow expected format."""
    target = generate_cartesian_target(index=0)
    assert target.startswith("Optimize Linux ")
    assert " using x86 " in target
    assert " microarchitecture features" in target


def test_all_keywords_covered():
    """Test that all Intel keywords appear in the matrix."""
    all_targets = list_all_targets()
    for keyword in INTEL_KEYWORDS:
        assert any(keyword in t for t in all_targets), f"Keyword {keyword} not found in any target"


def test_all_subsystems_covered():
    """Test that all Linux subsystems appear in the matrix."""
    all_targets = list_all_targets()
    for subsystem in LINUX_SUBSYSTEMS:
        assert any(subsystem in t for t in all_targets), f"Subsystem {subsystem} not found in any target"
