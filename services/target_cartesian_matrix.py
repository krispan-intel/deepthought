"""
services/target_cartesian_matrix.py

Cartesian Matrix Target Generator:
Generates stable, grounded targets from a matrix of Intel keywords × Linux subsystems.

Purpose: Replace wild random-walk mutation with deterministic cross-product anchors
to ensure targets are physically plausible and findable in the vector corpus.

Matrix: 10 Intel keywords × 10 Linux subsystems = 100 stable targets
"""

from __future__ import annotations

import itertools
import random
from typing import List, Tuple

# Intel x86 Hardware Keywords — high-value patentable technologies
INTEL_KEYWORDS = [
    "TDX",              # Trust Domain Extensions (confidential computing)
    "eBPF",             # Extended Berkeley Packet Filter (kernel programmability)
    "CXL",              # Compute Express Link (memory/device interconnect)
    "AMX",              # Advanced Matrix Extensions (AI acceleration)
    "PEBS",             # Precise Event-Based Sampling (PMU profiling)
    "TSX",              # Transactional Synchronization Extensions (HLE/RTM)
    "APIC",             # Advanced Programmable Interrupt Controller
    "EPT",              # Extended Page Tables (VT-x nested paging)
    "AVX-512",          # Advanced Vector Extensions (SIMD)
    "RAPL",             # Running Average Power Limit (power telemetry)
]

# Linux Kernel Subsystems — major architectural domains
LINUX_SUBSYSTEMS = [
    "scheduler",        # Process scheduling (sched/)
    "memory management", # Page allocator, NUMA, TLB (mm/)
    "networking",       # TCP/IP stack, XDP, sk_buff (net/)
    "file system",      # VFS, ext4, XFS, btrfs (fs/)
    "block I/O",        # Block layer, I/O scheduler (block/)
    "interrupt handling", # IRQ, softirq, tasklets (kernel/irq/)
    "virtualization",   # KVM, VFIO, virt (virt/, arch/x86/kvm/)
    "device driver",    # PCI, DMA, driver model (drivers/)
    "synchronization",  # locks, RCU, barriers (kernel/locking/)
    "power management", # cpuidle, cpufreq, suspend (kernel/power/)
]

# Pre-computed Cartesian product matrix (100 entries)
_TARGET_MATRIX: List[Tuple[str, str]] = list(itertools.product(INTEL_KEYWORDS, LINUX_SUBSYSTEMS))


def generate_cartesian_target(index: int | None = None) -> str:
    """
    Generate a target from the Cartesian matrix.

    Args:
        index: Optional index into the matrix (0-99). If None, picks randomly.

    Returns:
        A formatted target string: "Optimize {subsystem} using {keyword}"
    """
    if index is None:
        index = random.randint(0, len(_TARGET_MATRIX) - 1)
    else:
        index = index % len(_TARGET_MATRIX)

    keyword, subsystem = _TARGET_MATRIX[index]
    return f"Optimize Linux {subsystem} using x86 {keyword} microarchitecture features"


def list_all_targets() -> List[str]:
    """Return all 100 Cartesian matrix targets."""
    return [
        f"Optimize Linux {subsystem} using x86 {keyword} microarchitecture features"
        for keyword, subsystem in _TARGET_MATRIX
    ]


def get_matrix_size() -> int:
    """Return the total number of targets in the matrix."""
    return len(_TARGET_MATRIX)
