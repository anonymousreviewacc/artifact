package com.example.plgenn.utils;

import java.util.ArrayList;
import java.util.List;

public class ContextFormatter {

    public static List<String> formatAllTargets(String payload, String category) {

        List<String> results = new ArrayList<>();

        results.add("[GENERIC] " + payload);

        results.add("[DVWA] id=1" + payload + "&Submit=Submit");

        results.add("[BWAPP] login=" + payload + "&password=test&form=submit");

        results.add("[XVWA] search=" + payload);

        results.add("[JUICE] {\"email\":\"" + payload + "\",\"password\":\"test\"}");

        return results;
    }
}