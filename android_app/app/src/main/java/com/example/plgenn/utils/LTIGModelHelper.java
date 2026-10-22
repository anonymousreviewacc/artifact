package com.example.plgenn.utils;

import android.content.Context;
import android.content.res.AssetFileDescriptor;
import android.util.Log;

import org.tensorflow.lite.Interpreter;

import java.io.BufferedReader;
import java.io.FileInputStream;
import java.io.IOException;
import java.io.InputStreamReader;
import java.nio.MappedByteBuffer;
import java.nio.channels.FileChannel;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

/** Android adapter for the selected Model 6 TFLite contract. */
public class LTIGModelHelper {
    private static final String TAG = "LTIGModel6";
    private static final int SEQ_LENGTH = 100;
    private static final int VOCAB_SIZE = 20000;
    private static final String KERAS_FILTERS = "!\"#$%&()*+,-./:;<=>?@[\\]^_`{|}~";

    private final Interpreter tflite;
    private final Map<String, Integer> vocabMap = new HashMap<>();
    private final String[] patterns;
    private final int categoryTensor;
    private final int patternTensor;

    public static class ModelPredictions {
        public final float confidence;
        public final String pattern;

        public ModelPredictions(float confidence, String pattern) {
            this.confidence = confidence;
            this.pattern = pattern;
        }
    }

    public LTIGModelHelper(Context context) throws IOException {
        loadVocab(context);
        patterns = loadLines(context, "pattern_labels.txt");
        tflite = loadModel(context);
        int cat = -1;
        int pat = -1;
        for (int i = 0; i < tflite.getOutputTensorCount(); i++) {
            int[] shape = tflite.getOutputTensor(i).shape();
            if (shape.length == 2 && shape[1] == 12) cat = i;
            if (shape.length == 2 && shape[1] == 36) pat = i;
            Log.i(TAG, "Output " + i + " shape=" + shape[0] + "x" + shape[1]);
        }
        if (cat < 0 || pat < 0 || patterns.length != 36) {
            tflite.close();
            throw new IOException("Model 6 tensor/label contract mismatch: category=" + cat +
                    ", pattern=" + pat + ", pattern labels=" + patterns.length);
        }
        categoryTensor = cat;
        patternTensor = pat;
        Log.i(TAG, "Model 6 loaded; category output=" + cat + ", pattern output=" + pat);
    }

    private static Interpreter loadModel(Context context) throws IOException {
        try (AssetFileDescriptor fd = context.getAssets().openFd("plgenn_ltig_model.tflite");
             FileInputStream fis = new FileInputStream(fd.getFileDescriptor())) {
            MappedByteBuffer buffer = fis.getChannel().map(FileChannel.MapMode.READ_ONLY,
                    fd.getStartOffset(), fd.getDeclaredLength());
            Interpreter.Options options = new Interpreter.Options();
            options.setNumThreads(2);
            return new Interpreter(buffer, options);
        }
    }

    private void loadVocab(Context context) throws IOException {
        try (BufferedReader reader = new BufferedReader(new InputStreamReader(
                context.getAssets().open("vocab.txt"), StandardCharsets.UTF_8))) {
            String line;
            int index = 1; // Keras OOV token occupies index 1; 0 is padding.
            while ((line = reader.readLine()) != null) {
                line = line.trim();
                if (!line.isEmpty()) vocabMap.put(line, index++);
            }
        }
        if (!vocabMap.containsKey("<UNK>")) throw new IOException("Model 6 OOV token missing from vocab");
    }

    // The JSON label asset is a one-string-per-line compact list generated from the
    // model's ordered JSON labels; this avoids a JSON parser dependency here.
    private static String[] loadLines(Context context, String filename) throws IOException {
        List<String> values = new ArrayList<>();
        try (BufferedReader reader = new BufferedReader(new InputStreamReader(
                context.getAssets().open(filename), StandardCharsets.UTF_8))) {
            String line;
            while ((line = reader.readLine()) != null) {
                line = line.replace("\uFEFF", "").trim();
                if (!line.isEmpty()) values.add(line);
            }
        }
        return values.toArray(new String[0]);
    }

    private List<String> tokenizeForKeras(String payload) {
        List<String> tokens = new ArrayList<>();
        if (payload == null) return tokens;
        StringBuilder token = new StringBuilder();
        String lower = payload.toLowerCase(java.util.Locale.ROOT);
        for (int i = 0; i < lower.length(); i++) {
            char c = lower.charAt(i);
            if (KERAS_FILTERS.indexOf(c) >= 0 || Character.isWhitespace(c)) {
                if (token.length() > 0) {
                    tokens.add(token.toString());
                    token.setLength(0);
                }
            } else {
                token.append(c);
            }
        }
        if (token.length() > 0) tokens.add(token.toString());
        return tokens;
    }

    private int[][] textInput(String payload) {
        List<String> tokens = tokenizeForKeras(payload);
        int keepFrom = Math.max(0, tokens.size() - SEQ_LENGTH);
        int retained = tokens.size() - keepFrom;
        int[][] input = new int[1][SEQ_LENGTH]; // pre-padding with zero
        int offset = SEQ_LENGTH - retained;
        for (int i = 0; i < retained; i++) {
            int index = vocabMap.getOrDefault(tokens.get(keepFrom + i), 1);
            input[0][offset + i] = index < VOCAB_SIZE ? index : 1;
        }
        return input;
    }

    // Model 6 training computes LTIG from whitespace-delimited raw payload tokens,
    // then applies the StandardScaler fitted on the training partition.
    private float[][] ltigInput(String payload) {
        String trimmed = payload == null ? "" : payload.trim();
        String[] tokens = trimmed.isEmpty() ? new String[0] : trimmed.split("\\s+");
        if (tokens.length == 0) return new float[1][8];
        Map<String, Integer> nodeCounts = new HashMap<>();
        for (String token : tokens) nodeCounts.put(token, nodeCounts.getOrDefault(token, 0) + 1);
        double nodeScore = 0;
        for (int count : nodeCounts.values()) nodeScore += Math.sqrt(count);
        Map<String, Boolean> edges = new HashMap<>();
        for (int i = 0; i + 1 < tokens.length; i++) edges.put(tokens[i] + "_" + tokens[i + 1], true);
        int uniqueNodes = nodeCounts.size();
        int uniqueEdges = edges.size();
        double nodeDensity = nodeScore / Math.max(trimmed.length(), 1);
        double repetitionRatio = (double) tokens.length / Math.max(uniqueNodes, 1);
        double[] raw = {
                nodeDensity, (uniqueNodes / 2.0) / 50.0, uniqueNodes / 50.0,
                tokens.length / 100.0, Math.max(0, tokens.length - 1) / 100.0,
                uniqueEdges / 100.0, repetitionRatio / 10.0,
                (double) uniqueEdges / Math.max(tokens.length, 1)
        };
        double[] mean = {0.0360279347539817, 0.021940283337614518, 0.043880566675229035,
                0.022785297279555996, 0.012785297397258704, 0.012739778137365518,
                0.10078965394839803, 0.15295495839017506};
        double[] scale = {0.047688864359725074, 0.03117266617443228, 0.06234533234886456,
                0.03434619573893724, 0.03434619555384631, 0.03407381929531839,
                0.004508379328260884, 0.32055476359510543};
        float[][] input = new float[1][8];
        for (int i = 0; i < 8; i++) input[0][i] = (float) ((raw[i] - mean[i]) / scale[i]);
        return input;
    }

    private float[][][] run(String payload) {
        Object[] inputs = new Object[]{ltigInput(payload), textInput(payload)};
        Map<Integer, Object> outputs = new HashMap<>();
        for (int i = 0; i < tflite.getOutputTensorCount(); i++) {
            int[] shape = tflite.getOutputTensor(i).shape();
            outputs.put(i, new float[shape[0]][shape[1]]);
        }
        tflite.runForMultipleInputsOutputs(inputs, outputs);
        return new float[][][]{(float[][]) outputs.get(categoryTensor), (float[][]) outputs.get(patternTensor)};
    }

    public float predictCategoryConfidence(String payload) {
        float[] scores = run(payload)[0][0];
        float max = 0;
        for (float score : scores) if (score > max) max = score;
        return max;
    }

    public ModelPredictions predict(String payload) {
        float[][][] result = run(payload);
        float confidence = 0;
        for (float score : result[0][0]) if (score > confidence) confidence = score;
        float[] patternScores = result[1][0];
        int maxIndex = 0;
        for (int i = 1; i < patternScores.length; i++) {
            if (patternScores[i] > patternScores[maxIndex]) maxIndex = i;
        }
        return new ModelPredictions(confidence, patterns[maxIndex]);
    }

    public void close() {
        if (tflite != null) tflite.close();
    }
}
