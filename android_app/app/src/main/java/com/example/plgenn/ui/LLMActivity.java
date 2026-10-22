package com.example.plgenn.ui;

import android.os.Bundle;
import android.view.View;
import android.widget.Button;
import android.widget.EditText;
import android.widget.ProgressBar;
import android.widget.TextView;
import android.widget.Toast;
import androidx.appcompat.app.AppCompatActivity;
import com.example.plgenn.R;
import com.example.plgenn.utils.LLMGenerator;

import java.text.SimpleDateFormat;
import java.util.Date;
import java.util.Locale;

public class LLMActivity extends AppCompatActivity {
    private EditText etTarget, etDescription, etHttpRequest;
    private Button btnGenerate;
    private TextView tvOutput;
    private ProgressBar progressBar;
    private LLMGenerator llmGenerator;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_llm);

        // Initialize views
        etTarget = findViewById(R.id.etTarget);
        etDescription = findViewById(R.id.etDescription);
        etHttpRequest = findViewById(R.id.etHttpRequest);
        btnGenerate = findViewById(R.id.btnGenerate);
        tvOutput = findViewById(R.id.tvOutput);
        progressBar = findViewById(R.id.progressBar);

        // Initialize LLM Generator
        llmGenerator = new LLMGenerator();

        // Set up generate button
        btnGenerate.setOnClickListener(v -> generatePayloads());
    }

    private void generatePayloads() {
        String target = etTarget.getText().toString().trim();
        String description = etDescription.getText().toString().trim();
        String httpRequest = etHttpRequest.getText().toString().trim();

        if (target.isEmpty()) {
            Toast.makeText(this, "Please enter a target URL or IP", Toast.LENGTH_SHORT).show();
            return;
        }

        // Show loading
        progressBar.setVisibility(View.VISIBLE);
        btnGenerate.setEnabled(false);
        tvOutput.setText("🔄 Generating payloads with AI...");

        // Run in background thread
        new Thread(() -> {
            try {
                String result = llmGenerator.generate(target, description, httpRequest);

                // Update UI on main thread
                runOnUiThread(() -> {
                    tvOutput.setText(result);
                });
            } catch (Exception e) {
                runOnUiThread(() -> {
                    String timestamp = new SimpleDateFormat("dd/MM/yyyy HH:mm", Locale.getDefault()).format(new Date());
                    tvOutput.setText("❌ Error: " + e.getMessage() + "\n\n" +
                            "Try using Rule-Based generator instead.\n" +
                            "Time: " + timestamp);
                });
            } finally {
                runOnUiThread(() -> {
                    progressBar.setVisibility(View.GONE);
                    btnGenerate.setEnabled(true);
                });
            }
        }).start();
    }
}