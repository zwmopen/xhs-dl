package com.zwmopen.xhsdl;

import static org.junit.Assert.assertEquals;

import org.junit.Test;

public final class MediaNameTest {
    @Test
    public void imagesUseCoverAndInnerPageNames() {
        NoteData note = new NoteData();
        note.title = "标题/测试";
        NoteData.MediaItem item = new NoteData.MediaItem("https://example/a", "webp", "image/webp");

        assertEquals("封面-标题_测试.jpg", note.mediaFileName(0, item));
        assertEquals("内页1-标题_测试.jpg", note.mediaFileName(1, item));
    }

    @Test
    public void videoUsesVideoName() {
        NoteData note = new NoteData();
        note.title = "演出第一场";
        NoteData.MediaItem item = new NoteData.MediaItem("https://example/v", "mp4", "video/mp4");

        assertEquals("视频-演出第一场.mp4", note.mediaFileName(0, item));
    }
}
