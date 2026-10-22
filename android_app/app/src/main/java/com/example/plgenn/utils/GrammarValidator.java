package com.example.plgenn.utils;

import java.util.regex.Pattern;

public class GrammarValidator {

    public boolean isValidPayload(String payload) {
        if (payload == null || payload.trim().isEmpty()) {
            return false;
        }

        // Rule 1: Check for balanced quotes in SQL
        if (isSQLPayload(payload)) {
            int singleQuotes = countOccurrences(payload, "'");
            int doubleQuotes = countOccurrences(payload, "\"");

            if (singleQuotes % 2 != 0) {
                return false; // Unbalanced single quotes
            }
            if (doubleQuotes % 2 != 0) {
                return false; // Unbalanced double quotes
            }
        }

        // Rule 2: Check for balanced parentheses
        if (countOccurrences(payload, "(") != countOccurrences(payload, ")")) {
            return false;
        }

        // Rule 3: Check for balanced comments
        if (payload.contains("/*") && !payload.contains("*/")) {
            return false;
        }

        // Rule 4: Check for obvious SQL syntax errors
        if (hasSQLSyntaxErrors(payload)) {
            return false;
        }

        // Rule 5: Check for XSS syntax
        if (isXSSPayload(payload) && !hasValidXSSSyntax(payload)) {
            return false;
        }

        return true;
    }

    private boolean isSQLPayload(String payload) {
        return payload.toUpperCase().contains("SELECT") ||
                payload.toUpperCase().contains("UNION") ||
                payload.toUpperCase().contains("OR ") ||
                payload.contains("'") ||
                payload.contains("--") ||
                payload.contains("#");
    }

    private boolean isXSSPayload(String payload) {
        return payload.contains("<script") ||
                payload.contains("<img") ||
                payload.contains("<svg") ||
                payload.contains("alert(") ||
                payload.contains("onerror=") ||
                payload.contains("onload=");
    }

    private boolean hasSQLSyntaxErrors(String payload) {
        String upper = payload.toUpperCase();

        // SELECT without FROM (basic check)
        if (upper.contains("SELECT") && upper.contains("FROM")) {
            int selectIndex = upper.indexOf("SELECT");
            int fromIndex = upper.indexOf("FROM");
            if (fromIndex < selectIndex) {
                return true; // FROM before SELECT
            }
        }

        // UNION without proper structure
        if (upper.contains("UNION")) {
            String beforeUnion = upper.substring(0, upper.indexOf("UNION"));
            String afterUnion = upper.substring(upper.indexOf("UNION") + 5);
            if (!beforeUnion.contains("SELECT") || !afterUnion.contains("SELECT")) {
                return true;
            }
        }

        return false;
    }

    private boolean hasValidXSSSyntax(String payload) {
        // Check for properly closed tags
        if (payload.contains("<script>") && !payload.contains("</script>")) {
            return false;
        }

        if (payload.contains("<img") && !payload.contains(">")) {
            return false;
        }

        // Check for proper JavaScript syntax
        if (payload.contains("alert(") && !payload.contains(")")) {
            return false;
        }

        return true;
    }

    private int countOccurrences(String str, String find) {
        int count = 0;
        int index = 0;
        while ((index = str.indexOf(find, index)) != -1) {
            count++;
            index += find.length();
        }
        return count;
    }
}