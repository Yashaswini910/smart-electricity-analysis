
# Tariff Data

This folder contains domestic electricity tariff schedules.

## Important

A tariff is used by the application only when:

- The state matches.
- The DISCOM matches.
- The consumer category matches.
- The tariff has been checked against the applicable official tariff order.
- The `verified` field is set to `true`.

Do not activate a tariff using guessed or outdated rates.

## Adding a tariff

Create or update a JSON file with this structure:

```json
[
  {
    "state": "State Name",
    "discom": "DISCOM Name",
    "category": "Domestic - General",
    "effective_date": "YYYY-MM-DD",
    "verified": false,
    "verification_note": "Verification details",
    "slabs": [
      {"upper": 50, "rate": 2.00},
      {"upper": 100, "rate": 3.00},
      {"upper": null, "rate": 5.00}
    ],
    "fixed_charge": 10.0,
    "max_units": null
  }
]
```

The rates above are illustrative format examples only. They are not actual electricity tariff recommendations.

### Fields

- `state`: State or Union Territory.
- `discom`: Exact provider name used in `states.json`.
- `category`: Must match the app's category.
- `effective_date`: Date from which the tariff applies.
- `verified`: Must be `true` before the app uses it.
- `slabs`: Incremental slab limits and rates.
- `fixed_charge`: Configured fixed charge for the applicable billing period.
- `max_units`: Optional maximum consumption supported by this schedule.

The current calculation engine handles energy charges and one configured fixed charge. It does not yet model every provider's electricity duty, fuel adjustment, subsidy, meter rent, demand charge, or other bill-specific components. Add those only after implementing and verifying their calculation rules.
