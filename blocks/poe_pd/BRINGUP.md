# poe_pd bring-up

No measurements yet. The block hasn't been built (first board: wallnode-amp rev A).

Each row is one measurement on a real board. It names the board and rev, the PSE (make, model,
type and class it granted) and the instrument. A failed or surprising result is recorded here too,
and goes into BLOCK.md's errata.

| Date | Board / rev | Measurement | Condition (PSE, load) | Expected | Measured | Instrument | Notes |
|---|---|---|---|---|---|---|---|

Measurements to take first:
- detection and classification on an 802.3bt Type 4 PSE: the class granted, and TPH/TPL (POE_TPH_N /
  POE_TPL_N) for it;
- the same on a Type 3 and a Type 1/2 PSE (demotion: TPH/TPL as SLUSCD1C Tables 2-3 p19);
- inrush and the time to PG, POE_VDD at turn-on (scope);
- POE_VDD - PRI_RTN at full load, the RTN current, and U10's temperature;
- the TVS clamp and the bridge drop at full load (the bridge diodes' temperature).
