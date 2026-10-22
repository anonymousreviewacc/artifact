package com.example.plgenn.ui;

import android.content.ClipData;
import android.content.ClipboardManager;
import android.os.Bundle;
import android.view.View;
import android.widget.*;

import androidx.appcompat.app.AppCompatActivity;
import androidx.core.widget.NestedScrollView;
import androidx.recyclerview.widget.LinearLayoutManager;
import androidx.recyclerview.widget.RecyclerView;

import com.example.plgenn.HybridPayloadItem;
import com.example.plgenn.R;
import com.example.plgenn.utils.GNNGenerator;
import com.example.plgenn.utils.LTIGModelHelper;

import java.util.ArrayList;
import java.util.List;

public class GNNActivity extends AppCompatActivity {

    private EditText etTarget, etDescription;
    private Spinner spCategoryMode, spComplexity, spSingleCategoryType;
    private LinearLayout llSingleCategoryContainer;
    private Button btnGenerate, btnCopyAll;
    private Switch swUseGNN;
    private RecyclerView rvPayloads;
    private TextView tvStatus;

    // Scroll controls
    private NestedScrollView scrollView;
    private ImageButton btnScrollTop, btnScrollBottom;

    private GNNGenerator gnnGenerator;
    private LTIGModelHelper ltigModel;
    private volatile boolean modelLoading;
    private PayloadAdapter adapter;

    private final List<HybridPayloadItem> payloadList = new ArrayList<>();

    private final String[] ALL_CATEGORIES = {
            "SQL Injection",
            "XSS",
            "IDOR",
            "Command Injection",
            "Path Traversal",
            "SSRF",
            "Local File Inclusion",
            "Remote File Inclusion",
            "XXE",
            "GraphQL Injection",
            "Open Redirect",
            "API Abuse"
    };

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_gnn);

        initViews();
        setupSpinners();
        setupRecycler();
        setupScrollButtons();

        btnGenerate.setOnClickListener(v -> generatePayloads());
        btnCopyAll.setOnClickListener(v -> copyAllPayloads());

        gnnGenerator = new GNNGenerator(this);

        modelLoading = true;
        tvStatus.setText("⏳ Model 6 loading…");
        new Thread(() -> {
            try {
                LTIGModelHelper loaded = new LTIGModelHelper(getApplicationContext());
                runOnUiThread(() -> {
                    ltigModel = loaded;
                    modelLoading = false;
                    if (!isFinishing()) tvStatus.setText("✅ Hybrid LTIG Model 6 ACTIVE");
                    else loaded.close();
                });
            } catch (Exception e) {
                android.util.Log.e("GNNActivity", "Failed to load the bundled Model 6 TFLite assets", e);
                runOnUiThread(() -> {
                    modelLoading = false;
                    if (!isFinishing()) tvStatus.setText("❌ Model 6 NOT LOADED");
                });
            }
        }, "model6-loader").start();
    }

    private void initViews() {

        etTarget = findViewById(R.id.etTarget);
        etDescription = findViewById(R.id.etDescription);

        spCategoryMode = findViewById(R.id.spCategory);
        spComplexity = findViewById(R.id.spComplexity);
        spSingleCategoryType = findViewById(R.id.spSingleCategoryType);

        llSingleCategoryContainer = findViewById(R.id.llSingleCategoryContainer);

        btnGenerate = findViewById(R.id.btnGenerate);
        btnCopyAll = findViewById(R.id.btnCopyAll);

        swUseGNN = findViewById(R.id.swUseGNN);

        rvPayloads = findViewById(R.id.rvPayloads);
        tvStatus = findViewById(R.id.tvStatus);

        scrollView = findViewById(R.id.scrollView);
        btnScrollTop = findViewById(R.id.btnScrollTop);
        btnScrollBottom = findViewById(R.id.btnScrollBottom);
    }

    private void setupSpinners() {

        String[] modes = {"Single Category", "All Categories"};

        ArrayAdapter<String> modeAdapter =
                new ArrayAdapter<>(this,
                        android.R.layout.simple_spinner_item,
                        modes);

        modeAdapter.setDropDownViewResource(
                android.R.layout.simple_spinner_dropdown_item);

        spCategoryMode.setAdapter(modeAdapter);

        spCategoryMode.setOnItemSelectedListener(
                new AdapterView.OnItemSelectedListener() {

                    @Override
                    public void onItemSelected(AdapterView<?> parent,
                                               View view,
                                               int position,
                                               long id) {

                        llSingleCategoryContainer.setVisibility(
                                position == 0 ? View.VISIBLE : View.GONE
                        );
                    }

                    @Override
                    public void onNothingSelected(AdapterView<?> parent) {}
                });

        String[] complexities = {"Basic", "Advanced", "Evasion"};

        ArrayAdapter<String> compAdapter =
                new ArrayAdapter<>(this,
                        android.R.layout.simple_spinner_item,
                        complexities);

        compAdapter.setDropDownViewResource(
                android.R.layout.simple_spinner_dropdown_item);

        spComplexity.setAdapter(compAdapter);

        ArrayAdapter<String> catAdapter =
                new ArrayAdapter<>(this,
                        android.R.layout.simple_spinner_item,
                        ALL_CATEGORIES);

        catAdapter.setDropDownViewResource(
                android.R.layout.simple_spinner_dropdown_item);

        spSingleCategoryType.setAdapter(catAdapter);

        llSingleCategoryContainer.setVisibility(View.VISIBLE);
    }

    private void setupRecycler() {

        adapter = new PayloadAdapter(payloadList);

        rvPayloads.setLayoutManager(new LinearLayoutManager(this));
        rvPayloads.setAdapter(adapter);
    }

    // Scroll buttons + auto hide logic
    private void setupScrollButtons() {

        btnScrollTop.setOnClickListener(v ->
                scrollView.smoothScrollTo(0, 0));

        btnScrollBottom.setOnClickListener(v ->
                scrollView.fullScroll(View.FOCUS_DOWN));

        scrollView.setOnScrollChangeListener(
                (NestedScrollView.OnScrollChangeListener)
                        (v, scrollX, scrollY, oldScrollX, oldScrollY) -> {

                            if (scrollY < 200)
                                btnScrollTop.setVisibility(View.GONE);
                            else
                                btnScrollTop.setVisibility(View.VISIBLE);

                            View view = scrollView.getChildAt(0);

                            if (scrollY >=
                                    (view.getMeasuredHeight()
                                            - v.getMeasuredHeight() - 200))
                                btnScrollBottom.setVisibility(View.GONE);
                            else
                                btnScrollBottom.setVisibility(View.VISIBLE);
                        });
    }

    private void generatePayloads() {

        btnGenerate.setEnabled(false);
        payloadList.clear();

        String target = etTarget.getText().toString().trim();
        String desc = etDescription.getText().toString().trim();
        String complexity = spComplexity.getSelectedItem().toString();
        String mode = spCategoryMode.getSelectedItem().toString();

        new Thread(() -> {

            int index = 1;

            if (mode.equals("Single Category")) {

                String selectedCategory =
                        spSingleCategoryType.getSelectedItem().toString();

                List<String> generated =
                        gnnGenerator.generatePayloadsWithGNN(
                                selectedCategory,
                                desc,
                                complexity,
                                target);

                index = addPayloads(selectedCategory, generated, index);

            } else {

                for (String category : ALL_CATEGORIES) {

                    List<String> generated =
                            gnnGenerator.generatePayloadsWithGNN(
                                    category,
                                    desc,
                                    complexity,
                                    target);

                    index = addPayloads(category, generated, index);
                }
            }

            runOnUiThread(() -> {

                adapter.notifyDataSetChanged();
                btnGenerate.setEnabled(true);

                scrollView.smoothScrollTo(0, 0);
            });

        }).start();
    }

    private int addPayloads(String category,
                            List<String> generated,
                            int startIndex) {

        int index = startIndex;

        for (String payload : generated) {

            float confidence = 0f;
            String pattern = "OTHER";

            if (swUseGNN.isChecked() && ltigModel != null) {

                try {
                    LTIGModelHelper.ModelPredictions preds = ltigModel.predict(payload);
                    confidence = preds.confidence;
                    pattern = preds.pattern;
                } catch (Exception e) {
                    android.util.Log.e("GNNActivity", "Model 6 inference failed for generated payload", e);
                }
            }

            payloadList.add(
                    new HybridPayloadItem(
                            "Payload " + index,
                            payload,
                            shortLabel(category),
                            confidence,
                            pattern
                    )
            );

            index++;
        }

        return index;
    }

    private String shortLabel(String fullCategory) {

        switch (fullCategory) {

            case "SQL Injection": return "SQL";
            case "XSS": return "XSS";
            case "IDOR": return "IDOR";
            case "Command Injection": return "CMD";
            case "Path Traversal": return "PATH";
            case "SSRF": return "SSRF";
            case "Local File Inclusion": return "LFI";
            case "Remote File Inclusion": return "RFI";
            case "XXE": return "XXE";
            case "GraphQL Injection": return "GQL";
            case "Open Redirect": return "REDIR";
            case "API Abuse": return "API";
        }

        return "UNK";
    }

    private void copyAllPayloads() {

        if (payloadList.isEmpty()) {

            Toast.makeText(this,
                    "No payloads to copy",
                    Toast.LENGTH_SHORT).show();

            return;
        }

        StringBuilder sb = new StringBuilder();

        for (HybridPayloadItem item : payloadList)
            sb.append(item.getPayload()).append("\n\n");

        ClipboardManager clipboard =
                (ClipboardManager) getSystemService(CLIPBOARD_SERVICE);

        clipboard.setPrimaryClip(
                ClipData.newPlainText("Payloads", sb.toString()));

        Toast.makeText(this,
                "Payloads copied",
                Toast.LENGTH_SHORT).show();
    }

    @Override
    protected void onDestroy() {

        super.onDestroy();

        if (gnnGenerator != null)
            gnnGenerator.close();

        if (ltigModel != null)
            ltigModel.close();
    }
}
