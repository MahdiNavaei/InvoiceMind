# GoldSet Card — GS-20260209-v1

- Project: InvoiceMind
- Partitions: Gold-Benchmark, Gold-Dev, Gold-EdgeCases
- Coverage: Mixed quality tiers (HIGH/MEDIUM/LOW), multilingual vendor patterns, numeric/date/currency variants
- Known limitations:
  - Seed-sized benchmark (for pipeline and governance validation)
  - Limited handwritten/document layout diversity
- Promotion rule:
  - Tuning only on Gold-Dev
  - Release gates only on Gold-Benchmark
