# PLGenN research artifact

This repository contains the Android source, trained model, training inputs, and evaluation records for **PLGenN: Classification Is Not Confirmation**. The generator proposes payloads for twelve vulnerability categories. A neural model labels candidate payloads by structural pattern, vulnerability category, and obfuscation profile. Behavioral confirmation is measured separately by sending candidates to local benchmark applications and checking class-specific response signals.

The artifact is organized so that model classification, payload generation, and runtime confirmation can be inspected independently. It does **not** include the vulnerable benchmark applications or an APK.

## Contents

| Path | Contents |
| --- | --- |
| [`android_app/`](android_app/) | Android Studio project, generator implementation, 67 category-labelled seed entries, and deployed TensorFlow Lite model and label files. |
| [`model_training/`](model_training/) | Training script, primary and supplemental data, source manifest, final model files, held-out predictions, evaluation summaries, and epoch logs. |
| [`evaluation/primary_density_run/`](evaluation/primary_density_run/) | Attempt-level density/mutation log, seed calibration, accepted payloads, benchmark observations, calculations, and analysis scripts. |
| [`evaluation/paired_analysis/`](evaluation/paired_analysis/) | Separate paired classification and runtime study, with generated candidates, predictions, benchmark results, and summaries. |
| [`evaluation/component_comparison/`](evaluation/component_comparison/) | Matched-randomness component runs (rule only, mutation only, rule plus mutation without filtering, full hybrid) and the recalculated ablation table. |
| [`evaluation/external_tool_comparison/outputs/`](evaluation/external_tool_comparison/outputs/) | External tool scan summaries and shared-oracle replay records. |

The twelve category labels are SQL, XSS, IDOR, CMD, PATH, SSRF, LFI, OPEN_REDIRECT, XXE, GRAPHQL, API_ABUSE, and RFI. The TensorFlow Lite output mapping is in [`model_training/candidate_v5_http_params_weight05_family_split_20261010/01_model/tflite_output_mapping.json`](model_training/candidate_v5_http_params_weight05_family_split_20261010/01_model/tflite_output_mapping.json). The Android asset [`plgenn_ltig_model.tflite`](android_app/app/src/main/assets/plgenn_ltig_model.tflite) is the deployed copy of that final model.

## Inspect the reported results

| Measurement | Result | Primary record |
| --- | ---: | --- |
| Held-out category macro F1 | 0.8645 on 14,203 rows | [`model6_summary.json`](model_training/candidate_v5_http_params_weight05_family_split_20261010/02_evaluation/model6_summary.json) and [`test_predictions.csv`](model_training/candidate_v5_http_params_weight05_family_split_20261010/02_evaluation/test_predictions.csv) |
| Generation yield (PSR) | 341 / 2,160 = 15.79% | [`density_mutation_events.csv`](evaluation/primary_density_run/01_App_Logs/density_mutation_events.csv) and [`generation_metrics_summary.json`](evaluation/primary_density_run/04_Calculations/generation_metrics_summary.json) |
| Invalid mutation rate (IMR) | 31 / 667 = 4.65% | Same attempt log and summary |
| Supported-oracle confirmation (ECR) | 274 / 625 = 43.84% | [`density_benchmark_results.csv`](evaluation/primary_density_run/05_Benchmark_Results/density_benchmark_results.csv) and [`density_ecr_summary.json`](evaluation/primary_density_run/05_Benchmark_Results/density_ecr_summary.json) |

PSR counts **accepted output entries deduplicated within each category/profile call**, divided by all generation attempts. It is not the per-attempt predicate pass rate; that separate count is 2,090 / 2,160. IMR counts structurally rejected adaptive-mutation attempts divided by all adaptive-mutation attempts. ECR uses only the 625 trials with a supported behavioral oracle. These trials cover six vulnerability classes; the remaining classes have coverage or oracle limitations documented in [`ecr_all_12_class_coverage_audited.csv`](evaluation/primary_density_run/05_Benchmark_Results/ecr_all_12_class_coverage_audited.csv). A failed confirmation is not proof that a target is secure.

The [`paired_analysis`](evaluation/paired_analysis/) and [`component_comparison`](evaluation/component_comparison/) directories are **different experiments** with their own denominators. In particular, the paired analysis reports 926 confirmed among 1,701 oracle-supported trials. Do not combine that rate with the 625-trial primary density run.

## Build the Android application

1. Install Android Studio with Android SDK 36 and JDK 17.
2. Open [`android_app/`](android_app/) as the Android Studio project and let Gradle resolve dependencies.
3. Run the `app` configuration on an emulator or Android device (minimum API 24). The repository includes the TensorFlow Lite model under `app/src/main/assets`; no model download is needed.

On a configured command line, `cd android_app` followed by `./gradlew assembleDebug` (or `gradlew.bat assembleDebug` on Windows) builds a debug APK. `local.properties`, build outputs, and IDE state are deliberately omitted.

The Android interface offers Basic, Advanced, and Evasion profiles. Each category/profile call makes up to 60 attempts. The hybrid generator selects a direct seed on approximately 70% of attempts and adaptive mutation on approximately 30%; for mutation, the normalized seed repetition score selects one, two, or three operations. The calibrated cutoffs and their selection rule are recorded in [`seed_density_calibration.csv`](evaluation/primary_density_run/01_App_Logs/seed_density_calibration.csv) and [`generation_metrics_summary.json`](evaluation/primary_density_run/04_Calculations/generation_metrics_summary.json). The actual decisions are recorded per attempt in the mutation event CSV.

## Inspect or rerun model training

The final training entry point is [`model_training/train_model6_v5_http_params_weight05.py`](model_training/train_model6_v5_http_params_weight05.py). It resolves its input and output directories relative to its own location. It requires Python with TensorFlow, NumPy, pandas, scikit-learn, matplotlib, and seaborn. From `model_training/`, run `python train_model6_v5_http_params_weight05.py` in an environment with those packages. Training is computationally expensive and will write into the supplied final run directory; copy the directory first if the archived outputs must remain untouched.

The training summary records 89,256 primary rows, 12,543 supplemental source records, 71,128 unique category/payload records after merging and deduplication, and a family-grouped train/development/test split. A heuristic template-family split reduces exact and near-template leakage; row-level source provenance is incomplete, so this is **not** a source-aware split. The source and licensing notes supplied with the supplemental data are in [`model6_v4_sources_and_provenance.json`](model_training/00_data/model6_v4_sources_and_provenance.json). These classification figures do not measure generator quality or exploitation.

## Runtime evaluation requirements

The runtime scripts were written for local installations of DVWA, XVWA, bWAPP, and OWASP Juice Shop. These applications, their setup state, account credentials, and any container images are not distributed here. Several evaluation scripts still contain **placeholder paths** (`/path/to/Research_project`) in place of the original machine's absolute paths. Configure these paths, target URLs, and local benchmark state before rerunning. Archived CSV and JSON records can be inspected without rerunning a benchmark.

The evaluation applies behavioral oracles only where a class/target pair has a defensible signal. Local SSRF, RFI, and XXE probes are included separately, but they are not silently added to the 625-trial pooled ECR. The external tool comparison has a separate scope and should be read from its recorded scan/replay files rather than treated as a matched twelve-class exploit test.

Use these scripts only against systems you own or are authorized to test.

## Data provenance and limits

The primary corpus predates this packaged run and lacks row-level source attribution. The supplemental manifest records inspected sources and imported subsets, including [PayloadsAllTheThings](https://github.com/swisskyrepo/PayloadsAllTheThings) and [HttpParamsDataset](https://github.com/Morzeux/HttpParamsDataset). Its notes distinguish inspected repositories from records actually imported. Payload labels and neural predictions are candidate descriptions, not proof of a vulnerability; runtime evidence is reported separately.

This repository omits manuscript drafts, screenshots, personal local paths, Android build caches, and the benchmark applications. The existing CSV and JSON files are the audit trail for the reported measurements.
