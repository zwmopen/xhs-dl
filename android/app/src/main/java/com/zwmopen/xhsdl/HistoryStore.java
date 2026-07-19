package com.zwmopen.xhsdl;

import android.content.Context;

import org.json.JSONArray;
import org.json.JSONObject;

import java.io.File;
import java.io.FileInputStream;
import java.io.FileOutputStream;
import java.nio.charset.StandardCharsets;

public final class HistoryStore {
    private final File file;

    public HistoryStore(Context context) {
        this.file = new File(context.getFilesDir(), "history.json");
    }

    public synchronized void add(NoteData note) throws Exception {
        JSONArray current = read();
        JSONArray next = new JSONArray();
        String key = note.noteId.isEmpty() ? note.sourceUrl : note.noteId;
        for (int i = 0; i < current.length(); i++) {
            JSONObject old = current.optJSONObject(i);
            if (old == null) continue;
            String oldKey = old.optString("笔记ID");
            if (oldKey.isEmpty()) oldKey = old.optString("下载网址");
            if (!key.equals(oldKey)) next.put(old);
        }
        JSONObject item = new JSONObject();
        item.put("下载网址", note.sourceUrl);
        item.put("笔记ID", note.noteId);
        item.put("标题", note.title);
        next.put(item);
        write(next);
    }

    public synchronized JSONArray read() {
        try {
            if (!file.isFile()) return new JSONArray();
            byte[] data;
            try (FileInputStream input = new FileInputStream(file)) {
                data = new byte[(int) file.length()];
                int offset = 0;
                while (offset < data.length) {
                    int count = input.read(data, offset, data.length - offset);
                    if (count < 0) break;
                    offset += count;
                }
            }
            return new JSONArray(new String(data, StandardCharsets.UTF_8));
        } catch (Exception ignored) {
            return new JSONArray();
        }
    }

    private void write(JSONArray value) throws Exception {
        File temporary = new File(file.getParentFile(), "history.json.tmp");
        try (FileOutputStream output = new FileOutputStream(temporary)) {
            output.write(value.toString(2).getBytes(StandardCharsets.UTF_8));
        }
        if (file.exists() && !file.delete()) throw new IllegalStateException("无法更新历史记录");
        if (!temporary.renameTo(file)) throw new IllegalStateException("无法保存历史记录");
    }
}
