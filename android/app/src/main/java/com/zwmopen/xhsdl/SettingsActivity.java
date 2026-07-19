package com.zwmopen.xhsdl;

import android.app.Activity;
import android.app.AlertDialog;
import android.content.Intent;
import android.content.SharedPreferences;
import android.database.Cursor;
import android.graphics.Color;
import android.graphics.Typeface;
import android.graphics.drawable.GradientDrawable;
import android.net.Uri;
import android.os.Bundle;
import android.provider.DocumentsContract;
import android.view.Gravity;
import android.view.View;
import android.widget.ArrayAdapter;
import android.widget.Button;
import android.widget.EditText;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.Spinner;
import android.widget.Switch;
import android.widget.TextView;
import android.widget.Toast;

import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

public final class SettingsActivity extends Activity {
    private static final int PICK_FOLDER = 41;
    private static final String[] MODE_LABELS = {
            "自动判断（推荐）", "快速（3–8 秒）", "标准（8–15 秒）",
            "稳妥（35–55 秒）", "慢速（55–85 秒）", "极慢（110–160 秒）"
    };
    private static final String[] MODE_VALUES = {"auto", "fast", "normal", "cautious", "slow", "very-slow"};

    private final ExecutorService executor = Executors.newSingleThreadExecutor();
    private SharedPreferences preferences;
    private int bg;
    private int surface;
    private int soft;
    private int primary;
    private int accent;
    private int text;
    private int muted;
    private Spinner modeSpinner;
    private EditText defaultFolder;
    private Switch automaticUpdates;
    private TextView customFolderLabel;
    private Button updateButton;

    @Override
    protected void onCreate(Bundle state) {
        super.onCreate(state);
        preferences = getSharedPreferences("settings", MODE_PRIVATE);
        applyPalette();
        getWindow().setStatusBarColor(bg);
        getWindow().setNavigationBarColor(bg);
        getWindow().getDecorView().setSystemUiVisibility(View.SYSTEM_UI_FLAG_LIGHT_STATUS_BAR);
        setContentView(buildUi());
    }

    @Override
    protected void onDestroy() {
        executor.shutdownNow();
        super.onDestroy();
    }

    private View buildUi() {
        ScrollView scroll = new ScrollView(this);
        scroll.setFillViewport(true);
        scroll.setBackgroundColor(bg);
        LinearLayout root = column();
        root.setPadding(dp(22), dp(18), dp(22), dp(34));
        scroll.addView(root, matchWrap());

        LinearLayout header = row();
        Button back = quietButton("‹");
        back.setTextSize(28);
        back.setOnClickListener(v -> finish());
        header.addView(back, new LinearLayout.LayoutParams(dp(52), dp(48)));
        LinearLayout titles = column();
        titles.setPadding(dp(12), 0, 0, 0);
        titles.addView(label("设置与帮助", 26, text, true));
        titles.addView(label("红薯下载 · Android V" + BuildConfig.VERSION_NAME, 12, muted, false));
        header.addView(titles, new LinearLayout.LayoutParams(0, -2, 1));
        root.addView(header, bottom(18));

        LinearLayout storage = section("保存位置与速度", "默认保存在系统 Download/红薯下载，也可以授权其他文件夹。", root);
        modeSpinner = new Spinner(this);
        modeSpinner.setAdapter(new ArrayAdapter<>(this, android.R.layout.simple_spinner_dropdown_item, MODE_LABELS));
        modeSpinner.setBackground(round(soft, 13, accent, 1));
        String currentMode = preferences.getString("mode", "auto");
        for (int i = 0; i < MODE_VALUES.length; i++) if (MODE_VALUES[i].equals(currentMode)) modeSpinner.setSelection(i);
        storage.addView(modeSpinner, top(14));

        defaultFolder = new EditText(this);
        defaultFolder.setText(preferences.getString("folder", "红薯下载"));
        defaultFolder.setHint("Download 下的默认文件夹名称");
        defaultFolder.setTextColor(text);
        defaultFolder.setHintTextColor(muted);
        defaultFolder.setPadding(dp(14), dp(11), dp(14), dp(11));
        defaultFolder.setBackground(round(soft, 13, accent, 1));
        storage.addView(defaultFolder, top(12));

        customFolderLabel = label(folderSummary(), 12, muted, false);
        storage.addView(customFolderLabel, top(12));
        Button choose = secondaryButton("选择其他下载目录");
        choose.setOnClickListener(v -> chooseFolder());
        storage.addView(choose, top(8));
        Button clear = quietButton("恢复默认 Download 目录");
        clear.setOnClickListener(v -> {
            preferences.edit().remove("download_tree_uri").remove("download_tree_name").apply();
            customFolderLabel.setText(folderSummary());
        });
        storage.addView(clear, top(8));

        automaticUpdates = new Switch(this);
        automaticUpdates.setText("启动时自动检测新版本");
        automaticUpdates.setTextColor(text);
        automaticUpdates.setChecked(preferences.getBoolean("auto_update", true));
        storage.addView(automaticUpdates, top(14));
        Button save = primaryButton("保存设置");
        save.setOnClickListener(v -> saveSettings());
        storage.addView(save, top(14));

        LinearLayout about = section("关于红薯下载", "本地优先的公开笔记原图保存工具，不要求小红书账号，不把链接交给第三方解析站。", root);
        about.addView(infoRow("设计思路", "内容清楚、操作克制；默认拟态悬浮，备用克制玻璃；下载结果与历史留在你的设备。"), top(12));
        Button guide = secondaryButton("使用说明与安全边界");
        guide.setOnClickListener(v -> showGuide());
        about.addView(guide, top(14));
        updateButton = secondaryButton("检测更新安装包");
        updateButton.setOnClickListener(v -> checkUpdate());
        about.addView(updateButton, top(10));
        Button repository = quietButton("打开项目与历史版本");
        repository.setOnClickListener(v -> openUrl("https://github.com/zwmopen/xhs-dl"));
        about.addView(repository, top(8));

        TextView footer = label("设置只保存在本机 · 不做云同步", 11, muted, false);
        footer.setGravity(Gravity.CENTER);
        root.addView(footer, top(20));
        return scroll;
    }

    private LinearLayout section(String title, String description, LinearLayout root) {
        LinearLayout card = column();
        card.setPadding(dp(18), dp(18), dp(18), dp(18));
        card.setElevation(dp(3));
        card.setBackground(round(surface, 22, Color.argb(48, 82, 122, 147), 1));
        card.addView(label(title, 18, text, true));
        TextView detail = label(description, 12, muted, false);
        detail.setLineSpacing(0, 1.18f);
        card.addView(detail, top(6));
        root.addView(card, bottom(16));
        return card;
    }

    private LinearLayout infoRow(String title, String description) {
        LinearLayout value = column();
        value.setPadding(dp(14), dp(13), dp(14), dp(13));
        value.setBackground(round(soft, 14, Color.TRANSPARENT, 0));
        value.addView(label(title, 13, text, true));
        TextView detail = label(description, 12, muted, false);
        detail.setLineSpacing(0, 1.18f);
        value.addView(detail, top(4));
        return value;
    }

    private void chooseFolder() {
        Intent intent = new Intent(Intent.ACTION_OPEN_DOCUMENT_TREE);
        intent.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION | Intent.FLAG_GRANT_WRITE_URI_PERMISSION |
                Intent.FLAG_GRANT_PERSISTABLE_URI_PERMISSION | Intent.FLAG_GRANT_PREFIX_URI_PERMISSION);
        startActivityForResult(intent, PICK_FOLDER);
    }

    @Override
    protected void onActivityResult(int requestCode, int resultCode, Intent data) {
        super.onActivityResult(requestCode, resultCode, data);
        if (requestCode != PICK_FOLDER || resultCode != RESULT_OK || data == null || data.getData() == null) return;
        Uri uri = data.getData();
        int flags = data.getFlags() & (Intent.FLAG_GRANT_READ_URI_PERMISSION | Intent.FLAG_GRANT_WRITE_URI_PERMISSION);
        try {
            getContentResolver().takePersistableUriPermission(uri, flags);
            preferences.edit()
                    .putString("download_tree_uri", uri.toString())
                    .putString("download_tree_name", displayName(uri))
                    .apply();
            customFolderLabel.setText(folderSummary());
        } catch (Exception error) {
            Toast.makeText(this, "没有取得这个文件夹的长期写入权限", Toast.LENGTH_LONG).show();
        }
    }

    private String displayName(Uri uri) {
        try (Cursor cursor = getContentResolver().query(uri, new String[]{DocumentsContract.Document.COLUMN_DISPLAY_NAME}, null, null, null)) {
            if (cursor != null && cursor.moveToFirst()) return cursor.getString(0);
        } catch (Exception ignored) {}
        return "已选择的文件夹";
    }

    private String folderSummary() {
        String uri = preferences.getString("download_tree_uri", "");
        if (!uri.isEmpty()) return "当前：" + preferences.getString("download_tree_name", "自定义文件夹") + "（系统已授权）";
        return "当前：Download/" + preferences.getString("folder", "红薯下载");
    }

    private void saveSettings() {
        String folder = defaultFolder.getText().toString().trim();
        preferences.edit()
                .putString("mode", MODE_VALUES[modeSpinner.getSelectedItemPosition()])
                .putString("folder", folder.isEmpty() ? "红薯下载" : folder)
                .putBoolean("auto_update", automaticUpdates.isChecked())
                .apply();
        customFolderLabel.setText(folderSummary());
        Toast.makeText(this, "设置已保存", Toast.LENGTH_SHORT).show();
    }

    private void showGuide() {
        String message = "1. 复制小红书公开笔记链接，或把整段分享文字粘贴到首页。\n\n"
                + "2. 单条直接采集；批量任务会按数量自动采用随机间隔。\n\n"
                + "3. 默认保存到 Download/红薯下载；也可以在本页授权其他目录。每条笔记只放媒体和文案.txt。\n\n"
                + "4. 历史记录集中保存在应用内部，不会散落 JSON。\n\n"
                + "只处理你有权保存的公开内容；不会绕过私密、删除、地区或年龄限制；作者主动嵌入原图的署名会保留。";
        present(new AlertDialog.Builder(this).setTitle("使用说明").setMessage(message).setPositiveButton("知道了", null).create());
    }

    private void checkUpdate() {
        updateButton.setEnabled(false);
        updateButton.setText("正在检测…");
        executor.execute(() -> {
            try {
                UpdateChecker.Result result = UpdateChecker.checkAndroid();
                runOnUiThread(() -> showUpdateResult(result));
            } catch (Exception error) {
                runOnUiThread(() -> {
                    resetUpdateButton();
                    present(new AlertDialog.Builder(this).setTitle("暂时无法检测")
                            .setMessage("请检查网络后再试。\n\n" + clean(error.getMessage()))
                            .setPositiveButton("关闭", null).create());
                });
            }
        });
    }

    private void showUpdateResult(UpdateChecker.Result result) {
        resetUpdateButton();
        if (!result.updateAvailable) {
            present(new AlertDialog.Builder(this).setTitle("已经是最新版")
                    .setMessage("当前版本 Android V" + result.currentVersion)
                    .setPositiveButton("好的", null).create());
            return;
        }
        present(new AlertDialog.Builder(this).setTitle("发现 Android V" + result.latestVersion)
                .setMessage("将打开官方发布页，下载新的 APK 后由系统确认安装。")
                .setNegativeButton("稍后", null)
                .setPositiveButton("打开安装包", (dialog, which) -> openUrl(result.apkUrl.isEmpty() ? result.releaseUrl : result.apkUrl))
                .create());
    }

    private void resetUpdateButton() {
        updateButton.setEnabled(true);
        updateButton.setText("检测更新安装包");
    }

    private void openUrl(String url) {
        try { startActivity(new Intent(Intent.ACTION_VIEW, Uri.parse(url))); }
        catch (Exception error) { Toast.makeText(this, "没有可打开网页的应用", Toast.LENGTH_SHORT).show(); }
    }

    private void present(AlertDialog dialog) {
        dialog.setOnShowListener(ignored -> {
            if (dialog.getWindow() != null) dialog.getWindow().setBackgroundDrawable(round(surface, 22, accent, 1));
            Button positive = dialog.getButton(AlertDialog.BUTTON_POSITIVE);
            Button negative = dialog.getButton(AlertDialog.BUTTON_NEGATIVE);
            if (positive != null) positive.setTextColor(accent);
            if (negative != null) negative.setTextColor(muted);
            TextView title = dialog.findViewById(getResources().getIdentifier("alertTitle", "id", "android"));
            TextView message = dialog.findViewById(android.R.id.message);
            if (title != null) title.setTextColor(text);
            if (message != null) message.setTextColor(text);
        });
        dialog.show();
    }

    private void applyPalette() {
        if ("glass".equals(preferences.getString("theme", "neo"))) {
            bg = Color.rgb(223, 234, 242); surface = Color.rgb(237, 244, 248); soft = Color.rgb(220, 234, 244);
            primary = Color.rgb(47, 111, 159); accent = Color.rgb(75, 134, 172); text = Color.rgb(16, 43, 69); muted = Color.rgb(97, 122, 145);
        } else {
            bg = Color.rgb(232, 237, 242); surface = Color.rgb(247, 249, 250); soft = Color.rgb(233, 239, 243);
            primary = Color.rgb(32, 52, 66); accent = Color.rgb(82, 122, 147); text = Color.rgb(24, 38, 51); muted = Color.rgb(108, 127, 143);
        }
    }

    private TextView label(String value, int size, int color, boolean bold) { TextView v = new TextView(this); v.setText(value); v.setTextSize(size); v.setTextColor(color); if (bold) v.setTypeface(Typeface.DEFAULT, Typeface.BOLD); return v; }
    private Button primaryButton(String value) { Button b = new Button(this); b.setText(value); b.setTextColor(Color.WHITE); b.setTextSize(14); b.setTypeface(Typeface.DEFAULT, Typeface.BOLD); b.setAllCaps(false); b.setBackground(round(primary, 14, Color.TRANSPARENT, 0)); b.setMinHeight(dp(50)); return b; }
    private Button secondaryButton(String value) { Button b = new Button(this); b.setText(value); b.setTextColor(text); b.setTextSize(13); b.setTypeface(Typeface.DEFAULT, Typeface.BOLD); b.setAllCaps(false); b.setBackground(round(soft, 13, Color.TRANSPARENT, 0)); b.setMinHeight(dp(48)); return b; }
    private Button quietButton(String value) { Button b = secondaryButton(value); b.setTextColor(muted); b.setBackground(round(Color.TRANSPARENT, 12, Color.TRANSPARENT, 0)); return b; }
    private GradientDrawable round(int color, int radius, int stroke, int width) { GradientDrawable d = new GradientDrawable(); d.setColor(color); d.setCornerRadius(dp(radius)); if (width > 0) d.setStroke(dp(width), stroke); return d; }
    private LinearLayout column() { LinearLayout v = new LinearLayout(this); v.setOrientation(LinearLayout.VERTICAL); return v; }
    private LinearLayout row() { LinearLayout v = new LinearLayout(this); v.setOrientation(LinearLayout.HORIZONTAL); v.setGravity(Gravity.CENTER_VERTICAL); return v; }
    private LinearLayout.LayoutParams matchWrap() { return new LinearLayout.LayoutParams(-1, -2); }
    private LinearLayout.LayoutParams top(int value) { LinearLayout.LayoutParams p = matchWrap(); p.topMargin = dp(value); return p; }
    private LinearLayout.LayoutParams bottom(int value) { LinearLayout.LayoutParams p = matchWrap(); p.bottomMargin = dp(value); return p; }
    private int dp(int value) { return Math.round(value * getResources().getDisplayMetrics().density); }
    private static String clean(String value) { return value == null || value.trim().isEmpty() ? "未知错误" : value; }
}
