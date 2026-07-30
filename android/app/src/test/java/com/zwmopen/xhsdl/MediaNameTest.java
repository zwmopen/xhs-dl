package com.zwmopen.xhsdl;

import static org.junit.Assert.assertEquals;

import org.junit.Test;

public final class MediaNameTest {
    @Test
    public void imagesUseCoverAndInnerPageNames() {
        NoteData note = new NoteData();
        note.title = "标题/测试";
        NoteData.MediaItem item = new NoteData.MediaItem("https://example/a", "webp", "image/webp");
        note.media.add(item);
        note.media.add(item);

        assertEquals("封面-标题_测试.jpg", note.mediaFileName(0, item));
        assertEquals("内页1-标题_测试.jpg", note.mediaFileName(1, item));
    }

    @Test
    public void videoUsesVideoName() {
        NoteData note = new NoteData();
        note.title = "演出第一场";
        NoteData.MediaItem item = new NoteData.MediaItem("https://example/v", "mp4", "video/mp4");
        note.media.add(item);

        assertEquals("视频-演出第一场.mp4", note.mediaFileName(0, item));
    }

    @Test
    public void mixedMediaNumbersImagesAndVideosSeparately() {
        NoteData note = new NoteData();
        note.title = "混合媒体";
        NoteData.MediaItem video1 = new NoteData.MediaItem("https://example/v1", "mp4", "video/mp4");
        NoteData.MediaItem cover = new NoteData.MediaItem("https://example/a", "webp", "image/webp");
        NoteData.MediaItem video2 = new NoteData.MediaItem("https://example/v2", "mp4", "video/mp4");
        note.media.add(video1);
        note.media.add(cover);
        note.media.add(video2);

        assertEquals("视频-混合媒体.mp4", note.mediaFileName(0, video1));
        assertEquals("封面-混合媒体.jpg", note.mediaFileName(1, cover));
        assertEquals("视频2-混合媒体.mp4", note.mediaFileName(2, video2));
    }
}
