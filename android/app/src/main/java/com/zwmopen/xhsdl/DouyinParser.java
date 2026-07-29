package com.zwmopen.xhsdl;

import android.app.Activity;
import android.graphics.Color;
import android.os.Handler;
import android.os.Looper;
import android.view.ViewGroup;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.widget.FrameLayout;

import org.json.JSONArray;
import org.json.JSONObject;

import java.io.IOException;
import java.util.HashSet;
import java.util.Set;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicBoolean;
import java.util.concurrent.atomic.AtomicReference;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

public final class DouyinParser {
    private static final String DESKTOP_UA =
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            + "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36";
    private static final Pattern ID_PATTERN = Pattern.compile("/(?:note|video)/(\\d+)");
    private static final Pattern TOPIC_PATTERN = Pattern.compile("#([^\\s#]+)");
    private static final String SCRIPT =
            "(function(){"
            + "var main=document.querySelector('main')||document.body;"
            + "var current=location.href,isNote=/\\\\/note\\\\//.test(current);"
            + "var text=main.innerText||'',meta=(document.querySelector('meta[name=\"description\"]')||{}).content||'';"
            + "var title=(document.title||'').replace(/\\\\s*-\\\\s*抖音\\\\s*$/,'').trim(),author='';"
            + "document.querySelectorAll('script[type=\"application/ld+json\"]').forEach(function(n){"
            + "try{var v=JSON.parse(n.textContent||'{}'),a=(v.itemListElement||[]).filter(function(x){return Number(x.position)===2})[0];"
            + "if(!author&&a&&a.name)author=String(a.name)}catch(e){}});"
            + "if(!author&&meta.indexOf(' - ')>=0){var m=meta.split(' - ').slice(1).join(' - ').match(/^(.*?)于\\\\d{8}发布/);author=m?m[1]:''}"
            + "if(author&&meta.indexOf(' - '+author+'于')>=0)title=meta.split(' - '+author+'于',1)[0].trim()||title;"
            + "function read(s){var n=main.querySelector(s);return n?(n.innerText||n.textContent||'').trim():''}"
            + "var media=[],seen={};"
            + "if(isNote){main.querySelectorAll('img').forEach(function(n){var u=n.currentSrc||n.src||'';"
            + "if(u.indexOf('aweme-images')<0||seen[u])return;seen[u]=1;"
            + "media.push({url:u,kind:'image',extension:u.indexOf('.png')>=0?'png':(u.indexOf('.jpeg')>=0||u.indexOf('.jpg')>=0?'jpg':'webp')})})}"
            + "else{main.querySelectorAll('video,video source').forEach(function(n){var u=n.currentSrc||n.src||'';"
            + "if(!/^https?:/.test(u)||seen[u])return;seen[u]=1;media.push({url:u,kind:'video',extension:'mp4'})})}"
            + "var published=(text.match(/发布时间[：:]\\\\s*([^\\\\n]+)/)||[])[1]||'';"
            + "return JSON.stringify({final_url:current,title:title,author:author,"
            + "likes:read('[data-e2e=\"video-player-digg\"]')||'未知',"
            + "comments:read('[data-e2e=\"feed-comment-icon\"]')||(text.match(/评论\\\\(([^)]+)\\\\)/)||[])[1]||'未知',"
            + "favorites:read('[data-e2e=\"video-player-collect\"]')||'未知',"
            + "shares:read('[data-e2e=\"video-player-share\"]')||'未知',"
            + "published_at:published.trim(),media:media});"
            + "})()";

    public NoteData fetch(Activity activity, String sourceUrl) throws Exception {
        CountDownLatch latch = new CountDownLatch(1);
        AtomicReference<JSONObject> payload = new AtomicReference<>();
        AtomicReference<Exception> failure = new AtomicReference<>();
        AtomicBoolean finished = new AtomicBoolean(false);
        Handler main = new Handler(Looper.getMainLooper());
        AtomicReference<WebView> webViewRef = new AtomicReference<>();
        AtomicReference<FrameLayout> holderRef = new AtomicReference<>();

        main.post(() -> {
            FrameLayout holder = new FrameLayout(activity);
            holder.setAlpha(0.01f);
            FrameLayout.LayoutParams tiny = new FrameLayout.LayoutParams(2, 2);
            activity.addContentView(holder, tiny);
            holderRef.set(holder);

            WebView webView = new WebView(activity);
            webViewRef.set(webView);
            holder.addView(webView, new FrameLayout.LayoutParams(2, 2));
            WebSettings settings = webView.getSettings();
            settings.setJavaScriptEnabled(true);
            settings.setDomStorageEnabled(true);
            settings.setLoadsImagesAutomatically(true);
            settings.setUserAgentString(DESKTOP_UA);
            webView.setBackgroundColor(Color.TRANSPARENT);
            webView.setWebViewClient(new WebViewClient() {
                @Override
                public void onPageFinished(WebView view, String url) {
                    poll(view, 0, finished, payload, failure, latch);
                }
            });
            webView.loadUrl(sourceUrl);
        });

        if (!latch.await(55, TimeUnit.SECONDS)) {
            failure.compareAndSet(null, new IOException("抖音公开页面加载超时，请稍后重试"));
        }
        finished.set(true);
        main.post(() -> {
            WebView webView = webViewRef.get();
            if (webView != null) {
                webView.stopLoading();
                webView.destroy();
            }
            FrameLayout holder = holderRef.get();
            if (holder != null && holder.getParent() instanceof ViewGroup) {
                ((ViewGroup) holder.getParent()).removeView(holder);
            }
        });
        if (failure.get() != null) throw failure.get();
        if (payload.get() == null) throw new IOException("抖音公开页面没有返回作品数据");
        return parse(sourceUrl, payload.get());
    }

    private void poll(WebView view, int attempt, AtomicBoolean finished,
                      AtomicReference<JSONObject> payload, AtomicReference<Exception> failure,
                      CountDownLatch latch) {
        if (finished.get()) return;
        view.evaluateJavascript(SCRIPT, raw -> {
            try {
                String json = new JSONArray("[" + raw + "]").getString(0);
                JSONObject value = new JSONObject(json);
                if (value.optJSONArray("media") != null
                        && value.optJSONArray("media").length() > 0) {
                    payload.set(value);
                    if (finished.compareAndSet(false, true)) latch.countDown();
                    return;
                }
            } catch (Exception ignored) {
            }
            if (attempt >= 35) {
                failure.set(new IOException("抖音公开页面已打开，但没有取得当前作品媒体"));
                if (finished.compareAndSet(false, true)) latch.countDown();
            } else {
                view.postDelayed(() -> poll(view, attempt + 1, finished, payload, failure, latch), 1000);
            }
        });
    }

    private NoteData parse(String sourceUrl, JSONObject payload) throws Exception {
        NoteData note = new NoteData();
        note.sourceUrl = sourceUrl;
        note.referer = "https://www.douyin.com/";
        note.title = payload.optString("title");
        note.description = note.title;
        note.author = payload.optString("author");
        note.likes = payload.optString("likes", "未知");
        note.comments = payload.optString("comments", "未知");
        Matcher id = ID_PATTERN.matcher(payload.optString("final_url"));
        if (id.find()) note.noteId = id.group(1);
        Matcher topics = TOPIC_PATTERN.matcher(note.title);
        Set<String> seenTopics = new HashSet<>();
        while (topics.find()) {
            String topic = topics.group(1);
            if (seenTopics.add(topic)) note.topics.add(topic);
        }
        JSONArray media = payload.optJSONArray("media");
        if (media != null) {
            for (int i = 0; i < media.length(); i++) {
                JSONObject item = media.optJSONObject(i);
                if (item == null || item.optString("url").isEmpty()) continue;
                String extension = item.optString("extension", "webp");
                String mime = "mp4".equals(extension) ? "video/mp4"
                        : "png".equals(extension) ? "image/png"
                        : "jpg".equals(extension) ? "image/jpeg" : "image/webp";
                note.media.add(new NoteData.MediaItem(item.optString("url"), extension, mime));
            }
        }
        if (note.media.isEmpty()) throw new IOException("没有找到抖音原始媒体");
        return note;
    }
}
