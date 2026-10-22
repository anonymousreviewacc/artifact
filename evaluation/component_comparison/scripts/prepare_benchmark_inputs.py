import csv, pathlib
src=pathlib.Path(r"/path/to/Research_project\Baseline_app_comparision\02_Generation_Results\android_run\BaselineAblation\baseline_payloads.csv")
out=pathlib.Path(r"/path/to/Research_project\Baseline_app_comparision\03_Benchmark_Results\inputs")
rows=list(csv.DictReader(src.open(encoding="utf-8-sig", newline="")))
for variant in sorted({r["variant"] for r in rows}):
    dest=out/(variant+"_input.csv")
    selected=[r for r in rows if r["variant"]==variant]
    with dest.open("w",encoding="utf-8-sig",newline="") as f:
        w=csv.DictWriter(f,fieldnames=["category","mode","index","payload"]); w.writeheader()
        for r in selected: w.writerow({k:r[k] for k in w.fieldnames})
    print(variant, len(selected), len({r['payload'] for r in selected}), dest)
