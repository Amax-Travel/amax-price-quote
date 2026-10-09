# Confirmed quote inputs

A job has a stable `job_id`, verified `opportunity` person/owner and category counts, `quote` details, and at least one `origin_groups` row. Use stable keys for all rows; keep them unchanged when resuming. Each flight and passenger references a `group_key`. Group category counts must sum to the opportunity counts. Existing quote IDs are recovered from the original journal, not guessed from client names.

Money uses decimal strings, explicit currency and basis, and `confirmed: true`. At most six decimal places are supported. Only conversion to integer micros occurs locally; Core owns pricing arithmetic. Record unknowns in `unresolved`. Confirm explicit zero margin when zero is intended. Missing extras are not evidence that the supplier includes them.

Hotel `check_in`, `check_out`, positive integer `qty`, and `stay_confirmed: true` are required. The cost is one room for the whole stay; dates determine nights. For a confirmed combined cost of 3414.65 for two rooms, each room costs exactly 1707.325. Never round that allocation to cents. Preserve the source combined amount in the private working notes.

A known first name can be entered exactly as supplied with `confirmed: true`, while `unresolved` records that the full passport name is pending. Do not invent unnamed passengers or nationality. Record the confirmed category and group; names do not determine the priced headcount. Keep overnight arrival dates and supplied PNR information in the relevant group's `flight_notes`; do not infer a PNR from raw itinerary status tokens.


| Form input | Job input | Core behavior |
| --- | --- | --- |
| Saved vehicle fare | `pricing_source: "fare_table"` (default), exact route/type and quantity; no `fare` | Requires one positive fare-table match; saved fare verified |
| Custom vehicle | `pricing_source: "custom"`, vehicle name, SAR `fare` with `basis: "per_vehicle"` | Unit fare × vehicle quantity × quote rate |
| Train | Same custom format, `car_type: "Train"`, `basis: "per_passenger"` | Explicit ticket quantity; no assumption that infants need tickets |
| Hotel | CAD `cost` with `basis: "per_room_stay"` | Exact full-stay cost of one room × quantity; dates determine nights |
| Commission: flat | `mode: "flat"`, `basis: "per_quote"` | Exact total commission |
| Commission: per person | `mode: "per_person"`, `basis: "per_person"` | Input × engine total passenger count |
| Commission: round-up | `mode: "round_up"`, `basis: "target_per_person"` | Nonnegative top-up to target × engine passenger count, excluding prior commission |
| Flight extras | Group `extra_flight_adult`, `seat_adult`, `bag_adult` (also child/infant) | Confirmed CAD per-category amounts; never parent flight aggregates |
| Passport nationality | Group `visa_nationalities` plus `visa_nationalities_confirmed: true` | Preserves explicit nationality/category/count rows; no country inference |
| Itinerary / PNR | Group `flight_notes`; `flights` entries with `group_key` | Group-linked itinerary and PDF notes |

Pricing is applied **after** line items. On repeat apply it is recalculated only if its confirmed inputs or the engine's cost/headcount basis changed. The server uses integer micros and never compounds the previous commission. The mode is job intent; Core stores its resolved commission amount. After later cost changes, reapply this job to resolve the intent again.

