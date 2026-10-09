# Confirmed quote inputs

A job has a stable `job_id`, verified `opportunity` person/owner and category counts, `quote` details, and at least one `origin_groups` row. Use stable keys for all rows; keep them unchanged when resuming. Each flight and passenger references a `group_key`. Group category counts must sum to the opportunity counts. Existing quote IDs are recovered from the original journal, not guessed from client names.

## Person versus opportunity

Put a supplied verified CRM person ID/link into `opportunity.person_ref`. Do not pass it to `/opportunities/resolve`, which expects an opportunity ID/link. With the package, month, counts, and verified owner, the first `apply` calls `POST /opportunities` to create or reuse the person's live deal, then binds the returned `twenty_id` to the quote. A missing opportunity lookup is not a missing person. Ask for identity only if the person itself is absent, invalid, or ambiguous after authorized lookup. Reuse the existing private journal if a quote was already started. Retrieve the salesperson owner from authorized context/CRM; do not assign the bot as owner.

The assistant works with many human salespeople. `owner_name` is accepted in place of `owner_email`; the adapter resolves it through `GET /opportunities/owners?q=NAME` before mutations. Use a unique returned match. For multiple matches ask for the distinguishing name; never guess an email pattern. `/users`, `/owners`, `/salespeople`, and `/me` are not this lookup. `/quotes/salespeople` is a scoped dashboard filter, not the assignable owner directory. Do not use a client's name as the salesperson, infer the sender from an old chat, or transfer a previous job's owner.

## Transport from itinerary

Use the last arriving airport after connections as the first ground pickup. Read the requested hotel order, train stations, sightseeing, and final departure airport to construct separate legs. Match each ground leg against `GET /transport-fares` and use the exact stored route/type labels. If the user requests a normal sedan and the table has one Camry/Sonata category, use it and state the choice. Do not substitute a larger vehicle or invent a missing fare. Include each requested ziyarat once, and remove superseded route assumptions before first apply.

Custom transport accepts a confirmed SAR or CAD unit fare. A CAD train fare uses `pricing_source: "custom"`, `car_type: "Train"`, explicit ticket `qty`, and `fare: {"amount": "150", "currency": "CAD", "basis": "per_passenger", "confirmed": true}`. The adapter checks native CAD support before writes and sends `cad_fare_micros`; Core multiplies it by ticket quantity. Fixed CAD fares do not change when SAR exchange rates change. Never relabel CAD as SAR or alter the quote's global rate to force a price. Preserve already confirmed currency and quantity; do not ask again.

If the user specifies only a total margin, map it to profit margin, not per-person margin or commission. Preserve any existing commission; for a new quote with no additional fee requested, use an explicitly documented zero additional commission rather than inventing a fee. Supplier inclusions remain attached to their source line; a later request to add transport overrides an earlier general “included” answer for transport. Do not silently infer that visas are free or included from an ambiguous answer.

Money uses decimal strings, explicit currency and basis, and `confirmed: true`. At most six decimal places are supported. Only conversion to integer micros occurs locally; Core owns pricing arithmetic. Record unknowns in `unresolved`. Confirm explicit zero margin when zero is intended. Missing extras are not evidence that the supplier includes them.

Hotel `check_in`, `check_out`, positive integer `qty`, and `stay_confirmed: true` are required. The cost is one room for the whole stay; dates determine nights. For a confirmed combined cost of 3414.65 for two rooms, each room costs exactly 1707.325. Never round that allocation to cents. Preserve the source combined amount in the private working notes.

A known first name can be entered exactly as supplied with `confirmed: true`, while `unresolved` records that the full passport name is pending. Do not invent unnamed passengers or nationality. Record the confirmed category and group; names do not determine the priced headcount. Keep overnight arrival dates and supplied PNR information in the relevant group's `flight_notes`; do not infer a PNR from raw itinerary status tokens.


| Form input | Job input | Core behavior |
| --- | --- | --- |
| Saved vehicle fare | `pricing_source: "fare_table"` (default), exact route/type and quantity; no `fare` | Requires one positive fare-table match; saved fare verified |
| Custom vehicle | `pricing_source: "custom"`, vehicle name, SAR or CAD `fare` with `basis: "per_vehicle"` | Unit fare × vehicle quantity; SAR converts at the quote rate |
| Train | Same custom format, `car_type: "Train"`, `basis: "per_passenger"` | Explicit ticket quantity; no assumption that infants need tickets |
| Hotel | CAD `cost` with `basis: "per_room_stay"` | Exact full-stay cost of one room × quantity; dates determine nights |
| Commission: flat | `mode: "flat"`, `basis: "per_quote"` | Exact total commission |
| Commission: per person | `mode: "per_person"`, `basis: "per_person"` | Input × engine total passenger count |
| Commission: round-up | `mode: "round_up"`, `basis: "target_per_person"` | Nonnegative top-up to target × engine passenger count, excluding prior commission |
| Flight extras | Group `extra_flight_adult`, `seat_adult`, `bag_adult` (also child/infant) | Confirmed CAD per-category amounts; never parent flight aggregates |
| Passport nationality | Group `visa_nationalities` plus `visa_nationalities_confirmed: true` | Preserves explicit nationality/category/count rows; no country inference |
| Itinerary / PNR | Group `flight_notes`; `flights` entries with `group_key` | Group-linked itinerary and PDF notes |

Pricing is applied **after** line items. On repeat apply it is recalculated only if its confirmed inputs or the engine's cost/headcount basis changed. The server uses integer micros and never compounds the previous commission. The mode is job intent; Core stores its resolved commission amount. After later cost changes, reapply this job to resolve the intent again.
