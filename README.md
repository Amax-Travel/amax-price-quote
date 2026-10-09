# AMAX Price Quote

Import this repository as a complete skill: [SKILL.md](SKILL.md), `references/`, and `scripts/`. No ZIP is required.

```sh
git clone https://github.com/Amax-Travel/amax-price-quote.git
cd amax-price-quote
python3 scripts/doctor.py
python3 scripts/doctor.py --api
```

A GitHub import that only loads SKILL.md is incomplete. See [runtime recovery](references/runtime.md). Requires Python 3.10+ and the existing AMAX loopback sales gatekeeper for the scripts; API-tool runtimes follow the documented contracts. CRM stage updates require an authorized Twenty write connection. The current custom transport API accepts SAR only; native CAD transport remains an integration gap.

Test the full workflow in the target agent before production use. This repository contains no customer records or credentials.
