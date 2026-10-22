package com.example.plgenn.ui;

import android.content.Intent;
import android.os.Bundle;

import androidx.appcompat.app.AppCompatActivity;

import com.example.plgenn.R;
import com.google.android.material.card.MaterialCardView;

public class HomeActivity extends AppCompatActivity {

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_home);

        // ================= INIT =================
        MaterialCardView btnRuleBased = findViewById(R.id.btnRuleBased);
        MaterialCardView btnGNN = findViewById(R.id.btnGNN);
        MaterialCardView btnTesting = findViewById(R.id.btnTesting); // 🧪 Testing

        // ================= NAVIGATION =================

        // Rule-Based Generator
        btnRuleBased.setOnClickListener(v -> {
            Intent intent = new Intent(
                    HomeActivity.this,
                    MainActivity.class
            );
            startActivity(intent);
        });

        // GNN / Hybrid Generator
        btnGNN.setOnClickListener(v -> {
            Intent intent = new Intent(
                    HomeActivity.this,
                    GNNActivity.class
            );
            startActivity(intent);
        });

        // 🧪 Payload Testing Page
        btnTesting.setOnClickListener(v -> {
            Intent intent = new Intent(
                    HomeActivity.this,
                    TestingActivity.class
            );
            startActivity(intent);
        });
    }
}
