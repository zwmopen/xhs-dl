package com.zwmopen.xhsdl;

import org.json.JSONArray;
import org.json.JSONObject;

import java.io.BufferedReader;
import java.io.InputStreamReader;
import java.net.HttpURLConnection;
import java.net.URL;

public final class UpdateChecker {
    private static final String RELEASES = "https://api.github.com/repos/zwmopen/xhs-dl/releases?per_page=20";

    private UpdateChecker() {}

    public static Result checkAndroid() throws Exception {
        HttpURLConnection connection = (HttpURLConnection) new URL(RELEASES).openConnection();
        connection.setConnectTimeout(8000);
        connection.setReadTimeout(8000);
        connection.setRequestProperty("User-Agent", "red-sweet-potato-download-android");
        StringBuilder body = new StringBuilder();
        try (BufferedReader reader = new BufferedReader(new InputStreamReader(connection.getInputStream()))) {
            String line;
            while ((line = reader.readLine()) != null) body.append(line);
        } finally {
            connection.disconnect();
        }
        JSONArray releases = new JSONArray(body.toString());
        for (int i = 0; i < releases.length(); i++) {
            JSONObject release = releases.optJSONObject(i);
            if (release == null) continue;
            String tag = release.optString("tag_name");
            if (!tag.startsWith("android-v")) continue;
            String latest = tag.substring("android-v".length());
            String assetUrl = "";
            JSONArray assets = release.optJSONArray("assets");
            if (assets != null) {
                for (int j = 0; j < assets.length(); j++) {
                    JSONObject asset = assets.optJSONObject(j);
                    if (asset != null && asset.optString("name").endsWith(".apk")) {
                        assetUrl = asset.optString("browser_download_url");
                        break;
                    }
                }
            }
            return new Result(
                    BuildConfig.VERSION_NAME,
                    latest,
                    compare(latest, BuildConfig.VERSION_NAME) > 0,
                    release.optString("html_url"),
                    assetUrl
            );
        }
        throw new IllegalStateException("没有找到安卓发布版本");
    }

    private static int compare(String left, String right) {
        String[] a = left.split("\\.");
        String[] b = right.split("\\.");
        for (int i = 0; i < Math.max(a.length, b.length); i++) {
            int x = i < a.length ? number(a[i]) : 0;
            int y = i < b.length ? number(b[i]) : 0;
            if (x != y) return Integer.compare(x, y);
        }
        return 0;
    }

    private static int number(String value) {
        try { return Integer.parseInt(value.replaceAll("\\D", "")); }
        catch (Exception ignored) { return 0; }
    }

    public static final class Result {
        public final String currentVersion;
        public final String latestVersion;
        public final boolean updateAvailable;
        public final String releaseUrl;
        public final String apkUrl;

        Result(String currentVersion, String latestVersion, boolean updateAvailable, String releaseUrl, String apkUrl) {
            this.currentVersion = currentVersion;
            this.latestVersion = latestVersion;
            this.updateAvailable = updateAvailable;
            this.releaseUrl = releaseUrl;
            this.apkUrl = apkUrl;
        }
    }
}
