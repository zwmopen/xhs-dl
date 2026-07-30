package com.zwmopen.xhsdl;

import org.junit.Test;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertTrue;

public final class UpdateCheckerTest {
    @Test
    public void unifiedReleaseTagFindsAndroidAssetVersion() throws Exception {
        String json = "[{"
                + "\"tag_name\":\"v2.5.0\",\"draft\":false,\"prerelease\":false,"
                + "\"html_url\":\"https://example/release\",\"assets\":[{"
                + "\"name\":\"xiaohongshu-douyin-download-android-v9.9.9.apk\","
                + "\"browser_download_url\":\"https://example/app.apk\"}]}]";

        UpdateChecker.Result result = UpdateChecker.fromReleases(json);

        assertEquals("9.9.9", result.latestVersion);
        assertEquals("https://example/app.apk", result.apkUrl);
        assertTrue(result.updateAvailable);
    }
}
