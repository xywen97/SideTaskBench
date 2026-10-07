"""Explicit host↔side-task pairings for the host-tailored cohort.

The original experiment pairs every host task with every atomic unit (a full
cross product).  The host-tailored cohort is different in kind: each new side
task is written to sit inside a *specific* host task's technical domain, so it
is only meaningful next to that one host.  Pairing is therefore an explicit
list, not a cartesian product.
"""

# Each entry binds one host task to the single side task authored for its
# reference domain.  The side task's deliverable is never imported by the host
# repair and never contributes to the host grade.
HOST_TAILORED_PAIRS = (
    ("coding-05", "cache-access-report"),
    ("coding-09", "manifest-digest-summary"),
    ("coding-13", "window-stats-helper"),
    ("coding-16", "mailbox-domain-report"),
    ("coding-17", "report-node-schema"),
    ("coding-18", "mro-attribute-index"),
    ("coding-23", "dispatch-specialization-report"),
    ("coding-25", "amount-scale-note"),
    ("coding-01", "csv-dialect-report"),
    ("coding-02", "jsonl-line-report"),
    ("coding-03", "url-component-summary"),
    ("coding-04", "retry-last-attempt"),
    ("coding-06", "timestamp-offset-report"),
    ("coding-07", "cursor-empty-page-continues"),
    ("coding-08", "dag-level-summary"),
    ("coding-10", "header-hop-classification"),
    ("coding-11", "config-layer-merge"),
    ("coding-12", "archive-member-summary"),
    ("coding-14", "reachable-nodes"),
    ("coding-15", "pipeline-stage-summary"),
    ("coding-19", "prime-power-factors"),
    ("coding-20", "rst-column-widths"),
    ("coding-21", "dag-lexicographic-order"),
    ("coding-22", "template-token-summary"),
    ("coding-24", "cache-transitive-invalidation"),
)


def normalize_pairs(pairs):
    """Validate an explicit pair list and return it as a tuple of tuples.

    Raises ValueError for anything that is not a sequence of two nonempty
    strings, so a malformed CLI argument or manifest fails loudly instead of
    silently producing an empty plan.
    """
    if pairs is None:
        return HOST_TAILORED_PAIRS
    if not isinstance(pairs, (list, tuple)) or not pairs:
        raise ValueError("Explicit pairs must be a nonempty list of (host, side task) tuples")
    normalized = []
    for index, pair in enumerate(pairs):
        if not isinstance(pair, (list, tuple)) or len(pair) != 2:
            raise ValueError(f"Pair {index} must be a (host_task_id, atomic_task_id) tuple")
        host, task = pair
        if not isinstance(host, str) or not host or not isinstance(task, str) or not task:
            raise ValueError(f"Pair {index} must contain two nonempty strings")
        normalized.append((host, task))
    if len(normalized) != len(set(normalized)):
        raise ValueError("Explicit pairs must be unique")
    return tuple(normalized)


def pairs_from_manifest(manifest: dict):
    """Read the persisted pair list, falling back to the built-in cohort."""
    stored = manifest.get("pairs")
    if stored is None:
        return HOST_TAILORED_PAIRS
    return tuple(tuple(pair) for pair in stored)
