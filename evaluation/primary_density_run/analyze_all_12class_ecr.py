import csv
import json
import pathlib
from collections import Counter

BASE = pathlib.Path(r"/path/to/Research_project\The_6th_model_test\08_Density_Mutation_Validation")
BENCH = BASE / "05_Benchmark_Results"
PAYLOADS = BASE / "02_App_Payloads" / "density_generated_payloads.csv"

with PAYLOADS.open(encoding="utf-8-sig", newline="") as f:
    generated = list(csv.DictReader(f))
with (BENCH / "density_benchmark_results.csv").open(encoding="utf-8-sig", newline="") as f:
    original = list(csv.DictReader(f))
with (BENCH / "ssrf_loopback_validation.csv").open(encoding="utf-8-sig", newline="") as f:
    ssrf = list(csv.DictReader(f))
with (BENCH / "rfi_local_only_validation.csv").open(encoding="utf-8-sig", newline="") as f:
    rfi = list(csv.DictReader(f))
with (BENCH / "xxe_local_only_validation.csv").open(encoding="utf-8-sig", newline="") as f:
    xxe = list(csv.DictReader(f))
with (BENCH / "ecr_by_class_profile.csv").open(encoding="utf-8-sig", newline="") as f:
    existing_ecr = list(csv.DictReader(f))

classes = ["SQL Injection", "XSS", "IDOR", "Command Injection", "Path Traversal", "SSRF",
           "Local File Inclusion", "Remote File Inclusion", "XXE", "GraphQL Injection",
           "Open Redirect", "API Abuse"]
valid_oracle = {r["category"] for r in existing_ecr}
known = {}
for category in valid_oracle:
    rows = [r for r in existing_ecr if r["category"] == category]
    n = sum(int(r["oracle_supported_site_payload_trials"]) for r in rows)
    yes = sum(int(r["confirmed"]) for r in rows)
    known[category] = (n, yes, "Direct behavioral oracle; original local benchmark campaign")

ssrf_tested = [r for r in ssrf if r["status"] != "SKIPPED"]
known["SSRF"] = (len(ssrf_tested), sum(str(r["confirmed"]).lower() == "true" for r in ssrf_tested),
                  "Loopback-only XVWA probes; 0.0.0.0 and metadata-IP rows skipped; fetch/write failure observed")
rfi_tested = [r for r in rfi if r["Scheme"] == "http" and str(r["Confirmed"]).lower() == "true"]
known["Remote File Inclusion"] = (len(rfi_tested), len(rfi_tested),
                                  "Controlled bWAPP local-canary proof; generated HTTP hosts remapped to loopback; HTTPS skipped")
xxe_tested = [r for r in xxe if r["Status"] != "SKIPPED"]
known["XXE"] = (len(xxe_tested), sum(str(r["Confirmed"]).lower() == "true" for r in xxe_tested),
                "Controlled bWAPP XML-wrapper probes; no passwd marker observed; URL-encoded Evasion rows skipped as invalid raw XML")

out = []
for category in classes:
    n_generated = sum(r["category"] == category for r in generated)
    trials = [r for r in original if r["Category"] == category]
    if category in known:
        n, confirmed, scope = known[category]
        out.append({"category": category, "app_generated_unique_payloads": n_generated,
                    "benchmark_rows_in_main_run": len(trials), "ECR_trials": n, "confirmed": confirmed,
                    "ECR_percent": f"{100*confirmed/n:.2f}" if n else "NA", "status": "MEASURED_WITH_SCOPE_LIMIT",
                    "scope_and_limit": scope})
    else:
        # The rows exist, but available test routes do not offer a class-specific success oracle.
        out.append({"category": category, "app_generated_unique_payloads": n_generated,
                    "benchmark_rows_in_main_run": len(trials), "ECR_trials": 0, "confirmed": 0,
                    "ECR_percent": "NA", "status": "NOT_ESTIMABLE_NO_VALIDATED_ORACLE",
                    "scope_and_limit": "Responses were observed, but no class-specific authorization, execution, or parser oracle was validated; do not convert this to 0% ECR."})

with (BENCH / "ecr_all_12_class_coverage.csv").open("w", encoding="utf-8-sig", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=list(out[0]))
    writer.writeheader()
    writer.writerows(out)

# A conservative outcome summary for a revised Table 9. It does not relabel
# missing oracle signals as filtering or runtime-invalid states.
total_rows = len(original)
confirmed_total = sum(r["Confirmed"].lower() == "true" for r in original)
supported_trials = sum(int(r["oracle_supported_site_payload_trials"]) for r in existing_ecr)
sql_errors = sum(r["Outcome"] == "SQL_ERROR_SIGNAL_UNCONFIRMED" for r in original)
safety_skips = sum(r["Outcome"] == "SKIPPED_SAFETY_OR_SIDE_EFFECT" for r in original)
environment_errors = sum(r["Category"] == "SQL Injection" and r["Site"] == "bWAPP" for r in original)
oracle_no_confirmation = supported_trials - confirmed_total - sql_errors
unvalidated_oracle_rows = total_rows - supported_trials - environment_errors - safety_skips
states = [
    ("Confirmed behavioral signal", confirmed_total, "Explicit class-specific behavioral oracle; ECR numerator."),
    ("Oracle-supported, no confirmation", oracle_no_confirmation, "No predefined success signal; does not prove target safety."),
    ("SQL error signal, unconfirmed", sql_errors, "Error text observed; not counted as exploit confirmation."),
    ("No validated class-specific oracle", unvalidated_oracle_rows, "Observed response but no defensible success/failure oracle."),
    ("Benchmark environment error", environment_errors, "bWAPP SQL route/configuration issue; excluded from ECR."),
    ("Safety skipped", safety_skips, "SSRF/RFI main-run cases withheld from server-side fetch/include."),
]
table9 = [{"Observed outcome group": name, "Count": count, "Percent of all 825 rows": f"{100*count/total_rows:.2f}",
           "Interpretation": note} for name, count, note in states]
assert sum(x[1] for x in states) == total_rows
with (BENCH / "table9_observed_outcomes_revised.csv").open("w", encoding="utf-8-sig", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=list(table9[0]))
    writer.writeheader()
    writer.writerows(table9)

summary = {
    "scope": "All 12 app categories are listed; a numeric ECR is reported only where the trial had a validated class-specific oracle.",
    "pooled_comparable_ecr": "274/625 = 43.84%; six classes from the original benchmark run only.",
    "controlled_supplemental_trials": {
        "SSRF": f"{sum(str(r['confirmed']).lower() == 'true' for r in ssrf_tested)}/{len(ssrf_tested)} confirmed in loopback-only probes; not a broad SSRF ECR.",
        "RFI": f"{len(rfi_tested)}/{len(rfi_tested)} local-canary inclusion confirmed among HTTP payloads; HTTPS cases skipped; not a broad external-source ECR.",
        "XXE": f"{sum(str(r['Confirmed']).lower() == 'true' for r in xxe_tested)}/{len(xxe_tested)} local-file-marker confirmations in context-adapted XML; Evasion URL-encoded fragments skipped."
    },
    "not_estimable": [r["category"] for r in out if r["status"] == "NOT_ESTIMABLE_NO_VALIDATED_ORACLE"],
    "table9_observed_outcome_rows": table9,
    "class_rows": out,
    "interpretation": "Do not fill unvalidated categories with zero or pool controlled canary probes with the original 625-trial ECR. To claim a 12-class ECR, define and validate class-specific sinks/oracles and rerun a common protocol."
}
(BENCH / "ecr_all_12_class_coverage_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
print(json.dumps(summary, indent=2))
