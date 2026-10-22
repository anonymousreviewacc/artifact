import re,json,csv,pathlib,collections,statistics
BASE=pathlib.Path(r'''/path/to/Research_project\The_6th_model_test\08_Density_Mutation_Validation''')
SOURCE=pathlib.Path(r'''/path/to/Research_project\app-network-plgen\app\src\main\java\com\example\plgenn\utils\GNNGenerator.java''')
text=SOURCE.read_text(encoding='utf-8')
seeds=[]
for cat,args in re.findall(r'case "([^"]+)":\s*Collections\.addAll\(list,(.*?)\);\s*break;',text,re.S):
    for raw in re.findall(r'"((?:\\.|[^"\\])*)"',args):
        seed=json.loads('"'+raw+'"')
        tokens=[t.lower() for t in re.findall(r'(?i)[a-z_][a-z0-9_]*|%[0-9a-f]{2}|(?:==|!=|<=|>=|&&|\|\||\.\.|//|/\*|\*/|--|#)|[^\s]',seed)]
        n=len(tokens); freq=collections.Counter(tokens)
        score=(sum(v*v for v in freq.values())-n)/(n*(n-1)) if n>1 else 0.0
        seeds.append({'category':cat,'seed':seed,'token_count':n,'distinct_tokens':len(freq),'D_norm':score})
assert len(seeds)==67, f'Expected 67 class-labelled seed entries, got {len(seeds)}'
scores=sorted(x['D_norm'] for x in seeds); distinct=sorted(set(scores)); n=len(scores)
def boundary(target, lower=None):
    eligible=[v for v in distinct if lower is None or v>lower]
    return min(eligible,key=lambda v:(abs(sum(s<v for s in scores)-target),v))
theta1=boundary(n/3); theta2=boundary(2*n/3,theta1)
java=SOURCE.read_text(encoding='utf-8')
assert f'THETA_1 = {theta1}' in java and f'THETA_2 = {theta2}' in java, 'Java constants do not match seed-derived cutoffs'
for x in seeds: x['intensity']='LOW' if x['D_norm']<theta1 else ('MODERATE' if x['D_norm']<theta2 else 'HIGH')
with (BASE/'01_App_Logs'/'seed_density_calibration.csv').open('w',newline='',encoding='utf-8-sig') as f:
    w=csv.DictWriter(f,fieldnames=list(seeds[0]));w.writeheader();w.writerows(seeds)
events=list(csv.DictReader((BASE/'01_App_Logs'/'density_mutation_events.csv').open(encoding='utf-8-sig',newline='')))
assert len(events)==2160 and all('operation_sequence' in r for r in events)
assert len({r['run_id'] for r in events})==36
byrun=collections.defaultdict(list)
for row in events:
    byrun[row['run_id']].append(row)
assert set(map(len,byrun.values()))=={60}
lookup={r['seed']:r['D_norm'] for r in seeds}
for r in events:
    assert r['seed'] in lookup and abs(float(r['density'])-lookup[r['seed']])<1e-12
    expected='LOW' if float(r['density'])<theta1 else ('MODERATE' if float(r['density'])<theta2 else 'HIGH')
    assert r['intensity']==expected
    assert r['theta1']==str(theta1) and r['theta2']==str(theta2)
counts=list(csv.DictReader((BASE/'02_App_Payloads'/'generation_counts.csv').open(encoding='utf-8-sig',newline='')))
accepted={(r['category'],r['mode']):int(r['count']) for r in counts}
strata=collections.defaultdict(list)
for r in events: strata[(r['category'],r['profile'])].append(r)
metrics=[]
for (cat,profile),rr in sorted(strata.items()):
    mut=[r for r in rr if r['path']=='ADAPTIVE_MUTATION']
    invalid=sum(r['structurally_valid'].lower()=='false' for r in mut)
    metrics.append({'category':cat,'profile':profile,'attempts':len(rr),'distinct_valid_outputs':accepted[(cat,profile)],'PSR':accepted[(cat,profile)]/len(rr),'mutation_attempts':len(mut),'invalid_mutations':invalid,'IMR':invalid/len(mut) if mut else 0,'direct_seed_attempts':len(rr)-len(mut),'low_density_mutations':sum(r['intensity']=='LOW' for r in mut),'moderate_density_mutations':sum(r['intensity']=='MODERATE' for r in mut),'high_density_mutations':sum(r['intensity']=='HIGH' for r in mut)})
with (BASE/'04_Calculations'/'psr_imr_by_class_profile.csv').open('w',newline='',encoding='utf-8-sig') as f:
    w=csv.DictWriter(f,fieldnames=list(metrics[0]));w.writeheader();w.writerows(metrics)
N=len(events); mutation=[r for r in events if r['path']=='ADAPTIVE_MUTATION']; invalid_mut=sum(r['structurally_valid'].lower()=='false' for r in mutation); nout=sum(accepted.values())
seed_groups=collections.Counter(x['intensity'] for x in seeds); mutation_groups=collections.Counter(x['intensity'] for x in mutation)
summary={'seed_entries':67,'unique_seed_strings':len(lookup),'categories':len(set(x['category'] for x in seeds)),'profiles':3,'theta1':theta1,'theta2':theta2,'threshold_selection':'Among observed scores from the 67 class-labelled in-app seed entries, choose cutoffs minimizing absolute distance from N/3 and 2N/3 cumulative counts; ties choose smaller scores. Frozen before benchmark execution.','seed_group_counts':dict(seed_groups),'run_count':len(byrun),'attempts':N,'direct_seed_attempts':N-len(mutation),'direct_seed_fraction':(N-len(mutation))/N,'mutation_attempts':len(mutation),'mutation_fraction':len(mutation)/N,'mutation_tier_counts':dict(mutation_groups),'distinct_valid_outputs':nout,'PSR':nout/N,'invalid_mutations':invalid_mut,'IMR':invalid_mut/len(mutation),'all_path_structural_rejects':sum(x['structurally_valid'].lower()=='false' for x in events),'validation':'36 runs x 60 attempts; score, cutoffs, branch tier, and operation_sequence cross-checked against the exact seed-derived scores.','interpretation_limit':'PSR is distinct outputs accepted by the current class-structure predicates divided by attempts. These predicates are not proof of parser acceptance or exploitability. IMR is structurally rejected adaptive-mutation attempts divided by adaptive-mutation attempts.'}
(BASE/'04_Calculations'/'generation_metrics_summary.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
print(json.dumps(summary,indent=2))
