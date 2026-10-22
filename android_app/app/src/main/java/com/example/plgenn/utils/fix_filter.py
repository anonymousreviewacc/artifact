from pathlib import Path
p=Path(r"/path/to/Research_project\app-network-plgen\app\src\main\java\com\example\plgenn\utils\LTIGModelHelper.java")
s=p.read_text(encoding="utf-8")
lines=s.splitlines()
new=r'    private static final String KERAS_FILTERS = "!\"#$%&()*+,-./:;<=>?@[\\]^_`{|}~";'
for i,line in enumerate(lines):
    if "private static final String KERAS_FILTERS" in line:
        lines[i]=new
        break
else: raise SystemExit("filter line not found")
p.write_text("\n".join(lines)+"\n",encoding="utf-8")
