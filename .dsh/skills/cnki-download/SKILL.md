---
name: cnki-download
description: 知网（CNKI）批量下载技能（中文输出）。根据文献清单（编号/题名/期刊），通过 Playwright 复用用户的 CARSI 机构登录态，自动逐篇检索知网并下载论文 PDF/CAJ，含登录检测、匹配容错、短关键词重试、详情页下载、文件校验（PDF/CAJ 头识别）与日志汇总。触发场景：用户要求"批量从知网下载论文"、"按清单下载知网文献"、"把中文论文从知网抓下来"，或给出一个文献清单文件要求自动下载全文。前置：本机 Python（py -3）、playwright 及 chromium（见"环境准备"）。
license: MIT
---

# 知网（CNKI）批量下载技能

把一份文献清单（编号 + 题名 + 期刊）转化为已下载到本地目录的论文 PDF/CAJ 文件。核心资产是 `scripts/cnki_download.py`（Playwright 自动化脚本）。

> **合规声明**：本技能仅在用户通过机构订阅合法登录（如 CARSI/校园网）的前提下，自动化"个人检索 + 下载"操作，不绕过任何付费或验证机制；请遵守知网服务条款与所在机构使用规范。

## 工作流程

### 0. 环境准备（首次）
- 检查 Python：`py -3 --version`
- 检查 playwright：`py -3 -c "import playwright"`；未装则 `py -3 -m pip install playwright`
- 检查 Chromium：`py -3 -c "from playwright.sync_api import sync_playwright; p=sync_playwright().start(); p.chromium.launch(headless=True); p.stop()"`；失败则 `py -3 -m playwright install chromium`

### 1. 准备清单（CSV）
清单需含列：`编号`、`题名`（必填）；`期刊年卷期页`（可选，用于结果判别）；`直达链接`（可选，如 wap.cnki.net 文章页）。
- 从总目/文献清单生成：可用 `python` 脚本从 Markdown 表格抽取，或复用既有 CSV（如《文献传递申请清单.csv》）。
- 只下载部分条目：可新建 CSV 只含目标行，或脚本用 `--ids` 参数指定（如 `--ids CN-01,CN-02`）。

### 2. 运行脚本（交互：需在弹出浏览器完成一次登录）
```powershell
py -3 <SKILL_ROOT>/scripts/cnki_download.py --list <清单.csv> --out <输出目录> [--profile <profile目录>] [--retry 2] [--headless]
```
- 首次运行时浏览器弹出 → 用户完成 **CARSI 机构登录**（选所在高校 → 学号/工号）；登录态保存于 profile（默认 `<SKILL_ROOT>/../../.pw_cache/cnki_profile`，即工作区 `.pw_cache`），**下次自动复用，无需再登录**
- 脚本自动轮询检测登录（首页出现机构名/用户名即继续）
- 逐篇：完整题名检索 → 结果匹配（题名前 6 字）→ 行内 PDF 下载 / "下载"下拉 / 详情页下载 → 失败则去前缀短关键词重试 → 仍失败标记"需人工"
- 文件校验：PDF 头 `%PDF` 与 CAJ 头 `CAJ` 自动分流命名（`编号.pdf` / `编号.caj`），无效文件自动删除
- 日志：`<输出目录>_log.csv`（编号/状态/来源），控制台实时进度

### 3. 结果与汇报
- 统计：成功数 / 需人工清单；按"成功编号 / 需人工编号"汇报
- 需人工的常见处理：知网直达页脚本（见 SKILL 备注）、换万方/维普（改清单直达链接）、转图书馆文献传递（CALIS/NSTL/读秀）
- 与 Zotero 衔接：PDF 拖入 Zotero 自动识别元数据；`编号.pdf` 命名可与已有 RIS 条目一一对应

## 注意事项
- **登录态**：profile 目录持久化 Cookie；登录失效时脚本会提示，重新登录即可
- **反爬/页面改版**：知网偶尔改版导致选择器失效——若大量"未匹配/无按钮"，更新 `scripts/cnki_download.py` 中的选择器列表（`table.result-table-list tr`、`li.list-item` 等）与按钮选择器
- **小文件**：<20 KB 视为无效自动丢弃；CAJ 版论文（部分老文献）自动命名 `.caj`
- **合规**：仅限本人机构订阅范围内个人研究使用，勿批量抓取用于再分发
- **后台运行**：脚本需用户登录确认，建议前台运行；确需后台时用 `--headless`（前提：profile 已登录）

## 常见问题
| 问题 | 处理 |
|---|---|
| 未检测到登录 | 浏览器完成 CARSI 登录后脚本自动继续；确认机构在知网机构列表 |
| 检索无结果 | 自动换短关键词重试；仍失败→改直达链接或转文献传递 |
| 下载按钮找不到 | 脚本会尝试详情页；仍失败→换数据库（万方/维普） |
| 文件是 CAJ | 自动命名 `.caj`，Zotero 可挂附件或用 CAJViewer 转 PDF |
