"""Download pinned public recipe/SDK inputs for one SpeedTree bake; no game/save uploads."""
from pathlib import Path
from urllib.request import urlopen
from urllib.parse import quote
import json,subprocess,hashlib
root=Path(__file__).resolve().parent;config=json.loads((root/'sources.json').read_text())
def fetch(source,name,target):
 url=source['repo'].replace('github.com','raw.githubusercontent.com')+'/'+source['commit']+'/'+quote(name)
 target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(urlopen(url,timeout=60).read());print(name,hashlib.sha256(target.read_bytes()).hexdigest())
for name,target in [('extern/include/SpeedTreeRT.h','sdk/SpeedTreeRT.h'),('extern/library/SpeedTreeRT.lib','sdk/SpeedTreeRT.lib')]:fetch(config['sdk'],name,root/target)
fetch(config['editor'],'SpeedTreeRT.dll',root/'SpeedTreeRT.dll')
for name in config['recipes']:fetch(config['client'],name,root/'recipes'/Path(name).name)
(root/'baked').mkdir(exist_ok=True)
