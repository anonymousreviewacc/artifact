package com.example.plgenn;

import android.os.Parcel;
import android.os.Parcelable;

public class HybridPayloadItem implements Parcelable {

    private String title;
    private String payload;
    private String category;
    private float confidence;
    private String structuralPattern;

    // ================= Constructor =================

    public HybridPayloadItem(String title,
                             String payload,
                             String category,
                             float confidence,
                             String structuralPattern) {

        this.title = title;
        this.payload = payload;
        this.category = category;
        this.confidence = confidence;
        this.structuralPattern = structuralPattern;
    }

    // ================= Parcelable =================

    protected HybridPayloadItem(Parcel in) {
        title = in.readString();
        payload = in.readString();
        category = in.readString();
        confidence = in.readFloat();
        structuralPattern = in.readString();
    }

    public static final Creator<HybridPayloadItem> CREATOR =
            new Creator<HybridPayloadItem>() {
                @Override
                public HybridPayloadItem createFromParcel(Parcel in) {
                    return new HybridPayloadItem(in);
                }

                @Override
                public HybridPayloadItem[] newArray(int size) {
                    return new HybridPayloadItem[size];
                }
            };

    @Override
    public int describeContents() {
        return 0;
    }

    @Override
    public void writeToParcel(Parcel dest, int flags) {
        dest.writeString(title);
        dest.writeString(payload);
        dest.writeString(category);
        dest.writeFloat(confidence);
        dest.writeString(structuralPattern);
    }

    // ================= Getters =================

    public String getTitle() {
        return title;
    }

    public String getPayload() {
        return payload;
    }

    public String getCategory() {
        return category;
    }

    public float getConfidence() {
        return confidence;
    }

    public String getStructuralPattern() {
        return structuralPattern;
    }

    // Optional short preview
    public String getShortPayload() {
        if (payload != null && payload.length() > 60) {
            return payload.substring(0, 57) + "...";
        }
        return payload;
    }
}