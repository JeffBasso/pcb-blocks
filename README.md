# pcb-blocks

Reusable circuit blocks for KiCad 10. Each block is a SKiDL Python module (the checked list of
parts and nets) paired with a KiCad design block (the drawn sheet), and the two are checked
against each other.

**Status: drawn and parity-checked; not yet bench-proven. No compliance certification
(IEEE 802.3bt, safety or EMC) is claimed.**

The first block, the 802.3bt PoE PD front end, is on the `poe-pd` pull request.

Licensed under the CERN Open Hardware Licence Version 2 - Permissive (CERN-OHL-P-2.0). See
[LICENSE](LICENSE).
