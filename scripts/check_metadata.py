"""Small consistency gate; official TT actions do the authoritative schema/PDK checks."""
import json
import re
from pathlib import Path

root = Path(__file__).resolve().parents[1]
info = (root / 'info.yaml').read_text()
assert re.search(r'yaml_version:\s*6\b', info)
assert re.search(r'language:\s*"Verilog"', info)
assert 'wokwi_id' not in info
assert re.search(r'top_module:\s*"tt_um_zarina_phone_flight"', info)
shape = re.search(r'tiles:\s*"([0-9]+x[0-9]+)"', info).group(1)
assert shape in {'1x1', '1x2'}, 'Unsupported or over-budget footprint'
sources = re.findall(r'^    - "([^"]+\.v)"', info, flags=re.M)
assert len(sources) == 7 and all((root / 'src' / s).is_file() for s in sources)
assert 'cells.v' not in sources
assert re.search(r'clock_hz:\s*25200000\b', info)
config = json.loads((root / 'src/config.json').read_text())
assert abs(config['CLOCK_PERIOD'] - 1e9 / 25200000) < 1e-6
assert config['RUN_LINTER'] == 1 and config['RUN_CTS'] == 1
assert (root / 'LICENSE').read_text().find('Apache License') >= 0
print('PASS: metadata, source list, SKY clock constraint, legal <=3-tile footprint, license')
