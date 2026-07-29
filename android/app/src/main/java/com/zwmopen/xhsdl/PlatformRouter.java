package com.zwmopen.xhsdl;

import java.net.URI;

public final class PlatformRouter {
    private PlatformRouter() {}

    public static String detect(String value) {
        if (value == null) return "unknown";
        String host;
        try {
            host = URI.create(value).getHost();
        } catch (Exception ignored) {
            return "unknown";
        }
        if (host == null) return "unknown";
        host = host.toLowerCase();
        if (host.equals("v.douyin.com") || host.equals("douyin.com")
                || host.equals("www.douyin.com") || host.equals("iesdouyin.com")
                || host.equals("www.iesdouyin.com")) return "douyin";
        if (host.equals("xhslink.com") || host.equals("www.xhslink.com")
                || host.equals("xiaohongshu.com") || host.equals("www.xiaohongshu.com")
                || host.equals("xiaohongshu.cn") || host.equals("www.xiaohongshu.cn")
                || host.equals("rednote.com") || host.equals("www.rednote.com")) return "xhs";
        return "unknown";
    }
}
