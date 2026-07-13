"""SaaS AI Repricing ingestion package.

Cache-first ingestion of Alpha Vantage (transcripts, fundamentals) and Sharadar
(point-in-time fundamentals, prices, reference data) into the rd_alpha database,
with cold backups to S3. See scripts/ingest_saas_ai.py for the CLI entrypoint.
"""
