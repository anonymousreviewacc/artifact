package com.example.plgenn.ui;

import android.content.ClipData;
import android.content.ClipboardManager;
import android.content.Intent;
import android.content.pm.PackageManager;
import android.net.Uri;
import android.os.Bundle;
import android.widget.ImageView;
import android.widget.TextView;
import android.widget.Toast;

import androidx.appcompat.app.AppCompatActivity;

import com.example.plgenn.R;

public class TestingActivity extends AppCompatActivity {

    // 🔗 One-command setup
    private static final String CMD =
            "curl -s https://raw.githubusercontent.com/NAVANEETHAN22/plgenn_app/main/plgenn_setup.sh | bash";

    private static final String TERMUX_PKG = "com.termux";
    private static final String TERMUX_ACTIVITY = "com.termux.app.TermuxActivity";

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_testing);

        ImageView btnCopy = findViewById(R.id.btnCopy);
        TextView tvCommand = findViewById(R.id.tvCommand);

        tvCommand.setText(CMD);

        // ⬇ Install Termux (F-Droid ONLY)
        findViewById(R.id.btnInstallTermux).setOnClickListener(v ->
                startActivity(new Intent(
                        Intent.ACTION_VIEW,
                        Uri.parse("https://f-droid.org/packages/com.termux/")
                ))
        );

        // 🚀 Open Termux (CORRECT WAY)
        findViewById(R.id.btnOpenTermux).setOnClickListener(v -> {

            if (!isTermuxInstalled()) {
                Toast.makeText(
                        this,
                        "Install Termux from F-Droid only (Play Store version is unsupported)",
                        Toast.LENGTH_LONG
                ).show();

                startActivity(new Intent(
                        Intent.ACTION_VIEW,
                        Uri.parse("https://f-droid.org/packages/com.termux/")
                ));
                return;
            }

            try {
                Intent intent = new Intent();
                intent.setClassName(TERMUX_PKG, TERMUX_ACTIVITY);
                intent.setFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
                startActivity(intent);
            } catch (Exception e) {
                Toast.makeText(
                        this,
                        "Installed Termux is unsupported. Use F-Droid version.",
                        Toast.LENGTH_LONG
                ).show();
            }
        });

        // 📋 Copy command (GitHub-style)
        btnCopy.setOnClickListener(v -> {
            ClipboardManager cb =
                    (ClipboardManager) getSystemService(CLIPBOARD_SERVICE);

            cb.setPrimaryClip(
                    ClipData.newPlainText("PlGenN Setup Command", CMD)
            );

            Toast.makeText(this, "Command copied", Toast.LENGTH_SHORT).show();
        });
    }

    // ✅ Correct installation check
    private boolean isTermuxInstalled() {
        try {
            getPackageManager().getPackageInfo(TERMUX_PKG, 0);
            return true;
        } catch (PackageManager.NameNotFoundException e) {
            return false;
        }
    }
}
