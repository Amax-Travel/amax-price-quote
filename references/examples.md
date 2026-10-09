# Synthetic draft example

Replace identity placeholders through authorized CRM lookups. Confirm each amount and quantity with the salesperson. This example is not client data.

```json
{
  "job_id": "example-trip",
  "opportunity": {
    "person_ref": "verified-person-reference",
    "owner_email": "rep@example.com",
    "package_type": "UMRAH_CUSTOM",
    "travel_month": 10,
    "pax_adult": 2, "pax_child": 0, "pax_infant": 0
  },
  "quote": {
    "sar_to_cad_rate": {"value": "0.37", "confirmed": true}
  },
  "origin_groups": [{
    "key": "toronto", "label": "Toronto", "origin_iata": "YYZ", "pax_adult": 2,
    "flight_notes": "Confirmed booking reference",
    "flight_adult": {"amount": "1200", "currency": "CAD", "basis": "per_adult", "confirmed": true},
    "visa_adult": {"amount": "150", "currency": "CAD", "basis": "per_adult", "confirmed": true}
  }],
  "passengers": [{
    "key": "traveller1", "group_key": "toronto", "name": "Example Traveller",
    "category": "Adult", "confirmed": true
  }],
  "hotels": [{
    "key": "stay1", "city": "Madinah", "hotel_name": "Example Hotel",
    "check_in": "2026-10-21", "check_out": "2026-10-25", "stay_confirmed": true,
    "room_type": "Double", "qty": 1,
    "cost": {"amount": "1200.125", "currency": "CAD", "basis": "per_room_stay", "confirmed": true}
  }],
  "transfers": [{
    "key": "train1", "pricing_source": "custom", "car_type": "Train",
    "route_from": "Medina train station", "route_to": "Makkah train station", "qty": 2,
    "fare": {"amount": "160", "currency": "SAR", "basis": "per_passenger", "confirmed": true}
  }],
  "pricing": {
    "margin": {"amount": "300", "currency": "CAD", "basis": "per_quote", "confirmed": true},
    "commission": {"mode": "flat", "amount": "100", "currency": "CAD", "basis": "per_quote", "confirmed": true}
  },
  "unresolved": ["Confirm remaining passenger name"]
}
```
