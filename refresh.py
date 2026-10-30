#!/usr/bin/env python3
"""market_index_convert.py — 把 4 个社区插件源转成 **DSH 插件市场索引 format 1**

## 承用户令（2026-10-18）

> 「**A，把4个源都转换了，我准备都添加了**」

## 规范来源（**逐行读自校验器源码·非猜**）

`@deepseek-ai/dsh-plugin-market-index` 的 `lib/index.js`（320 行·从 `app.asar` 提取）是
**format 1 的可执行规则集**。要点：

```json
{
  "format": 1,                     // 必须叫 format（不是 formatVersion）·值必须 === 1
  "title": <localizedText>,        // 必需；对象形式必须含 "en"
  "description": <localizedText>,  // 可选
  "metadata": {                    // 可选；categories/labels/sortKeys 的 id 必须先声明
    "categories": { "<id>": {"title": <localizedText>} },
    "labels":     { "<id>": {"title": <localizedText>} },
    "sortKeys":   { "<id>": {"title": <localizedText>, "order": "asc"|"desc"} }
  },
  "plugins": [{
    "name": "<合法 npm 包名>",       // 必需·≤214 字符·PACKAGE_NAME 正则
    "title"/"description": <localizedText>,
    "icon": "https://…" | "data:…",  // 可选
    "author": "<非空白字符串>",
    "homepage": "<http(s) 绝对 URL>",
    "repository": {"url": "<http(s)·无 query/fragment>", "directory": "<相对目录>"},
    "metadata": {"category": "<已声明 id>", "keywords": ["…"],
                 "labels": ["<已声明 id>"], "sortKeys": {"<已声明 id>": <数字>}},
    "versions": [{                  // 必需·非空·同一插件内 version 不得重复
      "version": "<精确 SemVer>",    // 不接受 "v" 前缀
      "publishTimestamp": <整数 Unix 秒·[0,1e11)>,
      "source": {"type":"npm"} | {"type":"git","url":…,"commit":"<40 hex>","path":…},
      "engines": {"dsh": "<SemVer range>"}
    }]
  }]
}
```

**未定义的成员会被丢弃**；`metadata.category`/`labels`/`sortKeys` 引用的 id **必须已声明**。

用法:
  python market_index_convert.py --all              # 转全部 4 源
  python market_index_convert.py --src awesome      # 转单源
  python market_index_convert.py --selftest
"""
from __future__ import annotations

import json
import re
import sys
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:  # noqa: BLE001
    pass

# 本脚本就在仓库根 ⇒ 输出直接写仓库根。
# 2026-10-30 改：原先写到上级 .sandbox-out/market-index，靠手工复制进仓库，
# 导致仓库里的索引长期停在 2026-10-18 的快照（awesome 2,967 vs 上游 3,993）。
ROOT = Path(__file__).resolve().parent
OUT = ROOT

# ── 校验器里的正则（逐字照抄·保证一致）──
PACKAGE_NAME = re.compile(r"^(?:@[a-z0-9][a-z0-9._~-]*/)?[a-z0-9][a-z0-9._~-]*$")
NUMERIC = r"(?:0|[1-9]\d*)"
PRERELEASE_PART = rf"(?:{NUMERIC}|\d*[a-zA-Z-][0-9a-zA-Z-]*)"
SEMVER = re.compile(
    rf"^{NUMERIC}\.{NUMERIC}\.{NUMERIC}(?:-{PRERELEASE_PART}(?:\.{PRERELEASE_PART})*)?(?:\+[0-9a-zA-Z-]+(?:\.[0-9a-zA-Z-]+)*)?$"
)
LANGUAGE_ID = re.compile(r"^[a-z]{2,8}(?:-[a-z0-9]{1,8})*$")

# ── 只转「上游没有 format 1」的源 ──
# 2026-10-30 裁：awesome-dsh-plugin 上游已提供原生 format 1
# （https://awesome-dsh-plugin.com/index.json ＝ https://cdn.jsdelivr.net/npm/dsh-plugin-catalog/index.json），
# 不再经本仓转换，直接作为索引源添加即可（少一层、且自动跟随上游）。
SOURCES = {
    "dsh.so": {
        "url": "https://www.dsh.so/plugins-index.json",
        "title": {"en": "dsh.so plugin index", "zh": "dsh.so 插件索引"},
        "kind": "list",
    },
    "lanshuagent": {
        "url": "https://dsh.lanshuagent.com/api/plugins",
        "title": {"en": "dsh.lanshuagent.com plugin index", "zh": "dsh.lanshuagent.com 插件索引"},
        "kind": "dict",
    },
    "dsh-plugin.org": {
        "url": "https://api.dsh-plugin.org/plugins.zh.json",
        "title": {"en": "dsh-plugin.org community index", "zh": "dsh-plugin.org 社区索引"},
        "kind": "list",
    },
}

UA = "Mozilla/5.0 (compatible; triforge-market-convert/1.0)"


def fetch(url: str, timeout: int = 120):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


# ══════════════════════════════════════════════════════════════════════════
# 字段清洗（**每条都对齐校验器规则**）
# ══════════════════════════════════════════════════════════════════════════
def norm_semver(v) -> str | None:
    """去 v 前缀 + 校验精确 SemVer；不合规返回 None"""
    if not isinstance(v, str):
        return None
    s = v.strip()
    if s.startswith("v") or s.startswith("V"):
        s = s[1:]
    # 去掉尾部 .0 之类多余？不动，只做合法性检查
    return s if SEMVER.match(s) else None


def norm_pkg_name(v) -> str | None:
    """合法 npm 包名（小写·≤214）"""
    if not isinstance(v, str):
        return None
    s = v.strip()
    if len(s) > 214 or not PACKAGE_NAME.match(s):
        return None
    return s


def norm_localized(v, fallback_en: str | None = None):
    """localizedText：字符串或 {lang: str}·对象必须含 en"""
    if isinstance(v, str) and v.strip():
        return v
    if isinstance(v, dict):
        out = {}
        for lang, txt in v.items():
            if isinstance(lang, str) and LANGUAGE_ID.match(lang) and isinstance(txt, str) and txt.strip():
                out[lang] = txt
        if "en" in out:
            return out
        if out and fallback_en:
            out["en"] = fallback_en
            return out
    if fallback_en:
        return fallback_en
    return None


def norm_url(v, allow_query: bool = False) -> str | None:
    """http(s) 绝对 URL·无 query/fragment（repository 用）"""
    if not isinstance(v, str) or not v.strip():
        return None
    s = v.strip()
    if not (s.startswith("https://") or s.startswith("http://")):
        return None
    if not allow_query and ("?" in s or "#" in s):
        s = s.split("?")[0].split("#")[0]
    return s if s.startswith("http") else None


def parse_date_seconds(v) -> int | None:
    """日期/ISO 串 → 整数 Unix 秒"""
    if isinstance(v, (int, float)) and v >= 0:
        n = int(v)
        # 若看起来是毫秒 ⇒ 转秒
        if n > 10_000_000_000:
            n //= 1000
        return n if 0 <= n < 10**11 else None
    if isinstance(v, str) and v.strip():
        s = v.strip().replace("Z", "+00:00")
        for fmt in (None, "%Y-%m-%d", "%Y-%m-%dT%H:%M:%S"):
            try:
                dt = datetime.fromisoformat(s) if fmt is None else datetime.strptime(s, fmt)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                return int(dt.timestamp())
            except Exception:  # noqa: BLE001
                continue
    return None


FALLBACK_TS = 1750000000  # 2025-06-15 附近·仅当源无任何时间字段时兜底（会记录计数）


# ══════════════════════════════════════════════════════════════════════════
# 各源 → format 1
# ══════════════════════════════════════════════════════════════════════════
def convert(name: str, raw) -> dict:
    items = raw if isinstance(raw, list) else (raw.get("plugins") or [])
    cats: dict[str, dict] = {}
    plugins: list[dict] = []
    seen: set[str] = set()
    stats = {"total": len(items), "kept": 0, "no_name": 0, "no_version": 0,
             "dup": 0, "fallback_ts": 0}

    for x in items:
        if not isinstance(x, dict):
            continue
        # ── 取字段（按源）──
        if name == "awesome":
            pkg = norm_pkg_name(x.get("npm"))
            ver = norm_semver(x.get("version"))
            desc = norm_localized(x.get("description"))
            repo = norm_url(x.get("url"))
            author = x.get("owner")
            home = norm_url(x.get("page"), allow_query=True)
            cat = x.get("category")
            kw = x.get("capabilities") if isinstance(x.get("capabilities"), list) else []
            ts = parse_date_seconds(x.get("added") or x.get("downloadsCheckedAt"))
        elif name == "lanshuagent":
            mf = x.get("manifest") if isinstance(x.get("manifest"), dict) else {}
            pkg = norm_pkg_name(mf.get("packageName") or x.get("name"))
            ver = norm_semver(mf.get("version"))
            desc = norm_localized(x.get("description"))
            repo = norm_url(x.get("url"))
            author = x.get("owner")
            home = norm_url(x.get("homepage"), allow_query=True)
            cat = x.get("category")
            kw = [x.get("language")] if x.get("language") else []
            ts = parse_date_seconds(x.get("added") or x.get("createdAt"))
        elif name == "dsh-plugin.org":
            r = x.get("r") if isinstance(x.get("r"), dict) else {}
            pkg = norm_pkg_name(r.get("npmPackage"))
            ver = norm_semver(x.get("vr"))
            desc = norm_localized(x.get("d"))
            repo = norm_url("https://github.com/" + str(r.get("repo"))) if r.get("repo") else None
            author = x.get("o")
            home = repo
            cat = x.get("c")
            kw = [t for t in (x.get("t") or []) if isinstance(t, str)][:12]
            ts = parse_date_seconds(x.get("u") or x.get("a"))
        else:  # dsh.so
            pkg = norm_pkg_name(x.get("alias") or x.get("name"))
            ver = None  # 该源无版本 ⇒ 用 0.0.0（见下）
            desc = norm_localized(x.get("description"))
            repo = norm_url(x.get("source"))
            author = None
            home = norm_url(x.get("url"), allow_query=True)
            cat = x.get("kind")
            kw = [t for t in (x.get("topics") or []) if isinstance(t, str)][:12]
            ts = parse_date_seconds((x.get("verification") or {}).get("lastVerifiedAt")) \
                if isinstance(x.get("verification"), dict) else None

        if not pkg:
            stats["no_name"] += 1
            continue
        # dsh.so 无版本 ⇒ 用 0.0.0 占位（并计数·诚实）
        if not ver:
            if name == "dsh.so":
                ver = "0.0.0"
            else:
                stats["no_version"] += 1
                continue
        if pkg in seen:
            stats["dup"] += 1
            continue
        seen.add(pkg)

        # category 必须已声明
        cid = None
        if isinstance(cat, str) and cat.strip():
            cid = re.sub(r"[^a-z0-9._-]", "-", cat.strip().lower())[:40] or None
            if cid:
                cats.setdefault(cid, {"title": {"en": cid}})

        if ts is None:
            ts = FALLBACK_TS
            stats["fallback_ts"] += 1

        md: dict = {}
        if cid:
            md["category"] = cid
        if kw:
            md["keywords"] = [str(k)[:60] for k in kw if isinstance(k, str)][:20]
        p: dict = {"name": pkg, "metadata": md,
                   "versions": [{"version": ver, "publishTimestamp": ts,
                                 "source": {"type": "npm"}}]}
        t = norm_localized(pkg, pkg)
        if t:
            p["title"] = t
        if desc:
            p["description"] = desc
        if isinstance(author, str) and author.strip():
            p["author"] = author.strip()
        if home:
            p["homepage"] = home
        if repo:
            p["repository"] = {"url": repo}
        plugins.append(p)
        stats["kept"] += 1

    return {
        "format": 1,
        "title": SOURCES[name]["title"],
        "description": {"en": f"Converted from {SOURCES[name]['url']}",
                        "zh": f"由 {SOURCES[name]['url']} 转换"},
        "metadata": {"categories": cats},
        "plugins": plugins,
        "_stats": stats,          # 非格式成员·校验器会丢弃（便于我核对）
    }


# ══════════════════════════════════════════════════════════════════════════
# 自校验（**按校验器规则复刻·同一套正则**）
# ══════════════════════════════════════════════════════════════════════════
def validate(doc: dict) -> list[str]:
    errs: list[str] = []
    if doc.get("format") != 1:
        errs.append("$.format must be 1")
    t = doc.get("title")
    if isinstance(t, dict) and "en" not in t:
        errs.append("$.title must contain en")
    if not isinstance(doc.get("plugins"), list):
        errs.append("$.plugins must be an array")
        return errs
    declared_cats = set(((doc.get("metadata") or {}).get("categories") or {}).keys())
    seen = set()
    for i, p in enumerate(doc["plugins"]):
        at = f"$.plugins[{i}]"
        nm = p.get("name")
        if not isinstance(nm, str) or not PACKAGE_NAME.match(nm) or len(nm) > 214:
            errs.append(f"{at}.name invalid: {nm!r}")
        if nm in seen:
            errs.append(f"{at}.name duplicates {nm}")
        seen.add(nm)
        md = p.get("metadata") or {}
        if "category" in md and md["category"] not in declared_cats:
            errs.append(f"{at}.metadata.category undeclared: {md['category']!r}")
        vs = p.get("versions")
        if not isinstance(vs, list) or not vs:
            errs.append(f"{at}.versions must be non-empty")
            continue
        vseen = set()
        for j, v in enumerate(vs):
            vat = f"{at}.versions[{j}]"
            ver = v.get("version")
            if not isinstance(ver, str) or not SEMVER.match(ver):
                errs.append(f"{vat}.version invalid: {ver!r}")
            if ver in vseen:
                errs.append(f"{vat}.version duplicates {ver}")
            vseen.add(ver)
            ts = v.get("publishTimestamp")
            if not isinstance(ts, int) or ts < 0 or ts >= 10**11:
                errs.append(f"{vat}.publishTimestamp invalid: {ts!r}")
            src = v.get("source") or {}
            if src.get("type") not in ("npm", "git"):
                errs.append(f"{vat}.source.type invalid: {src.get('type')!r}")
            if src.get("type") == "git":
                if not re.match(r"^[0-9a-f]{40}$", str(src.get("commit", ""))):
                    errs.append(f"{vat}.source.commit must be 40-hex")
        for k in ("homepage",):
            if k in p and not isinstance(p[k], str):
                errs.append(f"{at}.{k} must be a string")
        rp = p.get("repository")
        if isinstance(rp, dict):
            u = rp.get("url", "")
            if "?" in u or "#" in u:
                errs.append(f"{at}.repository.url must not contain query/fragment")
    return errs


def selftest() -> int:
    chk: list[tuple[str, bool, str]] = []

    def ck(n, ok, d=""):
        chk.append((n, ok, d))

    # ① 正则与校验器一致
    ck("SemVer 正则接受 1.2.3", bool(SEMVER.match("1.2.3")))
    ck("SemVer 正则接受 0.1.1-rc.6", bool(SEMVER.match("0.1.1-rc.6")))
    ck("**SemVer 正则拒绝 v 前缀**（校验器要求精确 SemVer）", not SEMVER.match("v1.2.3"))
    ck("norm_semver 会剥掉 v", norm_semver("v0.4.2") == "0.4.2")
    ck("包名正则接受 @scope/name", bool(PACKAGE_NAME.match("@anonyjcy/dsh-j-space")))
    ck("包名正则拒绝大写", not PACKAGE_NAME.match("BadName"))
    # ② localizedText
    ck("localizedText 接受字符串", norm_localized("hello") == "hello")
    ck("localizedText 对象需含 en", norm_localized({"zh": "中文"}) is None)
    ck("localizedText 对象含 en 通过", isinstance(norm_localized({"en": "a", "zh": "b"}), dict))
    # ③ 日期
    ck("日期转 Unix 秒", isinstance(parse_date_seconds("2026-10-11T12:25:55Z"), int))
    ck("毫秒自动转秒", parse_date_seconds(1792308493000) < 10**11)
    # ④ 端到端（小样本·不联网）
    # 2026-10-30: awesome 上游已有原生 format 1 ⇒ 不再转换，自检改用 lanshuagent 形状
    fake = {"plugins": [{"manifest": {"packageName": "@a/b", "version": "1.0.0"},
                         "description": {"en": "x"}, "url": "https://github.com/a/b",
                         "owner": "a", "homepage": "https://x.com/p/1",
                         "category": "ui", "added": "2026-01-01"}]}
    doc = convert("lanshuagent", fake)
    ck("转换产出 format=1", doc.get("format") == 1)
    ck("转换产出 1 条插件", len(doc.get("plugins", [])) == 1)
    errs = validate(doc)
    ck("**自产文档通过自校验（0 错）**", not errs, f"{len(errs)} 错" + (f": {errs[0]}" if errs else ""))
    # ⑤ 类别已声明
    ck("类别 id 已声明", "ui" in ((doc.get("metadata") or {}).get("categories") or {}))

    bad = [x for x in chk if not x[1]]
    print("=" * 88)
    print("MARKET INDEX CONVERT SELFTEST  （社区源 → DSH format 1）")
    print("=" * 88)
    for n, ok, d in chk:
        print(f"  {'✅' if ok else '❌'} {n}" + (f"  — {d}" if d else ""))
    print("-" * 88)
    print(f"  ==== {len(chk) - len(bad)}/{len(chk)} " + ("✅ 全绿" if not bad else "❌ 有失败") + " ====")
    print("=" * 88)
    return 0 if not bad else 1


def main() -> int:
    a = sys.argv[1:]
    if "--selftest" in a:
        return selftest()
    names = list(SOURCES) if ("--all" in a or not a) else [a[a.index("--src") + 1]]
    OUT.mkdir(parents=True, exist_ok=True)
    for n in names:
        if n not in SOURCES:
            print("  未知源:", n)
            continue
        t0 = time.time()
        try:
            raw = fetch(SOURCES[n]["url"])
        except Exception as e:  # noqa: BLE001
            print(f"  ❌ {n} 拉取失败: {str(e)[:100]}")
            continue
        doc = convert(n, raw)
        errs = validate(doc)
        stats = doc.pop("_stats", {})
        out = OUT / f"{n.replace('/', '_')}.format1.json"
        out.write_text(json.dumps(doc, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
        print(f"  ✅ {n}")
        print(f"       源 {stats['total']} 条 ⇒ 保留 {stats['kept']} 条"
              f"（无包名 {stats['no_name']} ｜ 无版本 {stats['no_version']} ｜ 重名 {stats['dup']} ｜ 兜底时间戳 {stats['fallback_ts']}）")
        print(f"       类别 {len(doc['metadata']['categories'])} 个 ｜ 自校验 {'✅ 0 错' if not errs else f'❌ {len(errs)} 错：' + errs[0]}")
        print(f"       输出 {out.name}  {out.stat().st_size // 1024} KB ｜ 耗时 {time.time() - t0:.1f}s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
