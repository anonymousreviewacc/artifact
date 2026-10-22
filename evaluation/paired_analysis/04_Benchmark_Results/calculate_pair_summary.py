import csv
from pathlib import Path
p=Path(r'/path/to/Research_project\The_6th_model_test\04_Benchmark_Results\model_prediction_runtime_pairs.csv')
with p.open(newline='',encoding='utf-8-sig') as f: rows=list(csv.DictReader(f))
from collections import Counter
c=Counter((r['classification_correct'],r['runtime_confirmed']) for r in rows)
print(c)
for k,v in c.items(): print(k,v,round(v*100/len(rows),2))
print('supports',len(rows))
