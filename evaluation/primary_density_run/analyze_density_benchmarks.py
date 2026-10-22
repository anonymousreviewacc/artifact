import csv,json,pathlib,collections
BASE=pathlib.Path(r'''/path/to/Research_project\The_6th_model_test\08_Density_Mutation_Validation'''); OUT=BASE/'05_Benchmark_Results'
rows=list(csv.DictReader((OUT/'density_benchmark_results.csv').open(encoding='utf-8-sig',newline='')))
assert len(rows)==825
# Only pairs with a direct, class-specific behavioural oracle are eligible for ECR.
SUPPORTED={('SQL Injection','DVWA'),('SQL Injection','XVWA'),('XSS','DVWA'),('XSS','XVWA'),('XSS','bWAPP'),('XSS','OWASP_Juice_Shop'),('Command Injection','DVWA'),('Command Injection','XVWA'),('Command Injection','bWAPP'),('Path Traversal','DVWA'),('Path Traversal','XVWA'),('Local File Inclusion','DVWA'),('Local File Inclusion','XVWA'),('Open Redirect','XVWA'),('Open Redirect','OWASP_Juice_Shop')}
eligible=[r for r in rows if (r['Category'],r['Site']) in SUPPORTED]
profiles=['Basic','Advanced','Evasion']; classes=['SQL Injection','XSS','Command Injection','Path Traversal','Local File Inclusion','Open Redirect']
class_profile=[]
for cat in classes:
 for mode in profiles:
  sub=[r for r in eligible if r['Category']==cat and r['Mode']==mode]
  n=len(sub); yes=sum(r['Confirmed'].lower()=='true' for r in sub)
  class_profile.append({'category':cat,'profile':mode,'oracle_supported_site_payload_trials':n,'confirmed':yes,'not_confirmed':n-yes,'ECR':yes/n if n else None,'ECR_percent':100*yes/n if n else None})
with (OUT/'ecr_by_class_profile.csv').open('w',newline='',encoding='utf-8-sig') as f:
 w=csv.DictWriter(f,fieldnames=list(class_profile[0]));w.writeheader();w.writerows(class_profile)
site_detail=[]
for cat,site in sorted(SUPPORTED):
 for mode in profiles:
  sub=[r for r in eligible if r['Category']==cat and r['Site']==site and r['Mode']==mode]
  n=len(sub); yes=sum(r['Confirmed'].lower()=='true' for r in sub)
  site_detail.append({'category':cat,'site':site,'profile':mode,'tested':n,'confirmed':yes,'ECR':yes/n if n else None})
with (OUT/'ecr_by_site_class_profile.csv').open('w',newline='',encoding='utf-8-sig') as f:
 w=csv.DictWriter(f,fieldnames=list(site_detail[0]));w.writeheader();w.writerows(site_detail)
profile=[]
for mode in profiles:
 sub=[r for r in eligible if r['Mode']==mode]; n=len(sub); yes=sum(r['Confirmed'].lower()=='true' for r in sub)
 profile.append({'profile':mode,'supported_trials':n,'confirmed':yes,'ECR':yes/n if n else None,'ECR_percent':100*yes/n if n else None})
with (OUT/'ecr_by_profile.csv').open('w',newline='',encoding='utf-8-sig') as f:
 w=csv.DictWriter(f,fieldnames=list(profile[0]));w.writeheader();w.writerows(profile)
# Table 9's original filtered/error/runtime-invalid taxonomy cannot be reconstructed from the saved metadata alone.
# Preserve only observable groups and label all other unconfirmed results as unresolved.
obs=[]
for mode in profiles:
 sub=[r for r in eligible if r['Mode']==mode]
 n=len(sub); success=sum(r['Confirmed'].lower()=='true' for r in sub)
 status_filtered=sum(r['Status'] in ('401','403') for r in sub if r['Confirmed'].lower()!='true')
 explicit_error=sum(r['Outcome'] in ('SERVER_ERROR','REQUEST_ERROR','SQL_ERROR_SIGNAL_UNCONFIRMED') for r in sub if r['Confirmed'].lower()!='true')
 unresolved=n-success-status_filtered-explicit_error
 obs.append({'profile':mode,'eligible_trials':n,'confirmed':success,'HTTP_401_403_unconfirmed':status_filtered,'explicit_server_request_or_SQL_error':explicit_error,'other_unconfirmed_not_safely_disambiguated':unresolved,'note':'Not equivalent to manuscript Table 9: response bodies/causal filter labels were not persisted, so filtered vs runtime-invalid vs ordinary no-effect cannot be separated.'})
with (OUT/'table9_observed_outcomes_not_equivalent.csv').open('w',newline='',encoding='utf-8-sig') as f:
 w=csv.DictWriter(f,fieldnames=list(obs[0]));w.writeheader();w.writerows(obs)
counts=collections.Counter(r['Outcome'] for r in rows)
observed_pairs=set((r['Category'],r['Site']) for r in rows)
safety_pairs={('SSRF','XVWA'),('Remote File Inclusion','XVWA')}
environment_pairs={('SQL Injection','bWAPP')}
no_oracle_pairs=observed_pairs-SUPPORTED-safety_pairs-environment_pairs
summary={'run_id':json.loads((OUT/'density_benchmark_metadata.json').read_text(encoding='utf-8'))['run_id'],'generated_payload_rows':341,'benchmark_result_rows':len(rows),'supported_oracle_trials':len(eligible),'confirmed_supported_trials':sum(r['Confirmed'].lower()=='true' for r in eligible),'pooled_ECR':sum(r['Confirmed'].lower()=='true' for r in eligible)/len(eligible),'pooled_ECR_percent':100*sum(r['Confirmed'].lower()=='true' for r in eligible)/len(eligible),'confirmed_all_rows_including_unvalidated_oracles':sum(r['Confirmed'].lower()=='true' for r in rows),'outcome_counts':dict(counts),'skipped_ssrf_rfi_rows':sum(r['Outcome']=='SKIPPED_SAFETY_OR_SIDE_EFFECT' for r in rows),'supported_pairs':sorted([list(x) for x in SUPPORTED]),'excluded_pairs_without_validated_oracle':sorted([list(x) for x in no_oracle_pairs]),'safety_skipped_pairs':sorted([list(x) for x in safety_pairs]),'benchmark_environment_error_pairs':sorted([list(x) for x in environment_pairs]),'ECR_definition':'Confirmed payload/site executions divided by tested payload/site trials for the explicitly listed class/site pairs with direct behavioural oracles. Unsupported pairs and SSRF/RFI are excluded, not counted as failures.','Table9_limitation':'The original four-way behavioural outcome decomposition is not recoverable from this run: response bodies and explicit filtering/runtime-invalid labels were not retained. The companion table lists only observable outcome groups and is not a replacement for Table 9.','Screenshots':'Representative per-site/category states in 06_Benchmark_Screenshots; the CSV is the per-payload evidence.'}
(OUT/'density_ecr_summary.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
print(json.dumps(summary,indent=2));print('\nProfile ECR:',profile)
