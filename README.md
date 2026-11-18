# RAR Issue Tracker Dashboard

網址（部署後）：https://marzlo.github.io/RAR/

資料來源是 Jira filter 12811（RAR 票），顯示 Jira ID、摘要、External Link（STLA prsse 編號）與狀態。

## 運作方式

```
.github/workflows/refresh-dashboard.yml  # 平日台北 08:17 到 19:17 每小時自動跑，也可在網頁上按「更新資料」
scripts/fetch_jira.py                    # 用 Jira API 抓 filter 12811 -> raw_issues.json
scripts/build_dashboard.py               # 整理資料並嵌進 template.html -> site/index.html
scripts/template.html                    # 頁面版型（要改外觀改這支）
```

`raw_issues.json` 與 `site/` 只在 Actions 執行時產生，不進 git。

## 第一次設定（只要做一次）

1. **Secrets**：repo → Settings → Secrets and variables → Actions，新增
   `JIRA_EMAIL`、`JIRA_API_TOKEN`（可以沿用 SYS2 那組；secrets 是各 repo 獨立的，要再建一次）。
2. **Pages**：Settings → Pages → Build and deployment → Source 選 **GitHub Actions**。
3. **跑一次**：Actions → Refresh RAR Dashboard → Run workflow。

## 網頁上的「更新資料」按鈕

需要一個 fine-grained token：Repository access 只選 `marzlo/RAR`，Permissions 的 **Actions** 設為 Read and write。
Token 只存在使用者自己的瀏覽器裡。按下按鈕後網頁會請 GitHub Actions 立即重抓 Jira，並在原頁面顯示進度，完成後自動重新載入。

## 注意：資料公開性

GitHub Free 的 Pages 只能從 public repo 發布，網址公開可見。頁面上會有 RAR 票的標題與狀態（Jira 與 prsse 連結需登入才能開）。
