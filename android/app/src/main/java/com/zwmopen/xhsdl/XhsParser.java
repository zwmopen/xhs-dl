package com.zwmopen.xhsdl;

import org.json.JSONArray;
import org.json.JSONException;
import org.json.JSONObject;

import java.io.BufferedReader;
import java.io.IOException;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.net.HttpURLConnection;
import java.net.URL;
import java.nio.charset.StandardCharsets;
import java.util.Iterator;

public final class XhsParser {
    private static final String USER_AGENT = "Mozilla/5.0 (Linux; Android 14; Mobile) AppleWebKit/537.36 Chrome/126 Mobile Safari/537.36";

    public NoteData fetch(String sourceUrl) throws Exception {
        String normalized = sourceUrl.replace("http://xhslink.com", "https://xhslink.com");
        Response response = request(normalized);
        JSONObject state = parseInitialState(response.body);
        JSONObject note = findNote(state);
        if (note == null) throw new IOException("公开页面没有返回笔记数据，可能链接已失效或触发访问限制");
        return parseNote(response.finalUrl, note);
    }

    private NoteData parseNote(String sourceUrl, JSONObject note) throws Exception {
        NoteData result = new NoteData();
        result.sourceUrl = sourceUrl;
        result.noteId = note.optString("noteId", "");
        result.title = note.optString("title", "");
        result.description = note.optString("desc", "");
        JSONObject user = note.optJSONObject("user");
        if (user != null) result.author = first(user.optString("nickname"), user.optString("nickName"));
        JSONObject interact = note.optJSONObject("interactInfo");
        if (interact != null) {
            result.comments = textValue(interact, "commentCount", "未知");
            result.likes = textValue(interact, "likedCount", "未知");
        }
        JSONArray tags = note.optJSONArray("tagList");
        if (tags != null) {
            for (int i = 0; i < tags.length(); i++) {
                JSONObject item = tags.optJSONObject(i);
                if (item != null && !item.optString("name").isEmpty()) result.topics.add(item.optString("name"));
            }
        }

        String type = note.optString("type", "normal");
        if ("video".equals(type)) addVideo(result, note);
        else addImages(result, note.optJSONArray("imageList"));
        if (result.media.isEmpty()) throw new IOException("未找到可下载的原始媒体地址");
        return result;
    }

    private void addImages(NoteData result, JSONArray images) {
        if (images == null) return;
        for (int i = 0; i < images.length(); i++) {
            JSONObject image = images.optJSONObject(i);
            if (image == null) continue;
            String raw = "";
            JSONArray infoList = image.optJSONArray("infoList");
            if (infoList == null) infoList = image.optJSONArray("info_list");
            if (infoList != null) {
                for (int j = 0; j < infoList.length(); j++) {
                    JSONObject candidate = infoList.optJSONObject(j);
                    if (candidate == null) continue;
                    String candidateUrl = candidate.optString("url", "");
                    if (raw.isEmpty() && !candidateUrl.isEmpty()) raw = candidateUrl;
                    String scene = first(candidate.optString("imageScene"), candidate.optString("image_scene"));
                    if ("H5_DTL".equals(scene) && !candidateUrl.isEmpty()) {
                        raw = candidateUrl;
                        break;
                    }
                }
            }
            if (raw.isEmpty()) raw = first(image.optString("urlDefault"), image.optString("url"));
            if (raw.isEmpty()) continue;
            raw = raw.replace("\\u002F", "/");
            String[] parts = raw.split("/");
            if (parts.length <= 5) continue;
            StringBuilder token = new StringBuilder();
            for (int j = 5; j < parts.length; j++) {
                if (token.length() > 0) token.append('/');
                token.append(parts[j]);
            }
            int bang = token.indexOf("!");
            if (bang >= 0) token.setLength(bang);
            if (token.length() == 0) continue;
            result.media.add(new NoteData.MediaItem(
                    "https://ci.xiaohongshu.com/" + token + "?imageView2/format/png",
                    "png", "image/png"));
        }
    }

    private void addVideo(NoteData result, JSONObject note) {
        JSONObject video = note.optJSONObject("video");
        String originKey = deepString(video, "consumer", "originVideoKey");
        if (!originKey.isEmpty()) {
            result.media.add(new NoteData.MediaItem(
                    "https://sns-video-bd.xhscdn.com/" + originKey, "mp4", "video/mp4"));
            return;
        }
        JSONObject stream = deepObject(video, "media", "stream");
        JSONArray items = stream == null ? null : stream.optJSONArray("h264");
        if (items == null || items.length() == 0) return;
        JSONObject best = items.optJSONObject(items.length() - 1);
        if (best == null) return;
        String url = best.optString("masterUrl", "");
        JSONArray backups = best.optJSONArray("backupUrls");
        if (backups != null && backups.length() > 0) url = backups.optString(0, url);
        if (!url.isEmpty()) result.media.add(new NoteData.MediaItem(url, "mp4", "video/mp4"));
    }

    private Response request(String rawUrl) throws IOException {
        HttpURLConnection connection = (HttpURLConnection) new URL(rawUrl).openConnection();
        connection.setInstanceFollowRedirects(true);
        connection.setConnectTimeout(15000);
        connection.setReadTimeout(25000);
        connection.setRequestProperty("User-Agent", USER_AGENT);
        connection.setRequestProperty("Accept-Language", "zh-CN,zh;q=0.9");
        connection.setRequestProperty("Referer", "https://www.xiaohongshu.com/");
        connection.connect();
        int status = connection.getResponseCode();
        if (status < 200 || status >= 400) throw new IOException("访问公开页面失败：HTTP " + status);
        String body = readAll(connection.getInputStream());
        String finalUrl = connection.getURL().toString();
        connection.disconnect();
        return new Response(finalUrl, body);
    }

    private JSONObject parseInitialState(String html) throws JSONException, IOException {
        String marker = "window.__INITIAL_STATE__=";
        int start = html.indexOf(marker);
        if (start < 0) throw new IOException("页面结构已变化，未找到公开笔记数据");
        start += marker.length();
        int end = html.indexOf("</script>", start);
        if (end < 0) throw new IOException("页面数据不完整");
        String json = html.substring(start, end).trim();
        if (json.endsWith(";")) json = json.substring(0, json.length() - 1);
        json = json.replaceAll("(?<=[:\\[,])\\s*undefined(?=\\s*[,}\\]])", "null");
        return new JSONObject(json);
    }

    private JSONObject findNote(JSONObject root) {
        JSONObject phone = deepObject(root, "noteData", "data", "noteData");
        if (phone != null) return phone;
        JSONObject noteRoot = root.optJSONObject("note");
        JSONObject map = noteRoot == null ? null : noteRoot.optJSONObject("noteDetailMap");
        if (map == null) return null;
        Iterator<String> keys = map.keys();
        while (keys.hasNext()) {
            JSONObject entry = map.optJSONObject(keys.next());
            if (entry != null && entry.optJSONObject("note") != null) return entry.optJSONObject("note");
        }
        return null;
    }

    private static JSONObject deepObject(JSONObject root, String... keys) {
        JSONObject value = root;
        if (value == null) return null;
        for (String key : keys) {
            value = value.optJSONObject(key);
            if (value == null) return null;
        }
        return value;
    }

    private static String deepString(JSONObject root, String parent, String key) {
        JSONObject value = root == null ? null : root.optJSONObject(parent);
        return value == null ? "" : value.optString(key, "");
    }

    private static String first(String first, String second) {
        return first == null || first.isEmpty() ? (second == null ? "" : second) : first;
    }

    private static String textValue(JSONObject object, String key, String fallback) {
        Object value = object.opt(key);
        return value == null || JSONObject.NULL.equals(value) ? fallback : String.valueOf(value);
    }

    private static String readAll(InputStream input) throws IOException {
        StringBuilder value = new StringBuilder();
        try (BufferedReader reader = new BufferedReader(new InputStreamReader(input, StandardCharsets.UTF_8))) {
            char[] buffer = new char[8192];
            int count;
            while ((count = reader.read(buffer)) >= 0) value.append(buffer, 0, count);
        }
        return value.toString();
    }

    private static final class Response {
        final String finalUrl;
        final String body;
        Response(String finalUrl, String body) { this.finalUrl = finalUrl; this.body = body; }
    }
}
