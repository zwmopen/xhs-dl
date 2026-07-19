package com.zwmopen.xhsdl;

import android.app.Activity;
import android.app.AlertDialog;
import android.content.ClipData;
import android.content.ClipboardManager;
import android.content.Context;
import android.content.Intent;
import android.content.SharedPreferences;
import android.graphics.Color;
import android.graphics.Typeface;
import android.graphics.drawable.GradientDrawable;
import android.net.Uri;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.provider.Settings;
import android.text.Editable;
import android.text.TextWatcher;
import android.view.Gravity;
import android.view.View;
import android.view.WindowManager;
import android.widget.Button;
import android.widget.EditText;
import android.widget.LinearLayout;
import android.widget.ProgressBar;
import android.widget.ScrollView;
import android.widget.Spinner;
import android.widget.ArrayAdapter;
import android.widget.Switch;
import android.widget.TextView;
import android.widget.Toast;

import org.json.JSONArray;
import org.json.JSONObject;

import java.io.BufferedReader;
import java.io.InputStreamReader;
import java.net.HttpURLConnection;
import java.net.URL;
import java.util.ArrayList;
import java.util.List;
import java.util.Locale;
import java.util.Random;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

public final class MainActivity extends Activity {
    private int BG;
    private int SURFACE;
    private int SOFT;
    private int PRIMARY;
    private int ACCENT;
    private int TEXT;
    private int MUTED;
    private static final Pattern URL_PATTERN = Pattern.compile("https?://[^\\s<>\\\"，。；：！？、）】》]+", Pattern.CASE_INSENSITIVE);
    private static final String[] MODE_LABELS = {
            "自动判断（推荐）", "快速（3–8 秒）", "标准（8–15 秒）",
            "稳妥（35–55 秒）", "慢速（55–85 秒）", "极慢（110–160 秒）"
    };
    private static final String[] MODE_VALUES = {"auto", "fast", "normal", "cautious", "slow", "very-slow"};

    private final ExecutorService executor = Executors.newSingleThreadExecutor();
    private final Handler handler = new Handler(Looper.getMainLooper());
    private final Random random = new Random();
    private SharedPreferences preferences;
    private EditText input;
    private Button clipboardButton;
    private Button collectButton;
    private TextView statusTitle;
    private TextView statusDetail;
    private TextView results;
    private ProgressBar progress;
    private String clipboardText = "";
    private boolean running;
    private boolean resumed;

    @Override
    protected void onCreate(Bundle state) {
        super.onCreate(state);
        preferences = getSharedPreferences("settings", MODE_PRIVATE);
        applyPalette();
        getWindow().setStatusBarColor(BG);
        getWindow().setNavigationBarColor(BG);
        getWindow().getDecorView().setSystemUiVisibility(View.SYSTEM_UI_FLAG_LIGHT_STATUS_BAR);
        setContentView(buildUi());
        String draft = preferences.getString("theme_draft", "");
        if (!draft.isEmpty()) {
            input.setText(draft);
            input.setSelection(input.length());
            preferences.edit().remove("theme_draft").apply();
        }
        acceptShareIntent(getIntent());
        if (preferences.getBoolean("auto_update", true)) executor.execute(this::checkUpdate);
    }

    @Override
    protected void onNewIntent(Intent intent) {
        super.onNewIntent(intent);
        setIntent(intent);
        acceptShareIntent(intent);
    }

    @Override
    protected void onResume() {
        super.onResume();
        resumed = true;
        watchClipboard();
    }

    @Override
    protected void onPause() {
        resumed = false;
        super.onPause();
    }

    @Override
    protected void onDestroy() {
        executor.shutdownNow();
        super.onDestroy();
    }

    private View buildUi() {
        ScrollView scroll = new ScrollView(this);
        scroll.setFillViewport(true);
        scroll.setBackgroundColor(BG);
        LinearLayout root = column();
        root.setPadding(dp(22), dp(20), dp(22), dp(24));
        scroll.addView(root, matchWrap());

        LinearLayout header = row();
        LinearLayout brand = column();
        TextView title = text("小红书原图", 30, TEXT, true);
        title.setTypeface(Typeface.create("serif", Typeface.NORMAL));
        brand.addView(title);
        brand.addView(text("公开笔记 · 手机直存 · 无需登录", 12, MUTED, false));
        header.addView(brand, new LinearLayout.LayoutParams(0, -2, 1));
        String theme = preferences.getString("theme", "neo");
        Button themeButton = secondaryButton("neo".equals(theme) ? "克制玻璃" : "拟态悬浮");
        themeButton.setOnClickListener(v -> switchTheme());
        LinearLayout.LayoutParams themeParams = new LinearLayout.LayoutParams(dp(96), dp(46));
        themeParams.rightMargin = dp(8);
        header.addView(themeButton, themeParams);
        Button settingsButton = secondaryButton("⚙  设置");
        settingsButton.setOnClickListener(v -> showSettings());
        header.addView(settingsButton, new LinearLayout.LayoutParams(dp(106), dp(46)));
        root.addView(header, marginBottom(20));

        LinearLayout card = column();
        card.setPadding(dp(20), dp(20), dp(20), dp(20));
        card.setBackground(round(SURFACE, 24, Color.rgb(216, 224, 230), 1));
        card.addView(text("粘贴分享内容", 17, TEXT, true), marginBottom(10));
        input = new EditText(this);
        input.setTextSize(15);
        input.setTextColor(TEXT);
        input.setHintTextColor(MUTED);
        input.setHint("把小红书链接或整段分享文字粘贴到这里……");
        input.setGravity(Gravity.TOP | Gravity.START);
        input.setPadding(dp(16), dp(15), dp(16), dp(15));
        input.setMinHeight(dp(176));
        input.setBackground(round(Color.rgb(238, 243, 246), 16, Color.rgb(209, 219, 227), 1));
        input.addTextChangedListener(new TextWatcher() {
            public void beforeTextChanged(CharSequence s, int start, int count, int after) {}
            public void onTextChanged(CharSequence s, int start, int before, int count) { refreshDetection(); }
            public void afterTextChanged(Editable s) {}
        });
        card.addView(input, matchWrap());

        clipboardButton = accentButton("粘贴并采集");
        clipboardButton.setVisibility(View.GONE);
        clipboardButton.setOnClickListener(v -> {
            input.setText(clipboardText);
            input.setSelection(input.length());
            clipboardButton.setVisibility(View.GONE);
            startCollection();
        });
        card.addView(clipboardButton, marginTop(12));

        LinearLayout status = column();
        status.setPadding(dp(18), dp(17), dp(18), dp(17));
        status.setBackground(round(SOFT, 18, Color.TRANSPARENT, 0));
        status.addView(text("采集状态", 12, MUTED, true));
        statusTitle = text("等待开始", 23, TEXT, true);
        status.addView(statusTitle, marginTop(8));
        statusDetail = text("粘贴后自动识别条数和安全频率", 12, MUTED, false);
        status.addView(statusDetail, marginTop(5));
        progress = new ProgressBar(this, null, android.R.attr.progressBarStyleHorizontal);
        progress.setMax(100);
        progress.setProgress(0);
        status.addView(progress, marginTop(16));
        results = text("", 12, Color.rgb(64, 85, 101), false);
        results.setLineSpacing(0, 1.25f);
        status.addView(results, marginTop(12));
        card.addView(status, marginTop(16));

        collectButton = primaryButton("开始采集");
        collectButton.setOnClickListener(v -> startCollection());
        card.addView(collectButton, marginTop(16));

        LinearLayout secondary = row();
        Button open = secondaryButton("打开下载目录");
        open.setOnClickListener(v -> openDownloads());
        Button history = secondaryButton("历史记录");
        history.setOnClickListener(v -> showHistory());
        secondary.addView(open, new LinearLayout.LayoutParams(0, dp(48), 1));
        LinearLayout.LayoutParams historyParams = new LinearLayout.LayoutParams(0, dp(48), 1);
        historyParams.leftMargin = dp(10);
        secondary.addView(history, historyParams);
        card.addView(secondary, marginTop(12));
        root.addView(card, matchWrap());

        TextView footer = text("原始媒体直存 · 作者嵌入的署名会保留 · Android V1.0.0", 10, MUTED, false);
        footer.setGravity(Gravity.CENTER);
        root.addView(footer, marginTop(18));
        return scroll;
    }

    private void applyPalette() {
        if ("glass".equals(preferences.getString("theme", "neo"))) {
            BG = Color.rgb(223, 234, 242);
            SURFACE = Color.rgb(237, 244, 248);
            SOFT = Color.rgb(220, 234, 244);
            PRIMARY = Color.rgb(47, 111, 159);
            ACCENT = Color.rgb(75, 134, 172);
            TEXT = Color.rgb(16, 43, 69);
            MUTED = Color.rgb(97, 122, 145);
        } else {
            BG = Color.rgb(232, 237, 242);
            SURFACE = Color.rgb(247, 249, 250);
            SOFT = Color.rgb(233, 239, 243);
            PRIMARY = Color.rgb(32, 52, 66);
            ACCENT = Color.rgb(82, 122, 147);
            TEXT = Color.rgb(24, 38, 51);
            MUTED = Color.rgb(108, 127, 143);
        }
    }

    private void switchTheme() {
        if (running) return;
        String next = "neo".equals(preferences.getString("theme", "neo")) ? "glass" : "neo";
        preferences.edit()
                .putString("theme", next)
                .putString("theme_draft", input.getText().toString())
                .apply();
        recreate();
    }

    private void startCollection() {
        if (running) return;
        List<String> urls = extractUrls(input.getText().toString());
        if (urls.isEmpty()) {
            Toast.makeText(this, "没有识别到小红书链接", Toast.LENGTH_SHORT).show();
            return;
        }
        running = true;
        collectButton.setEnabled(false);
        collectButton.setText("采集中");
        clipboardButton.setVisibility(View.GONE);
        results.setText("");
        progress.setProgress(0);
        String configured = preferences.getString("mode", "auto");
        String selected = "auto".equals(configured) ? automaticMode(urls.size()) : configured;
        statusTitle.setText("正在准备");
        statusDetail.setText("共 " + urls.size() + " 条 · " + modeDescription(selected, urls.size()));
        getWindow().addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON);
        executor.execute(() -> collectAll(urls, selected));
    }

    private void collectAll(List<String> urls, String mode) {
        int success = 0;
        int failed = 0;
        StringBuilder lines = new StringBuilder();
        XhsParser parser = new XhsParser();
        MediaSaver saver = new MediaSaver(this);
        HistoryStore history = new HistoryStore(this);
        String rootFolder = preferences.getString("folder", "xhs-dl");
        for (int i = 0; i < urls.size(); i++) {
            int index = i;
            String url = urls.get(i);
            try {
                postStatus("正在解析第 " + (i + 1) + " 条", url, percent(i, urls.size()));
                NoteData note = parser.fetch(url);
                saver.save(note, rootFolder, (done, total) ->
                        postStatus("正在保存 · " + note.title,
                                "媒体 " + done + " / " + total, percent(index, urls.size())));
                history.add(note);
                success++;
                if (lines.length() > 0) lines.append("\n\n");
                lines.append(i + 1).append('/').append(urls.size()).append("  完成  ").append(note.title);
            } catch (Exception error) {
                failed++;
                if (lines.length() > 0) lines.append("\n\n");
                lines.append(i + 1).append('/').append(urls.size()).append("  失败  ").append(cleanError(error));
            }
            String shown = lines.toString();
            int progressValue = percent(i + 1, urls.size());
            handler.post(() -> {
                results.setText(shown);
                progress.setProgress(progressValue);
            });
            if (i < urls.size() - 1) {
                long wait = randomDelay(mode);
                postStatus("安全等待中", "下一条将在约 " + (wait / 1000) + " 秒后开始", progressValue);
                try { Thread.sleep(wait); } catch (InterruptedException interrupted) {
                    Thread.currentThread().interrupt();
                    break;
                }
            }
        }
        int finalSuccess = success;
        int finalFailed = failed;
        handler.post(() -> finish(finalSuccess, finalFailed));
    }

    private void finish(int success, int failed) {
        running = false;
        collectButton.setEnabled(true);
        collectButton.setText("继续采集");
        statusTitle.setText(failed == 0 ? "全部保存完成" : "任务完成");
        statusDetail.setText("成功 " + success + " 条，失败 " + failed + " 条");
        progress.setProgress(100);
        getWindow().clearFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON);
        watchClipboard();
    }

    private void refreshDetection() {
        if (running || statusTitle == null) return;
        int count = extractUrls(input.getText().toString()).size();
        if (count == 0) {
            statusTitle.setText("等待开始");
            statusDetail.setText("还没有识别到小红书链接");
            return;
        }
        String configured = preferences.getString("mode", "auto");
        String mode = "auto".equals(configured) ? automaticMode(count) : configured;
        statusTitle.setText("已识别 " + count + " 条");
        statusDetail.setText(("auto".equals(configured) ? "自动使用：" : "手动使用：") + modeDescription(mode, count));
    }

    private void watchClipboard() {
        if (!resumed) return;
        try {
            ClipboardManager manager = (ClipboardManager) getSystemService(CLIPBOARD_SERVICE);
            ClipData clip = manager.getPrimaryClip();
            if (clip != null && clip.getItemCount() > 0) {
                CharSequence value = clip.getItemAt(0).coerceToText(this);
                String text = value == null ? "" : value.toString().trim();
                if (!extractUrls(text).isEmpty() && !text.equals(input.getText().toString().trim()) && !running) {
                    clipboardText = text;
                    clipboardButton.setVisibility(View.VISIBLE);
                } else if (!running) clipboardButton.setVisibility(View.GONE);
            }
        } catch (Exception ignored) {
        }
        handler.postDelayed(this::watchClipboard, 1200);
    }

    private void acceptShareIntent(Intent intent) {
        if (intent == null || !Intent.ACTION_SEND.equals(intent.getAction())) return;
        String shared = intent.getStringExtra(Intent.EXTRA_TEXT);
        if (shared != null && !shared.trim().isEmpty()) {
            input.setText(shared);
            input.setSelection(input.length());
        }
    }

    private void showSettings() {
        LinearLayout layout = column();
        layout.setPadding(dp(22), dp(8), dp(22), 0);
        layout.addView(text("自动判断会根据条数选择随机间隔，也可以手动覆盖。", 12, MUTED, false), marginBottom(12));
        Spinner spinner = new Spinner(this);
        spinner.setAdapter(new ArrayAdapter<>(this, android.R.layout.simple_spinner_dropdown_item, MODE_LABELS));
        spinner.setBackground(round(SOFT, 12, ACCENT, 1));
        String current = preferences.getString("mode", "auto");
        int selected = 0;
        for (int i = 0; i < MODE_VALUES.length; i++) if (MODE_VALUES[i].equals(current)) selected = i;
        spinner.setSelection(selected);
        layout.addView(spinner, matchWrap());
        EditText folder = new EditText(this);
        folder.setHint("Download 下的文件夹名称");
        folder.setTextColor(TEXT);
        folder.setHintTextColor(MUTED);
        folder.setPadding(dp(14), dp(10), dp(14), dp(10));
        folder.setBackground(round(SOFT, 12, ACCENT, 1));
        folder.setText(preferences.getString("folder", "xhs-dl"));
        layout.addView(folder, marginTop(12));
        Switch updates = new Switch(this);
        updates.setText("启动时检测安卓新版本");
        updates.setTextColor(TEXT);
        updates.setChecked(preferences.getBoolean("auto_update", true));
        layout.addView(updates, marginTop(10));
        AlertDialog dialog = new AlertDialog.Builder(this)
                .setTitle("采集设置")
                .setView(layout)
                .setNegativeButton("取消", null)
                .setPositiveButton("保存", (ignoredDialog, which) -> {
                    preferences.edit()
                            .putString("mode", MODE_VALUES[spinner.getSelectedItemPosition()])
                            .putString("folder", folder.getText().toString().trim().isEmpty() ? "xhs-dl" : folder.getText().toString().trim())
                            .putBoolean("auto_update", updates.isChecked())
                            .apply();
                    refreshDetection();
                }).create();
        presentDialog(dialog);
    }

    private void showHistory() {
        JSONArray items = new HistoryStore(this).read();
        StringBuilder text = new StringBuilder();
        int start = Math.max(0, items.length() - 30);
        for (int i = items.length() - 1; i >= start; i--) {
            JSONObject item = items.optJSONObject(i);
            if (item == null) continue;
            if (text.length() > 0) text.append("\n\n");
            text.append(item.optString("标题", "未命名")).append("\n").append(item.optString("笔记ID"));
        }
        AlertDialog dialog = new AlertDialog.Builder(this).setTitle("历史记录 · " + items.length() + " 条")
                .setMessage(text.length() == 0 ? "还没有成功记录" : text.toString())
                .setPositiveButton("关闭", null).create();
        presentDialog(dialog);
    }

    private void openDownloads() {
        try {
            Intent intent = new Intent(Intent.ACTION_OPEN_DOCUMENT_TREE);
            startActivity(intent);
            Toast.makeText(this, "文件位于 Download/" + preferences.getString("folder", "xhs-dl"), Toast.LENGTH_LONG).show();
        } catch (Exception error) {
            Toast.makeText(this, "请在文件管理中打开 Download/" + preferences.getString("folder", "xhs-dl"), Toast.LENGTH_LONG).show();
        }
    }

    private void checkUpdate() {
        try {
            HttpURLConnection connection = (HttpURLConnection) new URL("https://api.github.com/repos/zwmopen/xhs-dl/releases?per_page=20").openConnection();
            connection.setConnectTimeout(6000);
            connection.setReadTimeout(6000);
            connection.setRequestProperty("User-Agent", "xhs-dl-android");
            StringBuilder body = new StringBuilder();
            try (BufferedReader reader = new BufferedReader(new InputStreamReader(connection.getInputStream()))) {
                String line;
                while ((line = reader.readLine()) != null) body.append(line);
            }
            JSONArray releases = new JSONArray(body.toString());
            for (int i = 0; i < releases.length(); i++) {
                JSONObject release = releases.optJSONObject(i);
                if (release == null) continue;
                String tag = release.optString("tag_name");
                if (!tag.startsWith("android-v")) continue;
                if (compareVersion(tag.substring("android-v".length()), "1.0.0") > 0) {
                    String page = release.optString("html_url");
                    handler.post(() -> {
                        AlertDialog dialog = new AlertDialog.Builder(this).setTitle("发现安卓新版本 " + tag)
                            .setMessage("是否打开正式发布页？")
                            .setNegativeButton("稍后", null)
                            .setPositiveButton("打开", (d, w) -> startActivity(new Intent(Intent.ACTION_VIEW, Uri.parse(page)))).create();
                        presentDialog(dialog);
                    });
                }
                break;
            }
        } catch (Exception ignored) {
        }
    }

    private static int compareVersion(String left, String right) {
        String[] a = left.split("\\.");
        String[] b = right.split("\\.");
        for (int i = 0; i < Math.max(a.length, b.length); i++) {
            int x = i < a.length ? number(a[i]) : 0;
            int y = i < b.length ? number(b[i]) : 0;
            if (x != y) return Integer.compare(x, y);
        }
        return 0;
    }

    private static int number(String value) {
        try { return Integer.parseInt(value.replaceAll("\\D", "")); }
        catch (Exception ignored) { return 0; }
    }

    private void presentDialog(AlertDialog dialog) {
        dialog.setOnShowListener(ignored -> {
            if (dialog.getWindow() != null) {
                dialog.getWindow().setBackgroundDrawable(round(SURFACE, 22, ACCENT, 1));
            }
            Button positive = dialog.getButton(AlertDialog.BUTTON_POSITIVE);
            Button negative = dialog.getButton(AlertDialog.BUTTON_NEGATIVE);
            if (positive != null) positive.setTextColor(ACCENT);
            if (negative != null) negative.setTextColor(MUTED);
            TextView title = dialog.findViewById(getResources().getIdentifier("alertTitle", "id", "android"));
            if (title != null) title.setTextColor(TEXT);
            TextView message = dialog.findViewById(android.R.id.message);
            if (message != null) message.setTextColor(TEXT);
        });
        dialog.show();
    }

    private static String automaticMode(int count) {
        if (count <= 20) return "cautious";
        if (count <= 50) return "slow";
        return "very-slow";
    }

    private static String modeDescription(String mode, int count) {
        if (count <= 1) return "单条直接采集";
        switch (mode) {
            case "fast": return "快速 3–8 秒";
            case "normal": return "标准 8–15 秒";
            case "slow": return "慢速 55–85 秒";
            case "very-slow": return "极慢 110–160 秒";
            default: return "稳妥 35–55 秒";
        }
    }

    private long randomDelay(String mode) {
        int min;
        int max;
        switch (mode) {
            case "fast": min = 3; max = 8; break;
            case "normal": min = 8; max = 15; break;
            case "slow": min = 55; max = 85; break;
            case "very-slow": min = 110; max = 160; break;
            default: min = 35; max = 55;
        }
        return (min + random.nextInt(max - min + 1)) * 1000L;
    }

    private static List<String> extractUrls(String text) {
        List<String> result = new ArrayList<>();
        Matcher matcher = URL_PATTERN.matcher(text == null ? "" : text);
        while (matcher.find()) {
            String value = matcher.group().replaceAll("[.,;:!?()]+$", "");
            if (!result.contains(value)) result.add(value);
        }
        return result;
    }

    private void postStatus(String title, String detail, int value) {
        handler.post(() -> {
            statusTitle.setText(title);
            statusDetail.setText(detail);
            progress.setProgress(value);
        });
    }

    private static int percent(int done, int total) { return total == 0 ? 0 : Math.round(done * 100f / total); }
    private static String cleanError(Exception error) {
        String value = error.getMessage();
        return value == null || value.trim().isEmpty() ? error.getClass().getSimpleName() : value;
    }

    private LinearLayout column() { LinearLayout value = new LinearLayout(this); value.setOrientation(LinearLayout.VERTICAL); return value; }
    private LinearLayout row() { LinearLayout value = new LinearLayout(this); value.setOrientation(LinearLayout.HORIZONTAL); value.setGravity(Gravity.CENTER_VERTICAL); return value; }
    private TextView text(String value, int size, int color, boolean bold) { TextView view = new TextView(this); view.setText(value); view.setTextSize(size); view.setTextColor(color); if (bold) view.setTypeface(Typeface.DEFAULT, Typeface.BOLD); return view; }
    private Button primaryButton(String label) { Button button = new Button(this); button.setText(label); button.setTextColor(Color.WHITE); button.setTextSize(15); button.setTypeface(Typeface.DEFAULT, Typeface.BOLD); button.setAllCaps(false); button.setBackground(round(PRIMARY, 15, Color.TRANSPARENT, 0)); return button; }
    private Button accentButton(String label) { Button button = primaryButton(label); button.setBackground(round(ACCENT, 14, Color.TRANSPARENT, 0)); return button; }
    private Button secondaryButton(String label) { Button button = new Button(this); button.setText(label); button.setTextColor(Color.rgb(46, 70, 87)); button.setTextSize(13); button.setTypeface(Typeface.DEFAULT, Typeface.BOLD); button.setAllCaps(false); button.setBackground(round(Color.rgb(220, 229, 235), 13, Color.TRANSPARENT, 0)); return button; }
    private GradientDrawable round(int color, int radius, int stroke, int strokeWidth) { GradientDrawable d = new GradientDrawable(); d.setColor(color); d.setCornerRadius(dp(radius)); if (strokeWidth > 0) d.setStroke(dp(strokeWidth), stroke); return d; }
    private int dp(int value) { return Math.round(value * getResources().getDisplayMetrics().density); }
    private LinearLayout.LayoutParams matchWrap() { return new LinearLayout.LayoutParams(-1, -2); }
    private LinearLayout.LayoutParams marginTop(int value) { LinearLayout.LayoutParams p = matchWrap(); p.topMargin = dp(value); return p; }
    private LinearLayout.LayoutParams marginBottom(int value) { LinearLayout.LayoutParams p = matchWrap(); p.bottomMargin = dp(value); return p; }
}
