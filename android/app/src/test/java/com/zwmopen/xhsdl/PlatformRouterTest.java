package com.zwmopen.xhsdl;

import org.junit.Test;

import static org.junit.Assert.assertEquals;

public final class PlatformRouterTest {
    @Test
    public void detectsXhsAndDouyinShareLinks() {
        assertEquals("douyin", PlatformRouter.detect("https://v.douyin.com/VFppn9c-lds/"));
        assertEquals("douyin", PlatformRouter.detect("https://www.douyin.com/note/7663398572494336177"));
        assertEquals("xhs", PlatformRouter.detect("https://xhslink.com/o/70dt8TsFJon"));
        assertEquals("unknown", PlatformRouter.detect("https://example.com/file"));
    }
}
