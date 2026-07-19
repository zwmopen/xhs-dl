package com.zwmopen.xhsdl;

import android.content.ContentResolver;
import android.content.ContentValues;
import android.content.Context;
import android.database.Cursor;
import android.net.Uri;
import android.os.Environment;
import android.provider.MediaStore;
import android.provider.DocumentsContract;

import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;
import java.net.HttpURLConnection;
import java.net.URL;
import java.nio.charset.StandardCharsets;

public final class MediaSaver {
    private static final String USER_AGENT = "Mozilla/5.0 (Linux; Android 14; Mobile) AppleWebKit/537.36 Chrome/126 Mobile Safari/537.36";
    private final Context context;

    public MediaSaver(Context context) {
        this.context = context.getApplicationContext();
    }

    public int save(NoteData note, String rootFolder, String treeUri, Progress progress) throws IOException {
        if (treeUri != null && !treeUri.trim().isEmpty()) {
            return saveToTree(note, Uri.parse(treeUri), progress);
        }
        String relative = Environment.DIRECTORY_DOWNLOADS + "/" + cleanFolder(rootFolder) + "/" + note.folderName() + "/";
        int completed = 0;
        for (int i = 0; i < note.media.size(); i++) {
            NoteData.MediaItem item = note.media.get(i);
            String fileName = String.format("%02d.%s", i + 1, item.extension);
            if (!exists(fileName, relative)) writeFromNetwork(item.url, fileName, item.mimeType, relative);
            completed++;
            if (progress != null) progress.onMedia(completed, note.media.size());
        }
        replaceText("文案.txt", note.copyText(), relative);
        return completed;
    }

    private int saveToTree(NoteData note, Uri treeUri, Progress progress) throws IOException {
        Uri root = DocumentsContract.buildDocumentUriUsingTree(
                treeUri, DocumentsContract.getTreeDocumentId(treeUri));
        Uri noteDirectory = findOrCreateDirectory(root, note.folderName());
        int completed = 0;
        for (int i = 0; i < note.media.size(); i++) {
            NoteData.MediaItem item = note.media.get(i);
            String fileName = String.format("%02d.%s", i + 1, item.extension);
            if (findChild(noteDirectory, fileName) == null) {
                Uri destination = DocumentsContract.createDocument(
                        context.getContentResolver(), noteDirectory, item.mimeType, fileName);
                if (destination == null) throw new IOException("无法在所选目录创建媒体文件");
                writeTreeNetwork(item.url, destination);
            }
            completed++;
            if (progress != null) progress.onMedia(completed, note.media.size());
        }
        Uri oldText = findChild(noteDirectory, "文案.txt");
        if (oldText != null) DocumentsContract.deleteDocument(context.getContentResolver(), oldText);
        Uri textFile = DocumentsContract.createDocument(
                context.getContentResolver(), noteDirectory, "text/plain", "文案.txt");
        if (textFile == null) throw new IOException("无法在所选目录创建文案文件");
        try (OutputStream output = context.getContentResolver().openOutputStream(textFile, "w")) {
            if (output == null) throw new IOException("无法写入文案文件");
            output.write(note.copyText().getBytes(StandardCharsets.UTF_8));
        }
        return completed;
    }

    private Uri findOrCreateDirectory(Uri parent, String name) throws IOException {
        Uri existing = findChild(parent, name);
        if (existing != null) return existing;
        Uri created = DocumentsContract.createDocument(
                context.getContentResolver(), parent,
                DocumentsContract.Document.MIME_TYPE_DIR, cleanFolder(name));
        if (created == null) throw new IOException("无法在所选目录创建笔记文件夹");
        return created;
    }

    private Uri findChild(Uri parent, String name) {
        ContentResolver resolver = context.getContentResolver();
        Uri children = DocumentsContract.buildChildDocumentsUriUsingTree(
                parent, DocumentsContract.getDocumentId(parent));
        String[] columns = {
                DocumentsContract.Document.COLUMN_DOCUMENT_ID,
                DocumentsContract.Document.COLUMN_DISPLAY_NAME
        };
        try (Cursor cursor = resolver.query(children, columns, null, null, null)) {
            if (cursor == null) return null;
            while (cursor.moveToNext()) {
                if (name.equals(cursor.getString(1))) {
                    return DocumentsContract.buildDocumentUriUsingTree(parent, cursor.getString(0));
                }
            }
        } catch (Exception ignored) {
        }
        return null;
    }

    private void writeTreeNetwork(String source, Uri destination) throws IOException {
        HttpURLConnection connection = (HttpURLConnection) new URL(source).openConnection();
        connection.setConnectTimeout(20000);
        connection.setReadTimeout(60000);
        connection.setRequestProperty("User-Agent", USER_AGENT);
        connection.setRequestProperty("Referer", "https://www.xiaohongshu.com/");
        connection.connect();
        int status = connection.getResponseCode();
        if (status < 200 || status >= 400) throw new IOException("媒体下载失败：HTTP " + status);
        try (InputStream input = connection.getInputStream();
             OutputStream output = context.getContentResolver().openOutputStream(destination, "w")) {
            if (output == null) throw new IOException("无法写入所选目录");
            byte[] buffer = new byte[128 * 1024];
            int count;
            while ((count = input.read(buffer)) >= 0) output.write(buffer, 0, count);
        } catch (IOException error) {
            try { DocumentsContract.deleteDocument(context.getContentResolver(), destination); }
            catch (Exception ignored) {}
            throw error;
        } finally {
            connection.disconnect();
        }
    }

    private void writeFromNetwork(String source, String name, String mime, String relative) throws IOException {
        HttpURLConnection connection = (HttpURLConnection) new URL(source).openConnection();
        connection.setConnectTimeout(20000);
        connection.setReadTimeout(60000);
        connection.setRequestProperty("User-Agent", USER_AGENT);
        connection.setRequestProperty("Referer", "https://www.xiaohongshu.com/");
        connection.connect();
        int status = connection.getResponseCode();
        if (status < 200 || status >= 400) throw new IOException("媒体下载失败：HTTP " + status);
        Uri destination = create(name, mime, relative);
        try (InputStream input = connection.getInputStream();
             OutputStream output = context.getContentResolver().openOutputStream(destination)) {
            if (output == null) throw new IOException("无法写入手机存储");
            byte[] buffer = new byte[128 * 1024];
            int count;
            while ((count = input.read(buffer)) >= 0) output.write(buffer, 0, count);
        } catch (IOException error) {
            context.getContentResolver().delete(destination, null, null);
            throw error;
        } finally {
            connection.disconnect();
        }
        publish(destination);
    }

    private void replaceText(String name, String text, String relative) throws IOException {
        deleteExisting(name, relative);
        Uri destination = create(name, "text/plain", relative);
        try (OutputStream output = context.getContentResolver().openOutputStream(destination)) {
            if (output == null) throw new IOException("无法写入文案文件");
            output.write(text.getBytes(StandardCharsets.UTF_8));
        } catch (IOException error) {
            context.getContentResolver().delete(destination, null, null);
            throw error;
        }
        publish(destination);
    }

    private Uri create(String name, String mime, String relative) throws IOException {
        ContentValues values = new ContentValues();
        values.put(MediaStore.Downloads.DISPLAY_NAME, name);
        values.put(MediaStore.Downloads.MIME_TYPE, mime);
        values.put(MediaStore.Downloads.RELATIVE_PATH, relative);
        values.put(MediaStore.Downloads.IS_PENDING, 1);
        Uri uri = context.getContentResolver().insert(MediaStore.Downloads.EXTERNAL_CONTENT_URI, values);
        if (uri == null) throw new IOException("系统拒绝创建下载文件");
        return uri;
    }

    private void publish(Uri uri) {
        ContentValues values = new ContentValues();
        values.put(MediaStore.Downloads.IS_PENDING, 0);
        context.getContentResolver().update(uri, values, null, null);
    }

    private boolean exists(String name, String relative) {
        ContentResolver resolver = context.getContentResolver();
        String selection = MediaStore.Downloads.DISPLAY_NAME + "=? AND " + MediaStore.Downloads.RELATIVE_PATH + "=?";
        try (Cursor cursor = resolver.query(MediaStore.Downloads.EXTERNAL_CONTENT_URI,
                new String[]{MediaStore.Downloads._ID}, selection, new String[]{name, relative}, null)) {
            return cursor != null && cursor.moveToFirst();
        }
    }

    private void deleteExisting(String name, String relative) {
        String selection = MediaStore.Downloads.DISPLAY_NAME + "=? AND " + MediaStore.Downloads.RELATIVE_PATH + "=?";
        context.getContentResolver().delete(MediaStore.Downloads.EXTERNAL_CONTENT_URI,
                selection, new String[]{name, relative});
    }

    private static String cleanFolder(String value) {
        String cleaned = value == null ? "" : value.replaceAll("[\\\\/:*?\"<>|\\p{Cntrl}]", "_").trim();
        return cleaned.isEmpty() ? "xhs-dl" : cleaned;
    }

    public interface Progress {
        void onMedia(int completed, int total);
    }
}
