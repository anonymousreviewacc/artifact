import csv, json, shutil
from pathlib import Path
from collections import Counter, defaultdict
root=Path(r'/path/to/Research_project\The_6th_model_test')
res=root/'04_Benchmark_Results'
raw=res/'model6_benchmark_results_raw.csv'
corrected=res/'model6_benchmark_results.csv'
if not raw.exists(): shutil.copy2(corrected, raw)
with raw.open(newline='',encoding='utf-8-sig') as f: rows=list(csv.DictReader(f))
fields=list(rows[0])
for r in rows:
    if r['Site']=='bWAPP' and r['Category']=='SQL Injection':
        r['Outcome']='BENCHMARK_ENVIRONMENT_ERROR'
        r['Confirmed']='false'
        r['EvidenceCode']='php_mysql_connect_undefined'
        r['Error']='bWAPP SQL endpoint crashes: undefined function mysql_connect() in connect.php; payload was not processed.'
with corrected.open('w',newline='',encoding='utf-8-sig') as f:
    w=csv.DictWriter(f,fieldnames=fields); w.writeheader(); w.writerows(rows)
# Oracle-supported test set. Every target/payload is individually counted; no unsupported class-site pairs are treated as negatives.
supported={('SQL Injection','DVWA'),('SQL Injection','XVWA'),('XSS','DVWA'),('XSS','XVWA'),('XSS','bWAPP'),('XSS','OWASP_Juice_Shop'),('Command Injection','DVWA'),('Command Injection','XVWA'),('Command Injection','bWAPP'),('Open Redirect','XVWA')}
metrics=[]
for key in sorted(supported):
    subset=[r for r in rows if (r['Category'],r['Site'])==key]
    modes=defaultdict(list)
    for r in subset: modes[r['Mode']].append(r)
    for mode, rr in sorted(modes.items()):
        n=len(rr); pos=sum(x['Confirmed'].lower()=='true' for x in rr)
        metrics.append({'site':key[1],'category':key[0],'mode':mode,'submitted':n,'confirmed':pos,'not_confirmed':n-pos,'confirmation_rate_pct':round(100*pos/n,2) if n else None,'oracle':'SQL result-count differential' if key[0]=='SQL Injection' else 'browser JavaScript dialog' if key[0]=='XSS' else 'command output signal' if key[0]=='Command Injection' else 'HTTP 302 Location points to external host; redirect not followed'})
# totals by class/mode pooled across supported benchmarks, denominator includes only tested routes with valid configured oracle
by=defaultdict(list)
for r in rows:
    if (r['Category'],r['Site']) in supported: by[(r['Category'],r['Mode'])].append(r)
classmode=[]
for (cat,mode),rr in sorted(by.items()):
    n=len(rr); pos=sum(x['Confirmed'].lower()=='true' for x in rr)
    classmode.append({'category':cat,'mode':mode,'payload_site_trials':n,'confirmed':pos,'not_confirmed':n-pos,'confirmation_rate_pct':round(pos*100/n,2)})
valid=[r for r in rows if (r['Category'],r['Site']) in supported]
pos=sum(r['Confirmed'].lower()=='true' for r in valid)
# paired model diagnostic among supported rows, class label accuracy against intended generation category, not exploit detection metrics
pred_path=root/'02_Generated_Payloads'/'model6_generated_predictions.csv'
with pred_path.open(newline='',encoding='utf-8-sig') as f: preds=list(csv.DictReader(f))
pred={(r['category'],r['mode'],str(r['index'])):r for r in preds}
paired=[]
for r in valid:
    p=pred.get((r['Category'],r['Mode'],r['Index']))
    if p:
        rpred=p['predicted_category']
        intended={'SQL Injection':'SQL','Cross-Site Scripting (XSS)':'XSS'}
        # map actual labels by class names seen in data
        category_alias={'SQL Injection':'SQL','XSS':'XSS','Command Injection':'CMD','Open Redirect':'OPEN_REDIRECT'}
        target=category_alias.get(r['Category'],r['Category'])
        paired.append({'site':r['Site'],'category':r['Category'],'mode':r['Mode'],'index':r['Index'],'predicted_category':rpred,'intended_category':target,'classification_correct':str(rpred)==target,'runtime_confirmed':r['Confirmed'].lower()=='true','evidence':r['EvidenceCode']})
# Results summary
with (res/'benchmark_site_mode_confirmation.csv').open('w',newline='',encoding='utf-8-sig') as f:
    w=csv.DictWriter(f,fieldnames=list(metrics[0]));w.writeheader();w.writerows(metrics)
with (res/'benchmark_category_mode_confirmation.csv').open('w',newline='',encoding='utf-8-sig') as f:
    w=csv.DictWriter(f,fieldnames=list(classmode[0]));w.writeheader();w.writerows(classmode)
with (res/'model_prediction_runtime_pairs.csv').open('w',newline='',encoding='utf-8-sig') as f:
    w=csv.DictWriter(f,fieldnames=list(paired[0]));w.writeheader();w.writerows(paired)
# Result counts by outcome after environment correction
counts=Counter((r['Category'],r['Outcome'],r['Confirmed']) for r in rows)
meta=json.loads((res/'benchmark_run_metadata.json').read_text(encoding='utf-8'))
meta['result_csv']=str(corrected)
meta['raw_result_csv']=str(raw)
meta['correction_note']='The raw CSV is preserved unchanged. The corrected CSV reclassifies bWAPP SQL rows as benchmark environment errors because the endpoint crashes on undefined mysql_connect().'
meta['oracle_supported_pooled_exploratory_rate']={'confirmed':pos,'eligible_site_payload_trials':len(valid),'percent':round(100*pos/len(valid),2),'warning':'Exploratory pooled rate across only supported route/oracle combinations; not directly comparable to manuscript ECR due to changed payload set, endpoint coverage, authentication, oracle, and run protocol.'}
meta['unsupported_pairs_not_scored_as_negative']=True
meta['cautions']=['SSRF and RFI were skipped.','IDOR, GraphQL, API Abuse, XXE, Path Traversal, and LFI did not have sufficient validated oracles; no-confirmation is not a negative result.','Juice Shop XSS was browser-side fragment testing; 6 third-party asset requests were blocked.','XVWA setup/login timed out.','bWAPP SQL was not processed due to missing mysql_connect().']
(res/'benchmark_run_metadata_corrected.json').write_text(json.dumps(meta,indent=2),encoding='utf-8')
summary={'total_rows':len(rows),'environment_error_rows':sum(r['Outcome']=='BENCHMARK_ENVIRONMENT_ERROR' for r in rows),'oracle_supported_rows':len(valid),'oracle_confirmed_rows':pos,'exploratory_pooled_confirmation_pct':round(pos*100/len(valid),2),'counts_by_category_outcome':{f'{k[0]}|{k[1]}|{k[2]}':v for k,v in counts.items()},'paired_payload_site_trials':len(paired),'paired_model_label_correct':sum(x['classification_correct'] for x in paired),'paired_runtime_confirmed':sum(x['runtime_confirmed'] for x in paired)}
(res/'benchmark_summary_corrected.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
print(json.dumps(summary,indent=2))
