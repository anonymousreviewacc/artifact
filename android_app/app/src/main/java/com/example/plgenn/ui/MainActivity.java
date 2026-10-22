package com.example.plgenn.ui;

import android.os.Bundle;
import android.view.*;
import android.widget.*;
import androidx.annotation.NonNull;
import androidx.appcompat.app.AppCompatActivity;
import androidx.recyclerview.widget.*;
import com.example.plgenn.PayloadGenerator;
import com.example.plgenn.PayloadItem;
import com.example.plgenn.R;
import com.github.ybq.android.spinkit.SpinKitView;
import java.util.*;

public class MainActivity extends AppCompatActivity {

    private EditText etTarget, etDescription;
    private Spinner spCategory, spComplexity;
    private Button btnGenerate;
    private SpinKitView progressBar;
    private RecyclerView rvPayloads;

    private PayloadItemAdapter adapter;
    private PayloadGenerator payloadGenerator;
    private List<PayloadItem> payloadList;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_main);

        initializeViews();
        setupSpinners();
        setupRecyclerView();

        payloadGenerator = new PayloadGenerator();

        btnGenerate.setOnClickListener(v -> generatePayload());
    }

    private void initializeViews() {
        etTarget = findViewById(R.id.etTarget);
        etDescription = findViewById(R.id.etDescription);
        spCategory = findViewById(R.id.spCategory);
        spComplexity = findViewById(R.id.spComplexity);
        btnGenerate = findViewById(R.id.btnGenerate);
        progressBar = findViewById(R.id.progressBar);
        rvPayloads = findViewById(R.id.rvPayloads);
    }

    private void setupSpinners() {

        List<String> categories =
                new PayloadGenerator().getAvailableCategories();

        ArrayAdapter<String> categoryAdapter =
                new ArrayAdapter<>(this,
                        android.R.layout.simple_spinner_item,
                        categories);

        categoryAdapter.setDropDownViewResource(
                android.R.layout.simple_spinner_dropdown_item);

        spCategory.setAdapter(categoryAdapter);

        String[] complexities = {"Basic", "Advanced", "Evasion"};

        ArrayAdapter<String> complexityAdapter =
                new ArrayAdapter<>(this,
                        android.R.layout.simple_spinner_item,
                        complexities);

        complexityAdapter.setDropDownViewResource(
                android.R.layout.simple_spinner_dropdown_item);

        spComplexity.setAdapter(complexityAdapter);
    }

    private void setupRecyclerView() {
        payloadList = new ArrayList<>();
        adapter = new PayloadItemAdapter(payloadList);

        rvPayloads.setLayoutManager(new LinearLayoutManager(this));
        rvPayloads.setAdapter(adapter);

        rvPayloads.addItemDecoration(
                new DividerItemDecoration(this,
                        DividerItemDecoration.VERTICAL));
    }

    private void generatePayload() {

        String target = etTarget.getText().toString().trim();
        String description = etDescription.getText().toString().trim();
        String category = spCategory.getSelectedItem().toString();
        String complexity = spComplexity.getSelectedItem().toString();

        if (target.isEmpty()) {
            etTarget.setError("Enter target URL or IP");
            return;
        }

        if (!payloadGenerator.isValidTarget(target)) {
            etTarget.setError("Invalid target format");
            return;
        }

        progressBar.setVisibility(View.VISIBLE);
        btnGenerate.setEnabled(false);

        new Thread(() -> {

            String payload =
                    payloadGenerator.generatePayload(
                            category,
                            target,
                            complexity,
                            description
                    );

            if (!payloadGenerator.validatePayload(payload, category)) {
                payload = "Invalid payload generated.";
            }

            PayloadItem payloadItem = new PayloadItem(
                    "Payload for " + target,
                    payload,
                    category + " ⚡",
                    System.currentTimeMillis()
            );

            runOnUiThread(() -> {
                progressBar.setVisibility(View.GONE);
                btnGenerate.setEnabled(true);

                payloadList.add(0, payloadItem);
                adapter.notifyItemInserted(0);
                rvPayloads.smoothScrollToPosition(0);

                showPayloadDetail(payloadItem);
            });

        }).start();
    }

    private void showPayloadDetail(PayloadItem payloadItem) {

        new android.app.AlertDialog.Builder(this)
                .setTitle("Payload Details")
                .setMessage(payloadItem.getPayload())
                .setPositiveButton("Copy", (dialog, which) -> {
                    android.content.ClipboardManager clipboard =
                            (android.content.ClipboardManager)
                                    getSystemService(CLIPBOARD_SERVICE);

                    clipboard.setPrimaryClip(
                            android.content.ClipData.newPlainText(
                                    "Payload",
                                    payloadItem.getPayload()));
                })
                .setNegativeButton("Close", null)
                .show();
    }

    @Override
    protected void onDestroy() {
        super.onDestroy();
    }

    // ============================
    // Adapter
    // ============================

    private class PayloadItemAdapter
            extends RecyclerView.Adapter<PayloadItemAdapter.ViewHolder> {

        private List<PayloadItem> payloadItems;

        public PayloadItemAdapter(List<PayloadItem> payloadItems) {
            this.payloadItems = payloadItems;
        }

        @NonNull
        @Override
        public ViewHolder onCreateViewHolder(
                @NonNull ViewGroup parent,
                int viewType) {

            View view = LayoutInflater.from(parent.getContext())
                    .inflate(android.R.layout.simple_list_item_1,
                            parent,
                            false);

            return new ViewHolder(view);
        }

        @Override
        public void onBindViewHolder(
                @NonNull ViewHolder holder,
                int position) {

            PayloadItem item = payloadItems.get(position);
            holder.textView.setText(
                    item.getTitle() + " - " + item.getCategory());
        }

        @Override
        public int getItemCount() {
            return payloadItems.size();
        }

        class ViewHolder extends RecyclerView.ViewHolder {

            TextView textView;

            public ViewHolder(@NonNull View itemView) {
                super(itemView);

                textView = itemView.findViewById(android.R.id.text1);

                itemView.setOnClickListener(v -> {
                    PayloadItem item =
                            payloadItems.get(getAdapterPosition());
                    showPayloadDetail(item);
                });
            }
        }
    }
}