package com.example.plgenn.utils;

public class SemanticChecker {

    public boolean makesSense(String payload, String context) {
        if (payload == null || context == null) {
            return false;
        }

        String contextLower = context.toLowerCase();
        String payloadLower = payload.toLowerCase();

        // Check for context-payload alignment
        if (contextLower.contains("sql")) {
            return makesSenseForSQL(payloadLower, contextLower);
        } else if (contextLower.contains("xss")) {
            return makesSenseForXSS(payloadLower, contextLower);
        } else if (contextLower.contains("path") || contextLower.contains("directory")) {
            return makesSenseForPathTraversal(payloadLower);
        } else if (contextLower.contains("command") || contextLower.contains("cmd")) {
            return makesSenseForCommandInjection(payloadLower);
        }

        // Default: Accept if it has any security pattern
        return hasAnySecurityPattern(payloadLower);
    }

    private boolean makesSenseForSQL(String payload, String context) {
        // SQL payloads should have SQL patterns
        boolean hasSQLPattern = payload.contains("'") ||
                payload.contains("select") ||
                payload.contains("union") ||
                payload.contains("or ") ||
                payload.contains("and ") ||
                payload.contains("--") ||
                payload.contains("#");

        if (!hasSQLPattern) {
            return false;
        }

        // Context-specific checks
        if (context.contains("login") || context.contains("admin")) {
            return payload.contains("admin") ||
                    payload.contains("user") ||
                    payload.contains("password") ||
                    payload.contains("login");
        }

        if (context.contains("search")) {
            return payload.contains("search") ||
                    payload.contains("query") ||
                    payload.contains("q=");
        }

        return true;
    }

    private boolean makesSenseForXSS(String payload, String context) {
        // XSS payloads should have XSS patterns
        boolean hasXSSPattern = payload.contains("<script") ||
                payload.contains("<img") ||
                payload.contains("<svg") ||
                payload.contains("onerror") ||
                payload.contains("onload") ||
                payload.contains("alert(") ||
                payload.contains("document.");

        if (!hasXSSPattern) {
            return false;
        }

        // Check for mixed patterns (SQL+XSS = likely nonsense)
        if (hasSQLPattern(payload) && hasXSSPattern) {
            return false; // Mixed attack types usually don't make sense
        }

        return true;
    }

    private boolean makesSenseForPathTraversal(String payload) {
        return payload.contains("../") ||
                payload.contains("..\\") ||
                payload.contains("%2e%2e") ||
                payload.contains("etc/passwd") ||
                payload.contains("windows\\win.ini");
    }

    private boolean makesSenseForCommandInjection(String payload) {
        return payload.contains(";") ||
                payload.contains("|") ||
                payload.contains("&&") ||
                payload.contains("`") ||
                payload.contains("$(") ||
                payload.contains("ls") ||
                payload.contains("cat") ||
                payload.contains("whoami");
    }

    private boolean hasSQLPattern(String payload) {
        return payload.contains("select") ||
                payload.contains("union") ||
                payload.contains("' or ") ||
                payload.contains("' and ");
    }

    private boolean hasAnySecurityPattern(String payload) {
        return makesSenseForSQL(payload, "") ||
                makesSenseForXSS(payload, "") ||
                makesSenseForPathTraversal(payload) ||
                makesSenseForCommandInjection(payload);
    }
}