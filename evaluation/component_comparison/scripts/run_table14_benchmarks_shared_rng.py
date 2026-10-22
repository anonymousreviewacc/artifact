import asyncio,datetime,importlib.util,pathlib
SOURCE=pathlib.Path(r"/path/to/Research_project\The_6th_model_test\08_Density_Mutation_Validation\run_density_benchmarks.py");INPUTS=pathlib.Path(r"/path/to/Research_project\Baseline_app_comparision\03_Benchmark_Results\inputs_shared_rng_final");OUT=pathlib.Path(r"/path/to/Research_project\Baseline_app_comparision\03_Benchmark_Results\shared_rng_final");SHOTS=pathlib.Path(r"/path/to/Research_project\Baseline_app_comparision\05_Screenshots\shared_rng_final")
spec=importlib.util.spec_from_file_location("density_runner",SOURCE);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
for variant in ["rule_only","mutation_only_fixed2","rule_mutation_density_no_filter","full_hybrid_density"]:
 run_dir=OUT/variant;run_dir.mkdir(parents=True,exist_ok=True)
 module.INPUT=INPUTS/(variant+"_input.csv");module.OUT=run_dir/(variant+"_benchmark_results.csv");module.META=run_dir/(variant+"_benchmark_metadata.json");module.SHOTROOT=SHOTS/variant
 module.RUN_ID="table14_shared_rng_"+variant+"_"+datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
 print("START",variant,"rows",sum(1 for _ in module.INPUT.open(encoding="utf-8-sig"))-1,flush=True)
 asyncio.run(module.main());print("DONE",variant,flush=True)
