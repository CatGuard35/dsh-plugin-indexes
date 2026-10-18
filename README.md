# dsh-plugin-indexes

**DSH 插件市场索引（format 1）** —— 把社区插件源转成 DeepSeek Harness 官方市场能读的格式。

## 这是什么

DSH 的插件市场只接受 **Plugin market index format 1**。社区上的几个大索引
（`dsh.so`、`awesome-dsh-plugin.com`、`dsh.lanshuagent.com`、`dsh-plugin.org`）
各用自家格式，**直接添加会报「此索引的格式无效」**。

本仓库提供**转换后的 format 1 版本**，可直接作为 DSH 市场的索引源添加。

## 索引源 URL

```
https://raw.githubusercontent.com/CatGuard35/dsh-plugin-indexes/main/awesome.format1.json
https://raw.githubusercontent.com/CatGuard35/dsh-plugin-indexes/main/dsh.so.format1.json
https://raw.githubusercontent.com/CatGuard35/dsh-plugin-indexes/main/lanshuagent.format1.json
https://raw.githubusercontent.com/CatGuard35/dsh-plugin-indexes/main/dsh-plugin.org.format1.json
```

**CDN 备选（jsDelivr·更快且有缓存）：**

```
https://cdn.jsdelivr.net/gh/CatGuard35/dsh-plugin-indexes@main/awesome.format1.json
https://cdn.jsdelivr.net/gh/CatGuard35/dsh-plugin-indexes@main/dsh.so.format1.json
https://cdn.jsdelivr.net/gh/CatGuard35/dsh-plugin-indexes@main/lanshuagent.format1.json
https://cdn.jsdelivr.net/gh/CatGuard35/dsh-plugin-indexes@main/dsh-plugin.org.format1.json
```

## 如何在 DSH 里添加

1. 插件页 → **「发现」** → **「+ 添加索引源」**
2. 粘贴上面的 URL（逐个添加）
3. 保存

## 各文件

| 文件 | 插件数 | 来源 |
|---|---|---|
| `awesome.format1.json` | 2,967 | 见下 |
| `dsh.so.format1.json` | 13,445 | 见下 |
| `lanshuagent.format1.json` | 594 | 见下 |
| `dsh-plugin.org.format1.json` | 2,223 | 见下 |

## ⚠️ 已知限制

- **`dsh.so.format1.json`**：该源**没有版本字段**，转换时统一用 `0.0.0` 占位 ⇒
  **只适合浏览，不适合一键安装**（安装目标 `name@0.0.0` 多半装不上）。
- 其余三个源的 `source` 统一标为 `npm` ⇒ 若某包**未发布到 npm**，安装会失败。
- 转换规则**逐行照抄**官方校验器 `@deepseek-ai/dsh-plugin-market-index` 的 `lib/index.js`：
  - 顶层字段是 `format`（不是 `formatVersion`），值必须 `=== 1`
  - `title` 对象形式必须含 `en`
  - `plugins[].name` 必须是合法 npm 包名（≤214·小写）
  - `versions[].version` 必须是**精确 SemVer**（不接受 `v` 前缀）
  - `publishTimestamp` 必须是整数 Unix 秒
  - `metadata.category` 引用的 id 必须先在 `metadata.categories` 声明
  - `repository.url` 不得含 `?`/`#`

## 刷新

```bash
python refresh.py
```

重新拉取四个源并重写本目录的 JSON。需要 Python 3.10+。

## 许可

转换产物沿用各源自身的许可与署名。本仓库仅提供格式转换。
