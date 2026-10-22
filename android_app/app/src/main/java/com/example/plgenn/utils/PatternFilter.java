package com.example.plgenn.utils;

import java.util.Arrays;
import java.util.List;
import java.util.regex.Pattern;

public class PatternFilter {

    private static final List<Pattern> VALID_PATTERNS = Arrays.asList(
            // SQL Injection patterns
            Pattern.compile(".*'\\s+OR\\s+'.*"),
            Pattern.compile(".*UNION\\s+SELECT.*"),
            Pattern.compile(".*'\\s+AND\\s+.*"),
            Pattern.compile(".*;\\s*--.*"),
            Pattern.compile(".*'\\s*#.*"),

            // XSS patterns
            Pattern.compile(".*<script>.*</script>.*"),
            Pattern.compile(".*<img[^>]*onerror=.*"),
            Pattern.compile(".*<svg[^>]*onload=.*"),
            Pattern.compile(".*alert\\(.*\\).*"),
            Pattern.compile(".*document\\.cookie.*"),

            // Path traversal patterns
            Pattern.compile(".*\\.\\./.*"),
            Pattern.compile(".*%2e%2e%2f.*"),

            // Command injection patterns
            Pattern.compile(".*;\\s*(ls|cat|whoami|id).*"),
            Pattern.compile(".*\\|\\s*.*"),
            Pattern.compile(".*&&\\s*.*"),

            // Template injection patterns
            Pattern.compile(".*\\$\\{.*\\}.*"),
            Pattern.compile(".*%7B%7B.*%7D%7D.*")
    );

    public boolean matchesValidPattern(String payload) {
        if (payload == null || payload.trim().isEmpty()) {
            return false;
        }

        for (Pattern pattern : VALID_PATTERNS) {
            if (pattern.matcher(payload).matches()) {
                return true;
            }
        }

        // Also accept basic payloads without complex patterns
        return isBasicPayload(payload);
    }

    private boolean isBasicPayload(String payload) {
        // Accept basic test payloads
        return payload.contains("test") ||
                payload.contains("admin") ||
                payload.contains("user") ||
                payload.contains("password") ||
                payload.contains("search") ||
                payload.contains("query");
    }
}