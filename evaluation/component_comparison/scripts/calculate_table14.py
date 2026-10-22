import csv, pathlib, collections, re, json
BASE=pathlib.Path(r"/path/to/Research_project\Baseline_app_comparision")
GEN=BASE/"02_Generation_Results"/"android_run"/"final_rng_matched"/"baseline_ablation_20261019T024137.729884Z"/"baseline_payloads.csv"
ATT=BASE/"02_Generation_Results"/"android_run"/"final_rng_matched"/"baseline_ablation_20261019T024137.729884Z"/"baseline_attempts.csv"
PRED=BASE/"02_Generation_Results"/"android_run"/"final_rng_matched"/"baseline_ablation_20261019T024137.729884Z"/"baseline_predictions.csv"
HELD=pathlib.Path(r"/path/to/Research_project\Model_train\6th_model_train\candidate_v5_http_params_weight05_family_split_20261010\02_evaluation\test_predictions.csv")
OUT=BASE/"04_Calculations";OUT.mkdir(parents=True,exist_ok=True)
def read(path):
    with path.open(encoding="utf-8-sig",newline="") as f:return list(csv.DictReader(f))
attempts=read(ATT);outputs=read(GEN);predictions=read(PRED)
variants=["rule_only","mutation_only_fixed2","rule_mutation_density_no_filter","full_hybrid_density"]
labels=["SQL","XSS","IDOR","CMD","PATH","SSRF","LFI","OPEN_REDIRECT","XXE","GRAPHQL","API_ABUSE","RFI"]
catcode={"SQL Injection":"SQL","XSS":"XSS","IDOR":"IDOR","Command Injection":"CMD","Path Traversal":"PATH","SSRF":"SSRF","Local File Inclusion":"LFI","Remote File Inclusion":"RFI","XXE":"XXE","GraphQL Injection":"GRAPHQL","Open Redirect":"OPEN_REDIRECT","API Abuse":"API_ABUSE"}
token_re=re.compile(r"(?i)[a-z_][a-z0-9_]*|%[0-9a-f]{2}|(?:==|!=|<=|>=|&&|\|\||\.\.|//|/\*|\*/|--|#)|[^\s]")
def bigrams(payload):
    toks=[x.lower() for x in token_re.findall(payload)]
    return set(zip(toks,toks[1:]))
def diversity(rows):
    freq=collections.Counter(r["payload"] for r in rows);sets=[(bigrams(p),n) for p,n in freq.items()];n=len(rows)
    if n<2:return 0.0
    sim_sum=0.0
    for i,(a,na) in enumerate(sets):
        for b,nb in sets[i+1:]:
            union=a|b;sim=(len(a&b)/len(union)) if union else 1.0;sim_sum+=na*nb*sim
        sim_sum+=na*(na-1)/2
    return 1-sim_sum/(n*(n-1)/2)
def macro_f1(rows,true_key,pred_key):
    vals=[]
    for label in labels:
        tp=sum(r[true_key]==label and r[pred_key]==label for r in rows)
        fp=sum(r[true_key]!=label and r[pred_key]==label for r in rows)
        fn=sum(r[true_key]==label and r[pred_key]!=label for r in rows)
        den=2*tp+fp+fn;vals.append(2*tp/den if den else 0.0)
    return sum(vals)/len(labels),vals
eligible_categories={"SQL Injection","XSS","Command Injection","Path Traversal","Local File Inclusion","Open Redirect"}
summary=[];ecr_detail=[];f1_detail=[]
for v in variants:
    a=[r for r in attempts if r["variant"]==v];o=[r for r in outputs if r["variant"]==v];pr=[r for r in predictions if r["variant"]==v]
    calls=collections.defaultdict(set)
    for r in a:
        if r["structurally_valid"].lower()=="true":calls[(r["category"],r["profile"])].add(r["payload"])
    valid_unique=sum(map(len,calls.values()));psr=valid_unique/len(a)
    mut=[r for r in a if r["path"]=="ADAPTIVE_MUTATION"];invalid=sum(r["structurally_valid"].lower()!="true" for r in mut);imr=invalid/len(mut) if mut else None
    br=read(BASE/"03_Benchmark_Results"/"shared_rng_final"/v/(v+"_benchmark_results.csv"))
    elig=[r for r in br if r["Category"] in eligible_categories and not(r["Category"]=="SQL Injection" and r["Site"]=="bWAPP")]
    confirmed=sum(r["Confirmed"].lower()=="true" for r in elig);ecr=confirmed/len(elig)
    for (site,cat),group in sorted(collections.defaultdict(list,{}).items()):pass
    counts=collections.Counter((r["Site"],r["Category"],r["Confirmed"].lower()) for r in elig)
    for (site,cat,conf),n in sorted(counts.items()):ecr_detail.append({"variant":v,"site":site,"category":cat,"confirmed":conf,"count":n})
    coded=[dict(r,true_code=catcode[r["category"]]) for r in pr];mf,fvals=macro_f1(coded,"true_code","predicted_category")
    summary.append({"Configuration":v,"Attempts":len(a),"Retained_candidate_rows":len(o),"Valid_unique_per_call":valid_unique,"PSR":psr,"Mutation_attempts":len(mut),"Invalid_mutation_attempts":invalid,"IMR":imr,"Eligible_ECR_trials":len(elig),"Confirmed_trials":confirmed,"ECR":ecr,"Generated_output_macro_F1":mf,"Prediction_rows":len(pr),"Token_bigram_diversity":diversity(o)})
    f1_detail.append({"configuration":v,"prediction_rows":len(pr),"macro_f1":mf,**{label:fvals[i] for i,label in enumerate(labels)}})
held=read(HELD);heldf,heldvals=macro_f1(held,"true_category","predicted_category")
summary.append({"Configuration":"classifier_only","Attempts":"N/A","Retained_candidate_rows":"N/A","Valid_unique_per_call":"N/A","PSR":"N/A","Mutation_attempts":"N/A","Invalid_mutation_attempts":"N/A","IMR":"N/A","Eligible_ECR_trials":"N/A","Confirmed_trials":"N/A","ECR":"N/A","Generated_output_macro_F1":heldf,"Prediction_rows":len(held),"Token_bigram_diversity":"N/A"})
f1_detail.append({"configuration":"classifier_only_family_grouped_holdout","prediction_rows":len(held),"macro_f1":heldf,**{label:heldvals[i] for i,label in enumerate(labels)}})
order={"rule_only":0,"mutation_only_fixed2":1,"rule_mutation_density_no_filter":2,"classifier_only":3,"full_hybrid_density":4};summary.sort(key=lambda x:order[x["Configuration"]])
with (OUT/"Table14_Recalculated_Results.csv").open("w",encoding="utf-8-sig",newline="") as f:
 w=csv.DictWriter(f,fieldnames=list(summary[0]));w.writeheader();w.writerows(summary)
with (OUT/"Table14_ECR_By_Class_and_Target.csv").open("w",encoding="utf-8-sig",newline="") as f:
 w=csv.DictWriter(f,fieldnames=["variant","site","category","confirmed","count"]);w.writeheader();w.writerows(ecr_detail)
with (OUT/"Table14_Generated_Prediction_Metrics.csv").open("w",encoding="utf-8-sig",newline="") as f:
 w=csv.DictWriter(f,fieldnames=list(f1_detail[0]));w.writeheader();w.writerows(f1_detail)
(OUT/"Table14_Summary.json").write_text(json.dumps({"classifier_only_heldout_macro_f1":heldf,"classifier_only_heldout_n":len(held),"ecr_scope":"SQL Injection at DVWA and XVWA; XSS at DVWA, XVWA, bWAPP, and OWASP Juice Shop; Command Injection at DVWA, XVWA, and bWAPP; Path Traversal and LFI at DVWA and XVWA; Open Redirect at XVWA and OWASP Juice Shop. bWAPP SQL excluded because its route yielded no usable oracle. SSRF/RFI skipped for side-effect safety; IDOR, XXE, GraphQL, and API Abuse excluded from ECR because no validated oracle was available."},indent=2),encoding="utf-8")
for row in summary:print(row)
print("classifier holdout",len(held),heldf)

