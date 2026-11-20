# poe_pd bring-up

No measurements yet. The block hasn't been built (first board: wallnode-amp rev A).

Each row is one measurement on a real board. It names the board and rev, the PSE (make, model,
type and class it granted) and the instrument. A failed or surprising result is recorded here too,
and goes into BLOCK.md's errata.

| Date | Board / rev | Measurement | Condition (PSE, load) | Expected | Measured | Instrument | Notes |
|---|---|---|---|---|---|---|---|

Measurements to take first (rev B, LT4294 + LT4321):
- detection and classification on an 802.3bt Type 4 PSE: the class granted, and T2P (POE_T2P_N) for it,
  its duty cycle and frequency on the isolated side (scope), against LT4294 Table 3 p9 and the decode bands
  in BLOCK.md section 4;
- the same on a Type 3 and a Type 1/2 PSE (demotion: 50% / low / Hi-Z, LT4294 Table 4 p10);
- inrush and the time to PWRGD, POE_VDD at turn-on (scope), with the board's own load on POE_VDD
  (expected <= 0.35 A for the first 80 ms, BLOCK.md section 3);
- the LT4321 enabling: the BR_EN pin after power-on, and the bridge drop (IN - OUTP) at full load;
- at the highest load the PSE grants, held for 30 minutes: an IR picture of the eight bridge FETs and Q58,
  with the PSE first on one pair set only (data pairs, then spare pairs) and then on four pairs. Expected
  Tj well under BLOCK.md section 5a's worst-case figures (those use the 175 C Rds(on));
- the TVS clamp, if a surge test is available.
