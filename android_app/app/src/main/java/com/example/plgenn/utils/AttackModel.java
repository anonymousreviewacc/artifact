package com.example.plgenn.utils;

import android.content.Context;
import org.tensorflow.lite.Interpreter;

import java.io.FileInputStream;
import java.io.IOException;
import java.nio.MappedByteBuffer;
import java.nio.channels.FileChannel;
import java.util.HashMap;
import java.util.Map;

public class AttackModel {

    private Interpreter interpreter;

    public AttackModel(Context context) throws IOException {
        interpreter = new Interpreter(loadModelFile(context));
    }

    private MappedByteBuffer loadModelFile(Context context) throws IOException {
        FileInputStream fis = new FileInputStream(
                context.getAssets().openFd("attack_model.tflite").getFileDescriptor());
        FileChannel fileChannel = fis.getChannel();
        long startOffset = context.getAssets()
                .openFd("attack_model.tflite").getStartOffset();
        long declaredLength = context.getAssets()
                .openFd("attack_model.tflite").getDeclaredLength();

        return fileChannel.map(FileChannel.MapMode.READ_ONLY,
                startOffset, declaredLength);
    }

    public float[][] predict(String payload) {

        Object[] input = new Object[]{ new String[]{ payload } };

        float[][] category = new float[1][11];
        float[][] pattern = new float[1][35];
        float[][] obfuscation = new float[1][3];

        Map<Integer, Object> outputs = new HashMap<>();
        outputs.put(0, category);
        outputs.put(1, pattern);
        outputs.put(2, obfuscation);

        interpreter.runForMultipleInputsOutputs(input, outputs);

        return new float[][]{
                category[0],
                pattern[0],
                obfuscation[0]
        };
    }
}