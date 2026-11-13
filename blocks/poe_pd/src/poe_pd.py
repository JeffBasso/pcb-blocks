"""Test harness for the poe_pd block: pcb-skidl.ps1 builds board() and compares it with the drawn
sheet (poe_pd.kicad_sch, whose one sheet "PoE PD" is the design block). Not copied to boards."""
import os

import skidl
from skidl import Net

from blocks.poe_pd import poe_pd

_LIB = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..', 'lib'))


def board():
    # The repo's own library, so the block builds from a checkout without the installer.
    for paths in skidl.lib_search_paths.values():
        if _LIB not in paths:
            paths.append(_LIB)
    ports = [Net(n) for n in ('PR12', 'PR36', 'PR45', 'PR78', 'POE_VDD', 'PRI_RTN', 'VCIN', 'VCOUT',
                              'CONV_SS', 'POE_TPH_N', 'POE_TPL_N', '+3V3', 'GND')]
    poe_pd(*ports)
