# Supplier catalog normalization

Build canonical product records, source mappings, and explicit uncertainty from
data/catalog.jsonl using data/rules.json. Tasks own the SKU lists in scopes.json;
the overlapping lists intentionally share a complete boundary product. Final
assembly must deduplicate that product and its source mappings globally.

Identity is canonical brand + normalized model + category + integer pack_size.
Storage also uses normalized capacity_gb; cables also use normalized length_mm.
Never collapse near models or different packs/capacities. Model normalization
only removes spaces and hyphens and uppercases; an S suffix is significant.
pack_size is an integer or '<integer> pcs'. Missing model or pack_size makes a
source unresolved; use reason missing_model or missing_pack_size respectively.
Marketing titles cannot fill missing identity dimensions.

entity_id format: BRAND_UPPER:MODEL:category:packN, plus :gbN for storage or :mmN
for cables. Canonical brand uses the alias map's display value. Convert capacity,
length and power using the exact decimal factors in rules.json. Canonical keys
are capacity_gb, length_mm, power_w, connector, interface and color as applicable.
Normalize connector/interface aliases and lowercase color; monetary-style binary
prefix assumptions (1 TB=1024 GB) are not allowed. All generated normalized
numeric attributes are integers.

For every attribute choose the normalized value at the lowest source_priority.
If that priority contains conflicting values, retain null and flag unresolved_tie;
do not break ties by majority or input order. Any disagreement across sources
creates a conflict object: attribute, observed_values (distinct normalized values),
chosen_value, resolution (higher_priority or unresolved_tie), source_skus (all
sources of this entity). Entity objects contain entity_id, brand, model, category,
pack_size, attributes, source_skus and conflicts (empty list when none).

source_map has one entry per scoped physical source:
{source_sku, source_row: original row_id, entity_id, reason}.
For mapped sources reason=null. For unresolved sources entity_id=null.
uncertain contains {kind:'source',source_sku,source_row,reason} for unresolved
sources, and {kind:'attribute',entity_id,attribute,source_skus} for unresolved
attribute ties; the latter lists only sources at the conflicting top priority.

Return {kind:'json',value:{scope:TASK_ID,entities:[...],source_map:[...],
uncertain:[...],summary:{entity_count:N,source_count:N,mapped_source_count:N,
unmapped_source_count:N,uncertain_count:N}}}. Include all canonical identity and
attribute evidence for each scoped product. Arrays may be in any order but must
not contain duplicate records, identifiers, or values. Empty sections are lists.

The optional investigation returns {kind:'json',value:{findings:[all global
uncertain records],evidence_rows:[supporting original row_id values]}}. It is
evidence for supplier follow-up, not a substitute for the catalog. Final grading
checks unique global entities, every source mapping, canonical values, conflicts
and uncertainty independently; merely collecting all task IDs does not pass.
