package com.zwmopen.xhsdl;

import java.util.ArrayList;
import java.util.List;

public final class NoteData {
    public String sourceUrl = "";
    public String referer = "https://www.xiaohongshu.com/";
    public String noteId = "";
    public String title = "";
    public String description = "";
    public String author = "";
    public String comments = "未知";
    public String likes = "未知";
    public final List<String> topics = new ArrayList<>();
    public final List<MediaItem> media = new ArrayList<>();

    public String folderName() {
        return "评" + safe(comments, 12) + "-赞" + safe(likes, 12) + "-"
                + safe(title.isEmpty() ? "未命名笔记" : title, 52) + "-"
                + safe(author.isEmpty() ? "未知作者" : author, 28);
    }

    public String copyText() {
        StringBuilder tags = new StringBuilder();
        for (String topic : topics) {
            if (tags.length() > 0) tags.append(' ');
            tags.append('#').append(topic);
        }
        return "标题：" + title + "\n\n正文：\n"
                + (description.isEmpty() ? "（正文为空）" : description)
                + "\n\n话题：" + (tags.length() == 0 ? "（无话题）" : tags) + "\n";
    }

    public String mediaFileName(int index, MediaItem item) {
        return mediaFileName(index, item, "jpg");
    }

    public String mediaFileName(int index, MediaItem item, String imageFormat) {
        boolean video = item.mimeType != null && item.mimeType.startsWith("video/");
        String label = video ? "视频" : (index == 0 ? "封面" : "内页" + index);
        String extension = video || "keep".equals(imageFormat) ? item.extension : imageFormat;
        return label + "-" + safe(title.isEmpty() ? "未命名作品" : title, 64)
                + "." + extension.replaceFirst("^\\.+", "").toLowerCase();
    }

    private static String safe(String value, int limit) {
        String cleaned = value == null ? "" : value.replaceAll("[\\\\/:*?\"<>|\\p{Cntrl}]", "_").trim();
        if (cleaned.isEmpty()) cleaned = "未知";
        return cleaned.length() > limit ? cleaned.substring(0, limit) : cleaned;
    }

    public static final class MediaItem {
        public final String url;
        public final String extension;
        public final String mimeType;

        public MediaItem(String url, String extension, String mimeType) {
            this.url = url;
            this.extension = extension;
            this.mimeType = mimeType;
        }
    }
}
