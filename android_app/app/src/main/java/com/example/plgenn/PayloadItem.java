package com.example.plgenn;

import android.os.Parcel;
import android.os.Parcelable;
import java.text.SimpleDateFormat;
import java.util.Date;
import java.util.Locale;

public class PayloadItem implements Parcelable {

    private String title;
    private String payload;
    private String category;
    private long timestamp;

    public PayloadItem(String title, String payload, String category, long timestamp) {
        this.title = title;
        this.payload = payload;
        this.category = category;
        this.timestamp = timestamp;
    }

    // Parcelable implementation
    protected PayloadItem(Parcel in) {
        title = in.readString();
        payload = in.readString();
        category = in.readString();
        timestamp = in.readLong();
    }

    public static final Creator<PayloadItem> CREATOR = new Creator<PayloadItem>() {
        @Override
        public PayloadItem createFromParcel(Parcel in) {
            return new PayloadItem(in);
        }

        @Override
        public PayloadItem[] newArray(int size) {
            return new PayloadItem[size];
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
        dest.writeLong(timestamp);
    }

    // Getters and other methods remain the same
    public String getTitle() {
        return title;
    }

    public String getPayload() {
        return payload;
    }

    public String getCategory() {
        return category;
    }

    public long getTimestamp() {
        return timestamp;
    }

    public String getFormattedTime() {
        SimpleDateFormat sdf = new SimpleDateFormat("dd/MM/yyyy HH:mm", Locale.getDefault());
        return sdf.format(new Date(timestamp));
    }

    public String getShortPayload() {
        if (payload.length() > 50) {
            return payload.substring(0, 47) + "...";
        }
        return payload;
    }
}