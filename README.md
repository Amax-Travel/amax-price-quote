# AMAX Price Quote

Import this GitHub repository URL into your agent's skills interface:

https://github.com/Amax-Travel/amax-price-quote

The complete skill is a normal folder, not a ZIP: `SKILL.md`, `references/`, and `scripts/`. The importer must fetch supporting files recursively. Review the imported files, then enable the skill. An importer that reports “v1 imports only SKILL.md” must be updated; the entrypoint alone is incomplete.

Run `python3 scripts/doctor.py --api` from the installed skill directory to verify the files and deployed API capabilities. This skill requires the authorized AMAX sales-host gatekeeper; the public repository contains no credentials or customer records.

The workflow creates and updates drafts, resolves salesperson names, uses saved transport fares or confirmed SAR/CAD custom fares, applies margin and commission through Core, downloads customer/internal PDFs, and publishes an explicitly approved quote into CRM. The linked opportunity moves to Building Quote during preparation and Package Quote Presented after publication. Publication is separate from customer messaging.

All scripts stay inside this skill. Keep client jobs, journals, lifecycle records, and PDFs in private working folders outside it. Preserve each client's original journal when resuming. Python 3.10+ is required; there are no third-party Python dependencies.
