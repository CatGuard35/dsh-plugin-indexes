# dsh-plugin-indexes

**DSH 插件市场索引（format 1）** —— 把「上游没有 format 1」的社区插件源转成 DSH 市场能读的格式。

## 这是什么

DSH 的插件市场只接受 **Plugin market index format 1**。上游里有一部分站点已经是这个格式
（可直接添加），另一部分各用自家格式（直接添加会报「此索引的格式无效」）。

本仓库只负责**后者**：把非 format 1 的上游转成 format 1，并由 GitHub Actions 每天自动刷新。

## 索引源 URL（本仓转换产物）

```
https://raw.githubusercontent.com/CatGuard35/dsh-plugin-indexes/main/dsh.so.format1.json
https://raw.githubusercontent.com/CatGuard35/dsh-plugin-indexes/main/lanshuagent.format1.json
https://raw.githubusercontent.com/CatGuard35/dsh-plugin-indexes/main/dsh-plugin.org.format1.json
```

**CDN 备选（jsDelivr·更快且有缓存）：**

```
https://cdn.jsdelivr.net/gh/CatGuard35/dsh-plugin-indexes@main/dsh.so.format1.json
https://cdn.jsdelivr.net/gh/CatGuard35/dsh-plugin-indexes@main/lanshuagent.format1.json
https://cdn.jsdelivr.net/gh/CatGuard35/dsh-plugin-indexes@main/dsh-plugin.org.format1.json
```

## 不需要本仓转换的（上游本身就是 format 1，直连即可）

```
https://cdn.jsdelivr.net/npm/dsh-plugin-catalog/index.json   # Awesome DSH Plugin 精选（约 3,993）
https://awesome-dsh-plugin.com/index.json                   #   同一 catalog 的 Pages 镜像
https://dshopen.org/index.json                              # Open Plugin Market（约 958）
```

2026-10-30 起 `awesome` **不再经本仓转换**：上游已直接提供 format 1，绕过转换层更实时，
且不会再出现「转换版停在 2026-10-18、落后上游 1,000+ 条」的滞后。
本仓根目录的 `awesome.format1.json` 仅为兼容旧配置保留，**已弃用**，请改用上面的直连地址。

## 如何在 DSH 里添加

1. 插件页 → **「发现」** → **「+ 添加索引源」**
2. 粘贴上面的 URL（逐个添加）
3. 保存

> DSH 给每个索引源的抓取上限约 **15 秒**；raw.githubusercontent.com 在部分地区偏慢时，
> 优先使用上面的 jsDelivr CDN 地址。

## 各文件

| 文件 | 插件数（约） | 上游 | 上游原生 format 1？ |
|---|---|---:|---|
| `dsh.so.format1.json` | 13,445 | `www.dsh.so/plugins-index.json` | ❌ 需转换 |
| `lanshuagent.format1.json` | 594 | `dsh.lanshuagent.com/api/plugins` | ❌ 需转换 |
| `dsh-plugin.org.format1.json` | 2,223 | `api.dsh-plugin.org/plugins.zh.json` | ❌ 需转换 |
| `awesome.format1.json` | 2,967（已冻结） | `awesome-dsh-plugin.com/plugins.json` | ✅ 改用直连，本文件弃用 |

## ⚠️ 已知限制

- **`dsh.so.format1.json`**：该源**没有版本字段**，转换时统一用 `0.0.0` 占位 ⇒
  **只适合浏览，不适合一键安装**（安装目标 `name@0.0.0` 多半装不上）。
- 各源的 `source` 统一标为 `npm` ⇒ 若某包**未发布到 npm**，安装会失败。
- 转换规则**逐行照抄**官方校验器 `@deepseek-ai/dsh-plugin-market-index` 的 `lib/index.js`：
  - 顶层字段是 `format`（不是 `formatVersion`），值必须 `=== 1`
  - `title` 对象形式必须含 `en`
  - `plugins[].name` 必须是合法 npm 包名（≤214·小写）
  - `versions[].version` 必须是**精确 SemVer**（不接受 `v` 前缀）
  - `publishTimestamp` 必须是整数 Unix 秒
  - `metadata.category` 引用的 id 必须先在 `metadata.categories` 声明
  - `repository.url` 不得含 `?`/`#`

## 刷新

**自动**：`.github/workflows/refresh.yml` 每天 UTC 20:17（北京 04:17）跑一次，
有变化才提交；也可在 Actions 页手动 `Run workflow`。

**手动**：

```bash
python refresh.py --selftest   # 离线自检（不联网）
python refresh.py --all        # 拉取上游并重写本目录 JSON
```

需要 Python 3.10+（仅标准库，无第三方依赖）。转换结果直接写仓库根，无需再复制。

## 许可

转换产物沿用各源自身的许可与署名。本仓库仅提供格式转换。
