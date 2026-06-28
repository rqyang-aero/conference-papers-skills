# Conference Papers Skills

这是一组用于构建“会议论文阅读网站”的 Codex skills。它们可以从会议页面、RSS/Atom feed、手动论文列表中收集论文，补全 arXiv/PDF/项目主页/图片信息，生成结构化精读 note，并构建可搜索的静态 HTML 网站。

这个仓库的核心目标不是只生成论文列表，而是沉淀一套可维护的论文阅读数据：

- `data/papers/*.json`: 每篇论文的结构化元数据、图表、公式、精读 note。
- `data/conferences/*.json`: 会议年份索引和来源记录。
- `dist/`: 由 `data/` 统一渲染出来的静态网站。

`dist/` 是产物，`data/` 才是长期协作和维护的源。

## Skill 组成

```text
conference-papers/              # 核心实现：脚本、配置、模板、schema、测试
conference-papers-fetch/        # 抓取论文候选入口
conference-papers-read/         # 精读论文和生成 final note 入口
conference-papers-read2md/      # 从 paper JSON 生成 Obsidian 兼容精读 Markdown
conference-papers-site/         # 从已有 data/ 构建静态网站入口
conference-papers-maintain/     # 增量维护、去重、补 metadata、修内链入口
```

除 `conference-papers-read2md` 是独立 Markdown 导出 skill 外，其余 wrapper skill 都很薄，真正实现集中在 `conference-papers/scripts/`。这样可以避免多份脚本漂移。

## 安装到 Codex

从本仓库根目录安装到个人 skills 目录：

```bash
cp -R conference-papers ~/.codex/skills/
cp -R conference-papers-fetch ~/.codex/skills/
cp -R conference-papers-read ~/.codex/skills/
cp -R conference-papers-read2md ~/.codex/skills/
cp -R conference-papers-site ~/.codex/skills/
cp -R conference-papers-maintain ~/.codex/skills/
```

开发调试时推荐用软链接，这样仓库里的修改会立刻反映到 Codex skill：

```bash
mkdir -p ~/.codex/skills
for skill in \
  conference-papers \
  conference-papers-fetch \
  conference-papers-read \
  conference-papers-read2md \
  conference-papers-site \
  conference-papers-maintain
do
  rm -rf "$HOME/.codex/skills/$skill"
  ln -s "/Users/barry/Documents/Projects/conference-papers-skills/$skill" "$HOME/.codex/skills/$skill"
done
```

安装后重启 Codex。六个目录建议保持同级；其中 wrapper skills 会调用：

```text
../conference-papers/scripts/...
```

## 快速开始

创建一个网站工作目录：

```bash
mkdir -p ~/PaperSites/embodied-papers
cd ~/PaperSites/embodied-papers
codex --search -C ~/PaperSites/embodied-papers
```

抓取论文候选：

```text
Use $conference-papers-fetch 抓取 CVPR 2026 中 VLA、Humanoid、locomotion、loco-manipulation 相关论文。
```

精读重点论文：

```text
Use $conference-papers-read 精读 data/papers/xxx.json，生成 final note，要求图、表、公式完整。
```

生成 Obsidian 兼容 Markdown 到 inbox（不参与建站）：

```text
Use $conference-papers-read2md 精读 data/papers/xxx.json，生成 Obsidian md 到 data/_inbox。
```

重建网站：

```text
Use $conference-papers-site 根据 data/ 重建网站。
```

也可以一句话完整构建：

```text
Use $conference-papers 构建 CVPR 2026 的相关论文阅读网站，主题是 VLA、Humanoid、locomotion、loco-manipulation。
```

默认输出：

```text
data/
dist/
```

## 推荐工作流

长期维护建议使用这条流程：

```text
1. 在网站工作目录中配置 config/user-config.local.json
2. Use $conference-papers-fetch 抓取或刷新论文候选
3. 运行 enrich_arxiv.py 补 arXiv、abstract、pdf_url
4. 运行 enrich_fulltext.py 补 figure URL 和 project_url
5. Use $conference-papers-read 精读重点论文，生成 final note
6. 运行 validate_notes.py 做结构校验
7. 运行 resolve_links.py 修复 related/future work 内链
8. Use $conference-papers-site 重建 dist/
```

如果只想沉淀 Obsidian 精读笔记，而不是更新网站 note，可以在第 3 或第 4 步之后运行：

```text
Use $conference-papers-read2md 精读 data/papers/xxx.json
```

它会读取 `data/papers/*.json` 中的标题、作者、arXiv/PDF/项目主页等信息，生成：

```text
data/_inbox/{paper-id}/{MethodName}.md
data/_inbox/{paper-id}/assets/
```

`conference-papers-read2md` 不修改 `data/papers/*.json`，不生成 `paper["note"]`，也不参与 `dist/` 网站构建。

### Read2MD 本地测试

以测试站点为例：

```bash
cd /Users/barry/PaperSites/test-conference-papers

python3 ~/.codex/skills/conference-papers-read2md/scripts/paper_json_context.py \
  data/papers/asap-aligning-simulation-and-real-world-physics-for-learning-agile-humanoid-whole-body-ski.json \
  --site .
```

确认输出里包含：

```text
"suggested_method_name": "ASAP"
"primary_source": {"type": "arxiv_html", "url": "https://arxiv.org/html/2502.01143"}
"output_dir": "data/_inbox/asap-aligning-simulation-and-real-world-physics-for-learning-agile-humanoid-whole-body-ski"
```

然后在同一站点目录运行 Codex：

```bash
codex --search -C /Users/barry/PaperSites/test-conference-papers
```

发送：

```text
Use $conference-papers-read2md 精读 data/papers/asap-aligning-simulation-and-real-world-physics-for-learning-agile-humanoid-whole-body-ski.json，生成 Obsidian md 到 data/_inbox。
```

完成后检查：

```bash
find data/_inbox/asap-aligning-simulation-and-real-world-physics-for-learning-agile-humanoid-whole-body-ski -maxdepth 2 -type f | sort
```

应看到 `ASAP.md` 和 `assets/ASAP_fig*.png`。Markdown 中图片应为 Obsidian wikilink，例如：

```markdown
![[assets/ASAP_fig1.png|600]]
```

快速预览可以只生成 draft note：

```bash
python3 ~/.codex/skills/conference-papers/scripts/add_papers.py --draft
python3 ~/.codex/skills/conference-papers/scripts/enrich_arxiv.py --data data
python3 ~/.codex/skills/conference-papers/scripts/build_site.py --data data --out dist
```

正式发布不要把 draft note 当最终笔记。

## 配置

内置默认配置在：

```text
conference-papers/config/user-config.json
```

网站工作目录可以创建本地覆盖：

```text
config/user-config.local.json
```

示例：

```json
{
  "site": {
    "title": "Embodied AI Paper Atlas",
    "data_dir": "data",
    "output_dir": "dist"
  },
  "defaults": {
    "conference": "RSS",
    "year": 2026,
    "topics": ["VLA", "Humanoid", "locomotion"]
  },
  "sources": [
    {
      "name": "rss-2026",
      "conference": "RSS",
      "year": 2026,
      "type": "rss",
      "url": "https://example.org/rss.xml"
    }
  ]
}
```

配置优先级从低到高：

1. 脚本内置默认值。
2. `conference-papers/config/user-config.json`。
3. `conference-papers/config/user-config.local.json`。
4. 当前网站目录的 `config/user-config.local.json`。
5. 显式 CLI 参数。

## 数据结构

完整 schema 见 `conference-papers/references/site-schema.md`。核心 paper JSON 形态如下：

```json
{
  "id": "stable-paper-id",
  "title": "Paper title",
  "conference": "CVPR",
  "year": 2026,
  "topics": ["VLA", "Humanoid"],
  "authors": ["A. Author"],
  "abstract": "Abstract text",
  "url": "https://...",
  "detail_url": "https://...",
  "pdf_url": "https://...",
  "arxiv_id": "2601.00001",
  "arxiv_url": "https://arxiv.org/abs/2601.00001",
  "project_url": "https://...",
  "source": "cvf|rss|manual",
  "source_url": "https://source",
  "figures": [
    {
      "number": "Figure 1",
      "url": "https://...",
      "local_path": "",
      "caption": "Caption text",
      "section": "method",
      "anchor": "method-overview"
    }
  ],
  "note": {
    "mode": "final",
    "summary": "...",
    "background": "...",
    "contributions": ["..."],
    "method": [
      {
        "title": "3 Method section title",
        "text": "Parent method section explanation.",
        "subsections": [
          {
            "title": "3.1 Method subsection title",
            "text": "Subsection mechanism, evidence, and why it matters."
          }
        ]
      }
    ],
    "figures": [],
    "formulas": [
      {
        "title": "Formula name",
        "latex": "J(\\theta)=\\mathbb{E}_{\\tau}[r(\\tau)]",
        "text": "Formula meaning and why it matters.",
        "symbols": [
          {"symbol": "\\theta", "text": "policy parameters"}
        ],
        "section": "method"
      }
    ],
    "experiments": [
      {
        "title": "5 Experiments",
        "text": "Evaluation setup, baselines, metrics, and tasks.",
        "subsections": [
          {
            "title": "5.2 Main Results",
            "text": "Main result interpretation and what it proves."
          }
        ]
      }
    ],
    "tables": [
      {
        "title": "Table 1",
        "text": "Table content or caption.",
        "summary": "Conclusion supported by this table.",
        "section": "experiments"
      }
    ],
    "critical_thinking": [
      {"title": "优点", "text": "..."},
      {"title": "局限性", "text": "..."},
      {"title": "潜在改进", "text": "..."}
    ],
    "related_work": [],
    "future_work": [],
    "quality_gate": {
      "all_figures_verified": true,
      "all_tables_verified": true,
      "all_formulas_verified": true
    }
  }
}
```

## Final Note 要求

Final note 是结构化论文精读文章，不是摘要。写之前必须阅读：

```text
conference-papers/references/html-note-style.md
```

关键要求：

- `mode` 只有在全文、图、表、公式、实验和局限都核对后才能设为 `final`。
- 使用克制的中文技术深读风格，面向具身智能、机器人、CV 读者。
- 开篇交代真实痛点、重要性、核心方法和最硬证据。
- `background` 写成任务挑战、已有方法短板、本文切入点。
- `method` 按论文原章节层级组织，用 `subsections` 保留 `3` 和 `3.1` 的父子关系。
- `figures` 包含论文所有 Figure，并设置 `section`，不要放成页面末尾孤立图库。
- `formulas` 收录重要公式，使用 display math 的 `latex` 字段，并解释符号。
- `experiments` 按真实实验小节拆分，说明设置、指标、主结果、消融、泛化、效率和结论边界。
- `tables` 收录重要结果、消融、配置或效率表，并写清表格支持的结论。
- `critical_thinking` 必须包含 `优点`、`局限性`、`潜在改进` 三项，且要有具体证据。
- 结构合格但像广告稿、翻译稿、图表堆砌或泛泛总结的 note 不能标为 final。

## 图文同步和图片归档

图片可以使用外链，不要求默认下载。图文同步依赖 `figure.section`：

```json
{
  "number": "Figure 1",
  "url": "https://example.org/method.png",
  "caption": "Method overview.",
  "section": "method",
  "anchor": "method-overview"
}
```

支持的 section：

```text
background
contributions
method
experiments
critical_thinking
related_work
future_work
```

如果担心外链失效，可以归档已有 figure URL：

```bash
python3 ~/.codex/skills/conference-papers/scripts/archive_figures.py --data data
```

图片会保存到：

```text
data/assets/papers/{paper_id}/
```

脚本会回填 `local_path`。渲染时 `local_path` 优先于外链 `url`。

## 常用脚本

以下命令在网站工作目录中运行。开发仓库中也可以把 `~/.codex/skills/conference-papers/scripts/` 替换为 `conference-papers/scripts/`。

### 添加或合并论文

```bash
python3 ~/.codex/skills/conference-papers/scripts/add_papers.py \
  --conference CVPR \
  --year 2026 \
  --topic VLA \
  --topic Humanoid \
  --url "https://cvpr.thecvf.com/virtual/2026/papers.html" \
  --data data \
  --draft
```

### 只抓会议索引

```bash
python3 ~/.codex/skills/conference-papers/scripts/crawl_conference.py \
  --conference CVPR \
  --year 2026 \
  --url "https://cvpr.thecvf.com/virtual/2026/papers.html" \
  --topics VLA Humanoid locomotion \
  --out data/conferences/cvpr-2026.json
```

### 手动列表导入

```bash
python3 ~/.codex/skills/conference-papers/scripts/add_papers.py \
  --manual papers.json \
  --conference RSS \
  --year 2026 \
  --topic humanoid \
  --data data \
  --draft
```

手动 JSON 示例：

```json
[
  {
    "title": "LocoManip: Loco-Manipulation with Humanoid Robots",
    "authors": ["A. Author", "B. Builder"],
    "url": "https://arxiv.org/abs/2601.00001",
    "pdf_url": "https://arxiv.org/pdf/2601.00001",
    "abstract": "Humanoid locomotion and manipulation with a whole-body controller."
  }
]
```

### 补全 metadata

```bash
python3 ~/.codex/skills/conference-papers/scripts/enrich_arxiv.py --data data
python3 ~/.codex/skills/conference-papers/scripts/enrich_fulltext.py --data data
```

`enrich_arxiv.py` 会按 title 匹配 arXiv，补 `arxiv_id`、`arxiv_url`、`pdf_url`、`abstract` 和作者信息。匹配分数低时会跳过，不会强写。

`enrich_fulltext.py` 会访问 `detail_url` 或 `url`，尝试提取 `<figure>` 图片、caption 和项目主页。

### 生成 draft note

```bash
python3 ~/.codex/skills/conference-papers/scripts/generate_note_data.py \
  --paper data/papers/PAPER_ID.json \
  --draft \
  --data data
```

### 校验 final note

```bash
python3 ~/.codex/skills/conference-papers/scripts/validate_notes.py --data data
```

校验内容包括 draft 状态、必填字段、section 层级、公式 display math、figure 引用和 `quality_gate`。它不能替代人工对照全文确认。

### 解析相关工作内链

```bash
python3 ~/.codex/skills/conference-papers/scripts/resolve_links.py --data data
```

`related_work` 和 `future_work` 可以先只写：

```json
{
  "title": "OpenVLA",
  "text": "Used as the closest VLA policy baseline."
}
```

如果 corpus 中已有匹配论文，脚本会补 `paper_id` 和 `href`。

### 构建网站

```bash
python3 ~/.codex/skills/conference-papers/scripts/build_site.py --data data --out dist
```

本地预览：

```bash
python3 -m http.server 8080 -d dist
```

打开：

```text
http://localhost:8080
```

## 支持的数据源

当前支持：

- CVF/CVPR virtual pages。
- RSS/Atom feeds。
- 手动 JSON 论文列表。

新增数据源适配前，先阅读：

```text
conference-papers/references/source-adapters.md
```

## HTML 模板和搜索

模板文件在：

```text
conference-papers/assets/site-template/
  paper-note.html
  index.html
  collection.html
  site.css
  search.js
```

构建后会生成：

```text
dist/
  index.html
  search-index.json
  assets/
  {conference}/
  papers/{paper-id}/index.html
```

`search-index.json` 包含 title、authors、conference、year、topics、abstract 和页面 URL。前端搜索完全在浏览器中完成，不需要后端服务。

## 多人协作

推荐共享 `data/`，不要共享或拼接多个 `dist/`。

```text
人 A: CVPR 2026 -> data/papers/*.json
人 B: RSS 2026  -> data/papers/*.json
人 C: IROS 2026 -> data/papers/*.json
```

汇总后统一运行：

```bash
python3 ~/.codex/skills/conference-papers/scripts/enrich_arxiv.py --data data
python3 ~/.codex/skills/conference-papers/scripts/resolve_links.py --data data
python3 ~/.codex/skills/conference-papers/scripts/build_site.py --data data --out dist
```

## 开发和测试

在本仓库根目录运行：

```bash
python3 -m unittest discover -s conference-papers/tests
```

验证 skill 基本结构：

```bash
python3 /Users/barry/.codex/skills/.system/skill-creator/scripts/quick_validate.py conference-papers
python3 /Users/barry/.codex/skills/.system/skill-creator/scripts/quick_validate.py conference-papers-fetch
python3 /Users/barry/.codex/skills/.system/skill-creator/scripts/quick_validate.py conference-papers-read
python3 /Users/barry/.codex/skills/.system/skill-creator/scripts/quick_validate.py conference-papers-site
python3 /Users/barry/.codex/skills/.system/skill-creator/scripts/quick_validate.py conference-papers-maintain
```

如果当前 Python 环境缺少 `yaml` / PyYAML，先安装或临时指定依赖目录：

```bash
python3 -m pip install --target /tmp/codex-pyyaml PyYAML
PYTHONPATH=/tmp/codex-pyyaml python3 /Users/barry/.codex/skills/.system/skill-creator/scripts/quick_validate.py conference-papers
```

端到端 smoke test：

```bash
python3 conference-papers/scripts/add_papers.py \
  --manual conference-papers/tests/fixtures/manual_papers.json \
  --data /tmp/conference-papers-data \
  --draft

python3 conference-papers/scripts/build_site.py \
  --data /tmp/conference-papers-data \
  --out /tmp/conference-papers-dist
```

## 常见问题

### 为什么不直接维护 HTML？

因为搜索索引、会议页、topic 页、相关工作内链和图文同步都来自统一的 `data/`。HTML 应由 `build_site.py` 生成。

### 为什么 wrapper skills 没有自己的 scripts？

为了避免重复代码和版本漂移。wrapper 只负责自然语言触发，核心逻辑在 `conference-papers/scripts/`。

### 不下载图片能否图文同步？

可以。图文同步依赖 `figure.section`，不是依赖本地图片。外链图片也可以按 `method`、`experiments` 等 section 插入。

### 如何修改单篇论文页面？

修改：

```text
conference-papers/assets/site-template/paper-note.html
```

然后重新运行 `build_site.py`。

### 如何修改整体样式？

修改：

```text
conference-papers/assets/site-template/site.css
```

然后重新运行 `build_site.py`。
