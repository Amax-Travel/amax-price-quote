# Runtime checks and missing-file recovery

Canonical complete skill: https://github.com/Amax-Travel/amax-price-quote

An import must include `SKILL.md`, `references/`, and `scripts/`. Pasting only SKILL.md into a skill editor does not install its linked files. A public repository does not grant CRM/API access.

## With shell/filesystem tools

Locate this skill's directory and run `python3 scripts/doctor.py --api` there. Use the script paths relative to that directory, not an older `sales/scripts/quote-prototype` installation. A healthy check proves read access to the pricing contract and fares, not write permissions or CRM stage capabilities.

If files are missing, inspect available workspace locations, then recover the complete public repository to a new permitted directory:

```sh
git clone https://github.com/Amax-Travel/amax-price-quote.git /permitted/new-directory/amax-price-quote
```

Use the runtime's actual writable path, not this placeholder. Do not overwrite an existing checkout or move/delete client jobs and journals. Execute the recovered skill directly if the runtime permits; registration in the agent's skill UI may still be a separate operation. Rerun the check. Do not install scattered script copies into a sales scripts folder.

## With API tools but no shell

Discover the available authenticated Core/CRM tools and inspect their schemas. Read references using repository/file tools or GitHub raw files at a single commit revision. API calls do not require a computer/browser. Follow the confirmed payloads and ordering in the references. Check the pricing contract before mutations, keep a durable private operation record, and verify responses. If durable state is unavailable, do not initiate a multi-write workflow that cannot be safely resumed.

The required sequence is create/reuse opportunity from person, create/reuse draft, origin groups, linked flights/passengers, hotels, transport, pricing, totals, then PDF. Do not pass a person ID to opportunity resolution. Use the customer PDF endpoint for the actual server-generated PDF; do not reconstruct a final PDF from arithmetic in chat.

Use the runtime's binary download/artifact mechanism to deliver the PDF. A successful API request without a delivered file is not task completion. If the runtime has neither file tools nor a way to return binary API output, report that specific missing capability.

## Blocker reporting

Distinguish missing local files, network unavailability, API authorization, unsupported currency, and absent business inputs. State the attempted check and result once. Continue independent work and retain confirmed inputs. Never convert a recoverable missing reference into repeated customer questions, or claim a browser is required for an available API.
