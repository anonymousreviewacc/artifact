package com.example.plgenn.ui;

import android.content.ClipData;
import android.content.ClipboardManager;
import android.content.Context;
import android.view.LayoutInflater;
import android.view.View;
import android.view.ViewGroup;
import android.widget.ImageView;
import android.widget.TextView;
import android.widget.Toast;

import androidx.annotation.NonNull;
import androidx.recyclerview.widget.RecyclerView;

import com.example.plgenn.HybridPayloadItem;
import com.example.plgenn.R;

import java.util.List;

public class PayloadAdapter extends RecyclerView.Adapter<PayloadAdapter.PayloadViewHolder> {

    private final List<HybridPayloadItem> payloadList;

    public PayloadAdapter(@NonNull List<HybridPayloadItem> payloadList) {
        this.payloadList = payloadList;
    }

    @NonNull
    @Override
    public PayloadViewHolder onCreateViewHolder(@NonNull ViewGroup parent, int viewType) {
        View view = LayoutInflater.from(parent.getContext())
                .inflate(R.layout.item_payload, parent, false);
        return new PayloadViewHolder(view);
    }

    @Override
    public void onBindViewHolder(@NonNull PayloadViewHolder holder, int position) {

        HybridPayloadItem item = payloadList.get(position);

        holder.tvNumber.setText(String.valueOf(position + 1));
        holder.tvPayload.setText(item.getPayload());
        holder.tvLength.setText("Length: " + item.getPayload().length());

        // ✅ Real category from model (no guessing)
        holder.tvCategory.setText(item.getCategory());

        // ✅ Confidence and Structural Pattern display
        holder.tvType.setText(
                "Conf: " + String.format("%.3f", item.getConfidence()) + "  SP: " + item.getStructuralPattern()
        );

        // Copy on card click
        holder.cardPayload.setOnClickListener(v ->
                copyToClipboard(v.getContext(), item.getPayload())
        );

        // Copy icon click
        holder.ivCopy.setOnClickListener(v ->
                copyToClipboard(v.getContext(), item.getPayload())
        );
    }

    @Override
    public int getItemCount() {
        return payloadList.size();
    }

    // Optional safe update method
    public void updateData(@NonNull List<HybridPayloadItem> newPayloads) {
        payloadList.clear();
        payloadList.addAll(newPayloads);
        notifyDataSetChanged();
    }

    // ================= VIEW HOLDER =================
    static class PayloadViewHolder extends RecyclerView.ViewHolder {

        View cardPayload;
        TextView tvNumber, tvCategory, tvPayload, tvLength, tvType;
        ImageView ivCopy;

        PayloadViewHolder(@NonNull View itemView) {
            super(itemView);
            cardPayload = itemView.findViewById(R.id.cardPayload);
            tvNumber = itemView.findViewById(R.id.tvNumber);
            tvCategory = itemView.findViewById(R.id.tvCategory);
            tvPayload = itemView.findViewById(R.id.tvPayload);
            tvLength = itemView.findViewById(R.id.tvLength);
            tvType = itemView.findViewById(R.id.tvType);
            ivCopy = itemView.findViewById(R.id.ivCopy);
        }
    }

    // ================= UTIL =================
    private static void copyToClipboard(Context context, String text) {

        ClipboardManager clipboard =
                (ClipboardManager) context.getSystemService(Context.CLIPBOARD_SERVICE);

        if (clipboard != null) {
            clipboard.setPrimaryClip(
                    ClipData.newPlainText("payload", text)
            );
            Toast.makeText(context, "Payload copied", Toast.LENGTH_SHORT).show();
        }
    }
}