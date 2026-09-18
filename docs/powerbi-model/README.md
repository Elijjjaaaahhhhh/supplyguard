# Power BI model review snapshot

These TMDL extracts make the Phase 10 measures, changed import partitions, outlook columns and relationships reviewable in Git. They are documentation extracts, not a second report or a standalone deployable semantic model. The authoritative report remains `app/SupplyGuard.pbix`.

Imports use standard PostgreSQL navigation to stable mart views. No connection credentials are stored here. Existing Store/Product dimensions filter all facts in one direction. The outlook target date deliberately has no relationship to the historical date dimension, whose observations end one day earlier.
