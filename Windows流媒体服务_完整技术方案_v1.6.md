# Windows 流媒体服务开发需求完整技术方案

**文档版本**: 1.6  
**最后更新**: 2026-03-12

---

## 目录

1. [项目概述](#一项目概述)
2. [系统架构](#二系统架构)
3. [技术栈](#三技术栈)
4. [开发计划](#四开发计划)
5. [数据库详细设计](#五数据库详细设计)
6. [模块详细设计](#六模块详细设计)
7. [Windows 绿色部署方案](#七windows-绿色部署方案)
8. [前端界面功能设计](#八前端界面功能设计)
9. [附录A：术语表](#附录a术语表)
10. [附录B：非功能性需求](#附录b非功能性需求nfr)
11. [附录C：错误处理与降级策略](#附录c错误处理与降级策略)
12. [附录D：核心业务流程状态机](#附录d核心业务流程状态机)
13. [附录E：API接口契约](#附录eapi接口契约)
14. [附录F：测试策略](#附录f测试策略)
15. [附录G：部署与运维指南](#附录g部署与运维指南)
16. [附录H：第三方服务管理](#附录h第三方服务管理)
17. [附录I：用户交互设计规范](#附录i用户交互设计规范)
18. [附录J：发布检查清单](#附录j发布检查清单)
19. [附录K：数据库迁移指南](#附录k数据库迁移指南)
20. [附录L：性能优化指南](#附录l性能优化指南)
21. [附录M：安全加固指南](#附录m安全加固指南)

---

## 一、项目概述

### 1.1 项目背景

Windows 流媒体服务是一个基于 Python 技术栈开发的本地媒体资源管理工具，旨在帮助用户自动化地扫描、识别、整理和下载媒体资源。

### 1.2 核心目标

| 目标 | 说明 |
|-----|------|
| 自动化 | 减少人工干预，实现媒体资源的自动管理 |
| 智能化 | 利用 AI 技术提升识别准确率 |
| 可扩展 | 通过插件机制支持功能扩展 |
| 易用性 | 提供清晰的反馈和通知机制 |

### 1.3 运行环境

- **操作系统**: Windows 10/11
- **Python 版本**: 3.9+
- **硬件要求**: 4GB+ RAM, 10GB+ 磁盘空间

---

## 二、系统架构

### 2.1 整体架构

系统采用分层架构设计，包含应用接口层、业务逻辑层、数据访问层和外部集成层。业务逻辑层进一步划分为核心功能层、基础功能层和支撑功能层。

### 2.2 模块划分

| 层级 | 模块 | 模块ID | 功能定位 |
|-----|------|-------|---------|
| 基础功能层 | 本地文件扫描 | scanner | 扫描本地媒体文件 |
| 基础功能层 | 网络媒体信息获取 | media_fetcher | 查询网络数据源 |
| 核心功能层 | 本地媒体文件整理 | organizer | 整理和重命名文件 |
| 核心功能层 | 媒体识别增强 | ai_recognizer | AI辅助识别 |
| 核心功能层 | 媒体资源下载 | downloader | 管理下载任务 |
| 支撑功能层 | 服务状态反馈 | notification | 消息通知 |
| 支撑功能层 | 定时任务调度 | scheduler | 定时任务管理 |
| 支撑功能层 | 外部插件接口 | plugin_system | 插件扩展机制 |
| 支撑功能层 | 配置管理 | config_manager | 统一配置中枢 |
| 支撑功能层 | 监控与告警 | monitor_service | 系统健康保障 |
| 支撑功能层 | 媒体服务器集成 | media_server_integration | 生态对接 |
| 支撑功能层 | 数据备份恢复 | backup_manager | 数据安全保障 |
| 核心功能层 | 重复文件检测 | duplicate_detector | 存储优化 |
| 支撑功能层 | 数据统计可视化 | statistics_service | 数据洞察 |
| 核心功能层 | 媒体转码处理 | transcode_service | 格式统一与优化 |
| 支撑功能层 | 权限与安全管理 | security_manager | 系统安全基石 |
| 支撑功能层 | 多语言国际化 | i18n_service | 全球化支持 |

---

## 三、技术栈

### 3.1 核心依赖（MVP必需）

| 类别 | 依赖包 | 用途 |
|-----|-------|------|
| 基础框架 | python>=3.9, pydantic>=2.0 | 数据验证 |
| Web服务器 | uvicorn[standard]>=0.24.0 | ASGI服务器，推荐--workers 4 |
| 文件处理 | pathlib, watchdog>=3.0 | 路径操作与文件监控 |
| 异步文件 | aiofiles>=23.0.0 | 异步文件读写 |
| 媒体处理 | pymediainfo>=6.0 | 媒体元数据提取 |
| 网络请求 | httpx>=0.25 | 异步HTTP请求（替代requests） |
| 数据库 | sqlalchemy>=2.0, alembic>=1.12 | ORM与数据库迁移 |
| 任务队列 | BackgroundTasks (FastAPI内置) | 后台任务队列 |
| 配置管理 | pyyaml>=6.0, python-jsonschema | YAML配置解析与校验 |
| 日志监控 | loguru>=0.7 | 日志记录 |
| 加密安全 | cryptography>=41.0 | 敏感信息加密（Fernet） |
| 缓存 | cachetools>=5.3 | TMDB查询结果缓存 |

### 3.2 可选依赖（后续阶段）

| 类别 | 依赖包 | 用途 | 阶段 |
|-----|-------|------|------|
| 监控指标 | psutil>=5.9, prometheus-client | 系统监控与指标导出 | 增强阶段 |
| AI/ML | openai>=1.0 | AI辅助识别（可选插件） | 增强阶段 |
| 图像处理 | imagehash>=4.3, pillow>=10.0 | 感知哈希/重复检测 | 增强阶段 |
| 数据可视化 | matplotlib>=3.8, plotly>=5.18 | 统计图表生成 | 生态阶段 |

### 3.3 移除的依赖（根据优化建议）

| 原依赖包 | 移除原因 | 替代方案 |
|---------|---------|---------|
| ~~requests>=2.31~~ | 同步阻塞 | 使用httpx异步请求 |
| ~~apscheduler>=3.10~~ | 复杂度过高 | 使用FastAPI BackgroundTasks |
| ~~ffmpeg-python~~ | 不建议实现转码 | 使用专业工具HandBrake |
| ~~bcrypt>=4.1~~ | 仅简单管理员密码 | cryptography.fernet加密 |
| ~~pyjwt>=2.8, python-jose>=3.3~~ | 单机无需JWT | 简单session认证 |
| ~~babel>=2.13, python-i18n>=0.3~~ | 仅简体中文 | 硬编码中文，后续社区贡献 |

---

## 四、开发计划

### 4.1 MVP策略说明

**核心原则**：先做"整理助手"，再做"媒体中心"。

采用分阶段迭代开发，优先实现核心闭环功能，后续逐步增强。

### 4.2 阶段划分

#### 第一阶段（MVP - 核心闭环）- Week 1-8

**目标**：实现"扫描 -> 识别 -> 整理"的最小闭环，解决用户手动整理文件的痛点。

| 功能模块 | 实现内容 | 优先级 |
|---------|---------|--------|
| 文件扫描 | 本地文件扫描、增量扫描、文件系统监控 | P0 |
| 网络识别 | TMDB数据源集成、关键词规则、季集提取 | P0 |
| 文件整理 | 重命名/移动/硬链接、命名规则模板、目录规则 | P0 |
| 基础配置 | YAML配置、配置热重载、Web配置界面 | P0 |
| 简单认证 | 单管理员密码（无复杂RBAC） | P1 |

**砍掉/延后功能**：
- ❌ AI识别（延后到第二阶段，作为可选插件）
- ❌ 媒体下载（延后到第二阶段）
- ❌ 转码处理（不建议实现，使用专业工具如HandBrake）
- ❌ 重复检测（延后到第二阶段）
- ❌ 监控告警（延后，基础监控仅CPU/内存/磁盘）
- ❌ 媒体服务器集成（延后到第三阶段）
- ❌ 多语言国际化（仅简体中文，后续社区贡献）

#### 第二阶段（增强版）- Week 9-16

**目标**：增强核心功能，提升自动化能力。

| 功能模块 | 实现内容 | 优先级 |
|---------|---------|--------|
| 媒体下载 | 调用外部下载工具（qBittorrent等）、RSS订阅 | P1 |
| AI识别 | 作为可选插件，支持OpenAI/Kimi等 | P2 |
| 重复检测 | 文件哈希比对、相似度检测 | P2 |
| 基础监控 | CPU/内存/磁盘监控、简单告警 | P2 |
| 识别规则引擎 | 更完善的命名模板、自定义规则 | P1 |
| 数据备份 | 数据库自动备份、配置导出 | P2 |

#### 第三阶段（生态版）- Week 17-24

**目标**：与媒体中心生态对接，提升用户体验。

| 功能模块 | 实现内容 | 优先级 |
|---------|---------|--------|
| 媒体服务器集成 | Jellyfin/Emby/Plex库刷新、元数据同步 | P2 |
| 通知服务 | 企业微信/钉钉/邮件通知 | P2 |
| 数据统计 | 媒体库统计、下载统计、简单可视化 | P3 |

### 4.3 不建议实现的功能

| 功能 | 原因 | 替代方案 |
|-----|------|---------|
| **媒体转码** | 技术难度极高，易导致系统臃肿，属于专业工具领域 | 使用HandBrake、ShanaEncoder等专业工具 |
| **复杂权限系统** | Windows单机软件通常只有单一用户，RBAC属于过度设计 | 仅保留简单管理员密码 |
| **多语言国际化** | 初期用户群体明确，增加开发和维护成本 | 初期仅简体中文，后续社区贡献 |
| **内置监控时序数据库** | SQLite不适合存储大量时序数据 | 使用Prometheus抓取/metrics端点，或轮转日志文件 |

---

## 五、数据库详细设计

### 5.1 数据库配置

| 配置项 | 默认值 | 说明 |
|-------|-------|------|
| 数据库路径 | ./data/media_service.db | SQLite数据库文件路径 |
| 连接池大小 | 1 | SQLite串行化写入，避免锁竞争；高频读取使用连接池 |
| 连接超时 | 30秒 | 连接超时时间 |
| 回显SQL | False（生产） | 是否打印SQL语句 |

**监控数据处理**（根据优化建议）：
- ❌ 不使用 `metrics_time_series` 表存储监控数据
- ✅ 使用 `prometheus_client` 直接暴露 `/metrics` 端点
- ✅ 或由 Grafana Agent 抓取
- ✅ 备选方案：监控数据写入轮转日志文件（如 `metrics-2023-10-27.log`）

### 5.2 数据表清单

**图例**：🟢 MVP阶段（必需） 🟡 增强阶段 🟠 生态阶段 ❌ 不建议实现

| 序号 | 表名 | 中文名 | 阶段 | 说明 | 记录数预估 |
|-----|------|-------|------|------|-----------|
| 1 | media_files | 媒体文件表 | 🟢 | 存储扫描的媒体文件信息 | 10万+ |
| 2 | subtitle_files | 字幕文件表 | 🟢 | 存储字幕文件及关联关系 | 5万+ |
| 3 | recognition_results | 识别结果表 | 🟢 | 存储网络识别的媒体信息 | 10万+ |
| 4 | organize_tasks | 整理任务表 | 🟢 | 存储文件整理任务 | 1万+ |
| 5 | scan_history | 扫描历史表 | 🟢 | 存储扫描操作历史 | 1000+ |
| 6 | keyword_libraries | 关键词库表 | 🟢 | 定义不同类型的关键词库 | 10 |
| 7 | keyword_rules | 关键词规则表 | 🟢 | 存储具体的关键词规则 | 500+ |
| 8 | keyword_mappings | 关键词映射表 | 🟢 | 存储手动映射关系 | 1000+ |
| 9 | season_episode_rules | 季集提取规则表 | 🟢 | 存储季数和剧集提取规则 | 20+ |
| 10 | notification_logs | 通知日志表 | 🟢 | 存储通知发送记录 | 10万+ |
| 11 | config_history | 配置历史表 | 🟢 | 存储配置变更历史 | 1000+ |
| 12 | operation_logs | 通用操作日志表 | 🟢 | 存储所有模块操作日志 | 10万+ |
| 13 | download_tasks | 下载任务表 | 🟡 | 存储下载任务信息 | 5000+ |
| 14 | ai_service_configs | AI服务配置表 | 🟡 | 存储AI服务提供商配置 | 5+ |
| 15 | ai_recognition_logs | AI识别日志表 | 🟡 | 存储AI识别请求和响应 | 10万+ |
| 16 | duplicate_groups | 重复文件组表 | 🟡 | 存储重复文件组信息 | 1000+ |
| 17 | duplicate_items | 重复文件项表 | 🟡 | 存储重复文件明细 | 5000+ |
| 18 | backup_history | 备份历史表 | 🟡 | 存储备份任务记录 | 100+ |
| 19 | media_server_configs | 媒体服务器配置表 | 🟠 | 存储媒体服务器连接配置 | 5+ |
| 20 | media_server_libraries | 媒体服务器库映射表 | 🟠 | 存储库路径映射关系 | 20+ |
| 21 | statistics_summary | 统计汇总表 | 🟠 | 存储统计数据 | 1万+ |
| - | ~~metrics_time_series~~ | ~~监控指标时序表~~ | ❌ | ~~不建议使用SQLite存储~~ | - |
| - | ~~alert_rules~~ | ~~告警规则表~~ | ❌ | ~~延后实现~~ | - |
| - | ~~alert_history~~ | ~~告警历史表~~ | ❌ | ~~延后实现~~ | - |
| - | ~~transcode_tasks~~ | ~~转码任务表~~ | ❌ | ~~不建议实现~~ | - |
| - | ~~users~~ | ~~用户表~~ | ❌ | ~~仅保留简单管理员密码~~ | - |
| - | ~~audit_logs~~ | ~~审计日志表~~ | ❌ | ~~使用operation_logs替代~~ | - |
| - | ~~user_preferences~~ | ~~用户偏好表~~ | ❌ | ~~延后实现~~ | - |
| - | ~~media_info_i18n~~ | ~~媒体信息多语言表~~ | ❌ | ~~仅简体中文，延后实现~~ | - |

---

## 六、模块详细设计

### 6.1 本地文件扫描模块 🟢 MVP

**模块名称**: LocalFileScanner / 本地文件扫描器  
**功能定位**: 基础功能层 - 媒体资源发现入口  
**核心职责**: 遍历指定目录，识别并提取多媒体文件元数据  
**实现阶段**: 第一阶段（MVP）必需

#### 6.1.1 支持的文件扩展名

| 扩展名 | 类型 | 说明 |
|-------|------|------|
| .mp4 | 视频 | MPEG-4 Part 14 |
| .mkv | 视频 | Matroska Video Container |
| .avi | 视频 | Audio Video Interleave |
| .mov | 视频 | QuickTime File Format |
| .rmvb | 视频 | RealMedia Variable Bitrate |
| .ts | 视频 | MPEG Transport Stream |
| .m2ts | 视频 | Blu-ray BDAV MPEG-2 Transport Stream |
| .mts | 视频 | AVCHD Transport Stream |
| .wmv | 视频 | Windows Media Video |
| .flv | 视频 | Flash Video |
| .webm | 视频 | WebM Video Format |
| .vob | 视频 | DVD Video Object |

#### 6.1.2 增量扫描机制

通过对比文件元数据实现增量扫描：
- 优先使用SHA-256哈希值比对（最可靠）
- 回退到文件大小+修改时间比对（快速比对）
- 对于大文件采用分块读取计算哈希，避免内存溢出

#### 6.1.3 扫描触发方式

| 触发方式 | 优先级 | 实时性 | 资源占用 | 适用场景 |
|---------|--------|--------|---------|---------|
| **文件系统监控** | P0 | 实时 | 中 | 主要触发方式，推荐 |
| **定时扫描** | P1 | 延迟 | 低 | 兜底机制，监控失效时使用 |
| **手动触发** | P2 | 即时 | 按需 | 用户主动操作 |
| **API触发** | P2 | 即时 | 按需 | 外部系统集成 |

### 6.2 网络媒体信息获取模块 🟢 MVP

**模块名称**: WebMediaInfoFetcher / 网络媒体信息获取器  
**功能定位**: 基础功能层 - 媒体元数据补充来源  
**核心职责**: 从互联网获取媒体正式发布名称、年份、演职员等信息  
**实现阶段**: 第一阶段（MVP）必需

#### 6.2.1 数据源分类

| 类型 | 数据源 |
|-----|--------|
| 电影数据源 | TMDB, IMDB, Douban |
| 剧集数据源 | TVDB, TMDB TV, Douban |
| 动漫数据源 | AniDB, MyAnimeList, Bangumi, TMDB Anime |

#### 6.2.2 关键词库系统

关键词库系统包含五类词库：

| 词库类型 | 作用 | 处理方式 |
|---------|------|---------|
| 替换词库 | 关键字替换 | 替换为标准名称 |
| 跳过词库 | 跳过识别 | 命中则跳过该文件 |
| 字幕组词库 | 去除字幕组标识 | 从文件名中删除 |
| 屏蔽词库 | 去除无关词汇 | 从文件名中删除 |
| 手动映射 | 强制指定媒体ID | 直接查询指定媒体 |

#### 6.2.3 多阶段识别流程

采用单来源多文件并行模式：
1. 以TMDB为主源进行并行查询
2. 识别失败的文件记录并更换来源重新查询
3. 所有来源均失败时进入AI辅助识别
4. AI辅助仍失败则记录为需人工辅助识别

#### 6.2.4 识别操作模式配置

系统支持两种识别操作模式，用户可根据需求灵活配置：

| 操作模式 | 说明 | 适用场景 |
|---------|------|---------|
| **自动模式** | 文件扫描完成后自动开始识别 | 无人值守、批量处理 |
| **手动模式** | 扫描完成后停止，等待用户选择文件进行识别 | 精细控制、确认后处理 |

### 6.3 本地媒体文件整理模块 🟢 MVP

**模块名称**: MediaFileOrganizer / 媒体文件整理器  
**功能定位**: 核心功能层 - 媒体资源规范化管理  
**核心职责**: 根据网络获取的标准信息，对本地文件进行重命名和目录整理  
**实现阶段**: 第一阶段（MVP）必需

#### 6.3.1 整理动作类型

| 动作 | 说明 |
|-----|------|
| RENAME | 仅重命名 |
| MOVE | 仅移动 |
| RENAME_AND_MOVE | 重命名+移动 |
| HARDLINK | 创建硬链接（保留原文件，在目标位置创建硬链接） |
| RENAME_AND_HARDLINK | 重命名+创建硬链接 |
| SKIP | 跳过 |
| DELETE | 删除（谨慎使用） |

#### 6.3.2 命名规则体系

系统支持用户自定义命名规则，使用 **Jinja2 3.1.x** 模板引擎进行渲染。

**可用命名变量**：

| 变量名 | 说明 | 示例值 |
|-------|------|--------|
| `{title}` | 媒体标题 | The Matrix |
| `{original_title}` | 原始标题 | 黑客帝国 |
| `{year}` | 发行年份 | 1999 |
| `{season}` | 季数（数字） | 1 |
| `{episode}` | 集数（数字） | 5 |
| `{episode_title}` | 剧集标题 | Pilot |
| `{quality}` | 视频质量 | 1080p, 4K |
| `{source}` | 视频来源 | BluRay, WEB-DL |
| `{codec}` | 视频编码 | x264, HEVC |
| `{audio}` | 音频编码 | AAC, DTS |
| `{release_group}` | 发布组 | SPARKS, RARBG |
| `{language}` | 语言 | zh, en |
| `{audio_language}` | 音频语言 | zh, en, ja |
| `{subtitle_language}` | 字幕语言 | zh, en, ja |
| `{country}` | 发行国家/地区 | CN, US, JP, KR |
| `{country_name}` | 国家/地区名称 | 中国, 美国, 日本 |
| `{region}` | 地区代码 | US, EU, Asia |
| `{resolution}` | 分辨率 | 1920x1080 |
| `{bitdepth}` | 位深 | 8bit, 10bit |
| `{hdr}` | HDR格式 | HDR, DV |
| `{primary_category}` | 一级分类 | movie, tv, anime, undefined |
| `{sub_category}` | 二级分类 | action, comedy, drama, pending, failed |
| `{genre}` | 类型/流派 | 动作, 喜剧, 科幻 |
| `{file_name}` | 原始文件名（含扩展名） | Movie.Name.2024.1080p.mkv |
| `{file_stem}` | 原始文件名（不含扩展名） | Movie.Name.2024.1080p |
| `{file_extension}` | 文件扩展名 | mkv, mp4 |
| `{genre_en}` | 类型英文 | Action, Comedy, Sci-Fi |
| `{content_rating}` | 内容分级 | PG-13, R, TV-MA |
| `{studio}` | 制作公司 | Warner Bros, Netflix |

#### 6.3.3 目标目录配置

系统支持用户灵活配置媒体文件的目标整理目录，可按媒体类型、来源路径、标签等维度设置不同的目标位置。

**基础目录配置示例**：

```yaml
# directory_config.yaml 基础配置
target_directories:
  movie:
    primary: "D:/Media/电影"
    fallback: "E:/Media/电影"  # 主目录空间不足时使用
  tv:
    primary: "D:/Media/剧集"
  anime:
    primary: "D:/Media/动漫"
  documentary:
    primary: "D:/Media/纪录片"
```

#### 6.3.4 冲突解决策略

| 策略 | 说明 |
|-----|------|
| SKIP | 跳过 |
| OVERWRITE | 覆盖 |
| BACKUP | 备份后覆盖 |
| RENAME_NEW | 重命名新文件 |
| MERGE | 合并（剧集） |
| PROMPT | 提示用户 |

### 6.4 媒体识别增强模块 🟡 增强阶段

**模块名称**: AIEnhancedRecognizer / AI 增强识别器  
**功能定位**: 核心功能层 - 提升识别准确率  
**核心职责**: 利用 AI 能力处理模糊、不规范的媒体文件识别  
**实现阶段**: 第二阶段（增强）可选插件  
**说明**: 作为可选插件实现，非MVP必需功能

#### 6.4.1 AI增强识别场景

| 场景 | 说明 |
|-----|------|
| 模糊文件名识别 | 缩写/简称、缺失年份、拼写错误 |
| 非标准命名处理 | 无空格连接、特殊符号、广告水印 |
| 多语言混合识别 | 中英混合、日韩字符、音译差异 |
| 复杂文件识别 | 多版本区分、合集识别、特典/OVA |
| 智能纠错建议 | 相似结果推荐、人工确认流程、学习反馈 |

#### 6.4.2 AI接入架构

本应用主要使用**云端AI服务**，通过SDK或OpenAI规范接口接入。

**接入方式对比**:

| 接入方式 | 提供商 | 优点 | 缺点 | 推荐场景 |
|---------|-------|------|------|---------|
| **官方SDK** | OpenAI/Anthropic/百度等 | 功能完整、更新及时 | 依赖特定厂商 | 首选方案 |
| **OpenAI规范** | 兼容OpenAI API的第三方 | 统一接口、易切换 | 功能可能受限 | 备选方案 |
| **HTTP REST** | 通用REST API | 通用性强 | 需自行封装 | 特殊需求 |

#### 6.4.3 支持的AI服务提供商

| 提供商 | 接入方式 | SDK包 | API端点配置 |
|-------|---------|-------|------------|
| OpenAI | SDK + OpenAI规范 | `openai>=1.0` | `https://api.openai.com/v1` |
| Anthropic Claude | SDK | `anthropic` | `https://api.anthropic.com` |
| 百度文心一言 | SDK | `qianfan` | 百度智能云 |
| 阿里通义千问 | SDK + OpenAI规范 | `dashscope` | 阿里云 |
| 智谱GLM | SDK + OpenAI规范 | `zhipuai` | 智谱AI |
| DeepSeek | OpenAI规范 | `openai`兼容 | `https://api.deepseek.com/v1` |
| SiliconFlow | OpenAI规范 | `openai`兼容 | `https://api.siliconflow.cn/v1` |
| **Kimi (Moonshot)** | **OpenAI规范** | **`openai`兼容** | **`https://api.moonshot.cn/v1`** |

### 6.5 媒体资源下载模块 🟡 增强阶段

**模块名称**: MediaDownloader / 媒体资源下载器  
**功能定位**: 核心功能层 - 资源获取自动化  
**核心职责**: 调用 P2P 工具下载、RSS订阅内容获取  
**实现阶段**: 第二阶段（增强）  
**说明**: 调用外部成熟下载工具（qBittorrent等），非MVP必需

#### 6.5.1 P2P下载工具支持

| 工具 | 协议支持 | API方式 | 推荐场景 |
|-----|---------|---------|---------|
| qBittorrent | BitTorrent | Web API | 首选，功能全面 |
| Transmission | BitTorrent | RPC API | 轻量级，资源占用低 |
| Aria2 | HTTP/FTP/BitTorrent/Metalink | JSON-RPC | 多协议支持 |
| µTorrent | BitTorrent | Web UI | Windows用户熟悉 |

#### 6.5.2 下载任务状态

| 状态 | 说明 |
|-----|------|
| PENDING | 等待中 |
| QUEUED | 已入队 |
| DOWNLOADING | 下载中 |
| PAUSED | 已暂停 |
| COMPLETED | 已完成 |
| FAILED | 失败 |
| CANCELLED | 已取消 |

#### 6.5.3 下载来源

| 来源 | 说明 |
|-----|------|
| MAGNET | 磁力链接 |
| TORRENT_FILE | Torrent文件 |
| RSS | RSS订阅 |
| MANUAL | 手动添加 |

### 6.6 服务状态反馈模块 🟠 生态阶段

**模块名称**: NotificationService / 通知服务  
**功能定位**: 支撑功能层 - 服务运行状态监控  
**核心职责**: 向管理员推送服务状态、任务执行状况  
**实现阶段**: 第三阶段（生态）  
**说明**: 企业微信/钉钉/邮件通知，MVP阶段可使用本地日志替代

#### 6.6.1 通知场景

| 场景 | 说明 |
|-----|------|
| 服务状态通知 | 服务启动/停止、配置变更、连接状态、资源使用 |
| 任务执行通知 | 扫描完成、整理完成、下载进度、下载完成 |
| 异常告警通知 | 下载失败、识别失败、磁盘空间不足、网络异常 |
| 定时报告通知 | 每日统计、周/月汇总、存储预警 |
| 人工确认通知 | 低置信度识别、冲突待处理、异常待审核 |

#### 6.6.2 支持的通知渠道

| 渠道 | 接入方式 | 适用场景 |
|-----|---------|---------|
| 企业微信 | Webhook/应用 | 企业环境首选 |
| 飞书 | Webhook/机器人 | 字节系企业 |
| 钉钉 | Webhook/机器人 | 阿里系企业 |
| QQ | 第三方Bot/go-cqhttp | 个人用户 |
| Telegram | Bot API | 海外用户 |
| Webhook | HTTP POST | 自定义集成 |
| 邮件 | SMTP | 正式报告 |

#### 6.6.3 通知级别

| 级别 | 说明 |
|-----|------|
| DEBUG | 调试信息 |
| INFO | 普通信息 |
| SUCCESS | 成功通知 |
| WARNING | 警告 |
| ERROR | 错误 |
| CRITICAL | 严重错误 |

### 6.7 定时任务调度模块 🟢 MVP

**模块名称**: TaskScheduler / 任务调度器  
**功能定位**: 支撑功能层 - 自动化执行保障  
**核心职责**: 定时执行扫描、同步等核心功能  
**实现阶段**: 第一阶段（MVP）必需  
**技术选型**: 使用FastAPI BackgroundTasks替代APScheduler，简化架构

#### 6.7.1 定时任务类型

| 任务类型 | 说明 |
|---------|------|
| 目录扫描任务 | 定时扫描指定媒体目录、增量扫描、全量扫描 |
| RSS同步任务 | 定时检查订阅源更新、自动下载新资源 |
| 资源下载任务 | 定时启动队列中的下载、清理已完成任务 |
| 媒体整理任务 | 定时整理下载完成的文件、批量重命名队列 |
| 系统维护任务 | 数据库清理、日志归档、缓存清理、健康检查 |

#### 6.7.2 调度策略

| 策略 | 说明 | 示例 |
|-----|------|------|
| 固定间隔 | 每隔N时间执行 | 每30分钟 |
| Cron表达式 | 精确时间控制 | 每天02:00 |
| 触发式 | 事件触发 | 下载完成后 |
| 一次性 | 单次执行 | 指定时间执行一次 |

#### 6.7.3 任务状态

| 状态 | 说明 |
|-----|------|
| PENDING | 等待中 |
| RUNNING | 运行中 |
| COMPLETED | 已完成 |
| FAILED | 失败 |
| CANCELLED | 已取消 |
| PAUSED | 已暂停 |

### 6.8 外部插件接口模块 🟡 增强阶段

**模块名称**: PluginSystem / 插件系统  
**功能定位**: 支撑功能层 - 服务扩展能力  
**核心职责**: 提供标准化插件接口，支持功能扩展  
**实现阶段**: 第二阶段（增强）  
**说明**: AI识别等功能作为插件实现，保持核心简洁

#### 6.8.1 插件类型

| 类型 | 说明 |
|-----|------|
| 数据源插件 | 自定义媒体数据库接入、私有API接入、爬虫扩展 |
| 下载器插件 | 新P2P工具支持、网盘下载、直链下载 |
| 通知渠道插件 | 新IM平台支持、Webhook扩展 |
| 识别器插件 | 自定义AI模型、规则引擎扩展 |
| 处理器插件 | 字幕处理、格式转换、元数据写入、缩略图生成 |

#### 6.8.2 插件生命周期

发现 → 加载 → 初始化 → 运行 → 停止 → 卸载

#### 6.8.3 插件状态

| 状态 | 说明 |
|-----|------|
| DISCOVERED | 已发现 |
| LOADED | 已加载 |
| INITIALIZED | 已初始化 |
| RUNNING | 运行中 |
| ERROR | 错误 |
| STOPPED | 已停止 |

### 6.9 配置管理模块 🟢 MVP

**模块名称**: ConfigManager / 配置管理器  
**功能定位**: 支撑功能层 - 系统配置中枢  
**核心职责**: 统一管理所有配置项，支持热重载、版本控制和配置校验

#### 6.9.1 配置分类体系

| 配置类别 | 说明 | 存储方式 | 热重载 |
|---------|------|---------|--------|
| 系统配置 | 服务端口、日志级别、数据库连接 | YAML + 环境变量 | 部分支持 |
| 业务配置 | 扫描路径、命名规则、目录规则 | YAML + 数据库 | 完全支持 |
| 用户配置 | 界面主题、通知偏好、默认操作 | 数据库 | 完全支持 |
| 安全配置 | API密钥、加密密钥、访问令牌 | 加密存储 + 环境变量 | 不支持 |
| 运行时配置 | 任务状态、缓存数据、临时配置 | 内存 + Redis | 自动同步 |

#### 6.9.2 配置层级与优先级

配置采用多层覆盖机制，优先级从高到低：

```
1. 运行时参数（命令行）
2. 环境变量（OPENCLAW_*）
3. 用户配置（数据库）
4. 业务配置（config.d/*.yaml）
5. 系统配置（config.yaml）
6. 默认配置（代码内置）
```

#### 6.9.3 配置热重载机制

**热重载触发方式**：

| 触发方式 | 说明 | 适用场景 |
|---------|------|---------|
| 文件监听 | 配置文件变更自动检测 | 开发调试 |
| API调用 | POST /api/config/reload | 生产环境 |
| 定时检查 | 每30秒检查配置哈希 | 备用机制 |
| 事件触发 | 配置中心推送 | 分布式部署 |

#### 6.9.4 配置版本控制

**配置变更历史表** (config_history)：

| 字段名 | 类型 | 说明 |
|-------|------|------|
| id | INTEGER | 主键 |
| config_key | VARCHAR | 配置项键名 |
| old_value | TEXT | 旧值（敏感信息加密）|
| new_value | TEXT | 新值 |
| change_type | VARCHAR | 变更类型：create/update/delete |
| changed_by | VARCHAR | 变更用户/来源 |
| change_reason | VARCHAR | 变更原因 |
| created_at | DATETIME | 变更时间 |
| rolled_back | BOOLEAN | 是否已回滚 |

#### 6.9.5 配置校验机制

**校验规则类型**：

| 规则类型 | 说明 | 示例 |
|---------|------|------|
| required | 必填项 | `database.url` 不能为空 |
| type | 类型检查 | `server.port` 必须是整数 |
| range | 范围限制 | `temperature` 必须在 0-1 之间 |
| pattern | 正则匹配 | `naming_rules.pattern` 必须是有效 Jinja2 |
| path | 路径验证 | `target_directories.movie` 必须存在 |
| enum | 枚举值 | `log_level` 必须是 debug/info/warning/error |
| custom | 自定义校验 | 命名规则变量有效性检查 |

#### 6.9.6 Web 配置界面

**配置管理 API**：

| 接口 | 方法 | 说明 |
|-----|------|------|
| /api/config | GET | 获取完整配置（脱敏）|
| /api/config/{key} | GET | 获取单个配置项 |
| /api/config/{key} | PUT | 更新配置项 |
| /api/config/reload | POST | 触发配置热重载 |
| /api/config/history | GET | 获取配置变更历史 |
| /api/config/rollback/{id} | POST | 回滚到指定版本 |
| /api/config/validate | POST | 校验配置有效性 |
| /api/config/export | GET | 导出配置 |
| /api/config/import | POST | 导入配置 |

### 6.10 监控与告警模块 🟡 增强阶段

**模块名称**: MonitorService / 监控服务  
**功能定位**: 支撑功能层 - 系统健康保障  
**核心职责**: 实时监控系统状态，自动发现并告警异常

#### 6.10.1 监控指标体系

**系统资源监控**：

| 指标类别 | 具体指标 | 采集频率 | 告警阈值 |
|---------|---------|---------|---------|
| CPU | 使用率、负载平均值 | 30秒 | >80% 警告，>95% 严重 |
| 内存 | 使用率、可用内存、交换分区 | 30秒 | >85% 警告，>95% 严重 |
| 磁盘 | 使用率、IO 延迟、读写速率 | 60秒 | >85% 警告，>95% 严重 |
| 网络 | 带宽使用、连接数、延迟 | 30秒 | 根据基线动态 |

**应用性能监控**：

| 指标类别 | 具体指标 | 采集方式 |
|---------|---------|---------|
| 服务状态 | 各模块健康状态 | 主动探测 |
| 响应时间 | API 请求耗时 | 中间件埋点 |
| 错误率 | HTTP 5xx 比例、异常数量 | 日志分析 |
| 吞吐量 | 每秒请求数、任务处理数 | 计数器 |
| 队列深度 | 待处理任务数量 | 定时采样 |

**业务指标监控**：

| 指标类别 | 具体指标 | 说明 |
|---------|---------|------|
| 扫描统计 | 扫描文件数、识别成功率 | 每小时汇总 |
| 整理统计 | 整理文件数、失败率 | 每小时汇总 |
| 下载统计 | 下载速度、完成率、种子健康度 | 实时 |
| AI识别 | Token 消耗、响应时间、成本 | 每次调用 |
| 数据库 | 查询耗时、连接池使用率 | 持续 |

#### 6.10.2 健康检查机制

**健康检查类型**：

```yaml
health_checks:
  # 存活检查（Kubernetes livenessProbe）
  liveness:
    enabled: true
    interval: 10s
    timeout: 5s
    failure_threshold: 3

  # 就绪检查（Kubernetes readinessProbe）
  readiness:
    enabled: true
    interval: 5s
    timeout: 3s
    failure_threshold: 3

  # 启动检查（防止启动时过早接收流量）
  startup:
    enabled: true
    interval: 5s
    timeout: 3s
    failure_threshold: 30
```

#### 6.10.3 告警规则引擎

**告警级别定义**：

| 级别 | 颜色 | 响应时间 | 通知方式 |
|-----|------|---------|---------|
| P0 - 紧急 | 🔴 | 立即 | 电话+短信+所有渠道 |
| P1 - 严重 | 🟠 | 5分钟内 | 短信+即时通讯+邮件 |
| P2 - 警告 | 🟡 | 30分钟内 | 即时通讯+邮件 |
| P3 - 提示 | 🔵 | 24小时内 | 邮件+系统通知 |

### 6.11 媒体服务器集成模块 🟠 生态阶段

**模块名称**: MediaServerIntegration / 媒体服务器集成  
**功能定位**: 支撑功能层 - 生态对接  
**核心职责**: 与主流媒体服务器无缝对接，实现库刷新、元数据同步等功能

#### 6.11.1 支持的媒体服务器

| 服务器 | 版本要求 | API类型 | 功能支持 |
|-------|---------|---------|---------|
| Jellyfin | 10.8+ | REST API | ⭐⭐⭐⭐⭐ 完全支持 |
| Emby | 4.7+ | REST API | ⭐⭐⭐⭐⭐ 完全支持 |
| Plex | 1.32+ | REST API | ⭐⭐⭐⭐☆ 部分功能需 Plex Pass |
| Kodi | 20+ | JSON-RPC | ⭐⭐⭐☆☆ 基础支持 |

#### 6.11.2 核心集成功能

**库管理功能**：

| 功能 | Jellyfin | Emby | Plex | Kodi |
|-----|---------|------|------|------|
| 刷新媒体库 | ✅ | ✅ | ✅ | ✅ |
| 扫描新文件 | ✅ | ✅ | ✅ | ⚠️ 需插件 |
| 元数据更新 | ✅ | ✅ | ✅ | ⚠️ 需 NFO |
| 观看状态同步 | ✅ | ✅ | ✅ | ❌ |
| 播放列表管理 | ✅ | ✅ | ⚠️ 有限 | ❌ |
| 用户管理 | ✅ | ✅ | ⚠️ 需 Pass | ❌ |

### 6.12 数据备份与恢复模块 🟡 增强阶段

**模块名称**: BackupManager / 备份管理器  
**功能定位**: 支撑功能层 - 数据安全保障  
**核心职责**: 提供数据库、配置和元数据的自动备份与灾难恢复能力

#### 6.12.1 备份内容分类

| 备份类型 | 内容 | 频率建议 | 保留策略 |
|---------|------|---------|---------|
| 数据库备份 | SQLite数据库文件 | 每日 | 保留30天 |
| 配置备份 | 所有YAML配置文件 | 配置变更时 | 保留50个版本 |
| 元数据备份 | 识别结果、手动映射 | 每周 | 保留12周 |
| 完整备份 | 数据库+配置+元数据 | 每月 | 保留6个月 |

#### 6.12.2 备份策略配置

```yaml
backup_config:
  enabled: true

  # 备份存储路径
  backup_path: "./backups"

  # 自动备份策略
  auto_backup:
    database:
      enabled: true
      cron: "0 3 * * *"  # 每天凌晨3点
      retention_days: 30

    config:
      enabled: true
      on_change: true  # 配置变更时自动备份
      retention_count: 50

    full:
      enabled: true
      cron: "0 4 1 * *"  # 每月1号凌晨4点
      retention_months: 6
```

### 6.13 重复文件检测模块 🟡 增强阶段

**模块名称**: DuplicateDetector / 重复文件检测器  
**功能定位**: 核心功能层 - 存储优化  
**核心职责**: 检测并处理重复的媒体文件，节省存储空间

#### 6.13.1 重复检测算法

**检测维度**：

| 检测方式 | 算法 | 准确度 | 性能 | 适用场景 |
|---------|------|--------|------|---------|
| 文件哈希 | SHA-256/BLAKE3 | 100% | 快 | 完全相同的文件 |
| 感知哈希 | pHash/dHash | 85-95% | 中等 | 相似视频（不同压制）|
| 视频指纹 | 关键帧比对 | 90-98% | 慢 | 内容相同质量不同 |
| 元数据比对 | 标题+年份+时长 | 70-85% | 快 | 初步筛选 |

#### 6.13.2 重复处理策略

**处理动作**：

| 动作 | 说明 | 适用场景 |
|-----|------|---------|
| HARDLINK | 创建硬链接 | 保留多个路径，节省空间 |
| DELETE | 删除重复项 | 保留质量最高的版本 |
| MOVE | 移动到隔离区 | 待人工确认 |
| TAG | 仅标记不处理 | 后续人工处理 |

### 6.14 数据统计与可视化模块 🟠 生态阶段

**模块名称**: StatisticsService / 统计服务  
**功能定位**: 支撑功能层 - 数据洞察  
**核心职责**: 提供媒体库统计、下载分析、系统运行数据的可视化展示

#### 6.14.1 统计指标体系

**媒体库统计**：

| 指标 | 说明 | 计算方式 |
|-----|------|---------|
| 总文件数 | 媒体文件总数 | COUNT(media_files) |
| 总容量 | 媒体库占用空间 | SUM(file_size) |
| 类型分布 | 电影/剧集/动漫占比 | GROUP BY media_type |
| 质量分布 | 1080p/4K/720p占比 | 解析度分组统计 |
| 年代分布 | 按年份统计 | GROUP BY year |
| 识别率 | 已识别/未识别比例 | 识别状态统计 |
| 增长趋势 | 每日/每周新增文件 | 时间序列统计 |

**下载统计**：

| 指标 | 说明 |
|-----|------|
| 下载任务数 | 总任务/进行中/已完成 |
| 下载速度趋势 | 平均速度/峰值速度 |
| 来源分布 | 磁力/Torrent/RSS占比 |
| 成功率 | 成功/失败比例 |
| 空间效率 | 下载量/实际保存量 |

**系统运行统计**：

| 指标 | 说明 |
|-----|------|
| 扫描效率 | 文件数/扫描时间 |
| 识别成功率 | 网络识别/AI识别成功率 |
| 整理成功率 | 整理任务完成率 |
| API调用统计 | 各数据源调用次数/成功率 |
| AI成本统计 | Token消耗/费用 |

#### 6.14.2 统计报表类型

| 报表 | 周期 | 内容 |
|-----|------|------|
| 日报 | 每日 | 新增文件、下载完成、识别统计 |
| 周报 | 每周 | 周趋势、分类汇总、TOP10 |
| 月报 | 每月 | 月度增长、成本分析、存储预警 |
| 年报 | 每年 | 年度总结、趋势分析 |

#### 6.14.3 可视化图表

**仪表盘组件**：

| 图表类型 | 用途 |
|---------|------|
| 饼图/环形图 | 类型分布、质量分布 |
| 柱状图 | 年代分布、月度增长 |
| 折线图 | 趋势变化、下载速度 |
| 热力图 | 每日活动分布 |
| 词云 | 热门类型、常用标签 |
| 地图 | 地区分布（如有）|

### 6.15 媒体转码处理模块 ❌ 不建议实现

**模块名称**: TranscodeService / 转码服务  
**功能定位**: 核心功能层 - 格式统一与优化  
**核心职责**: 提供媒体文件格式转换、压缩优化、设备适配等转码能力  
**实现阶段**: ❌ 不建议实现  
**原因**: 技术难度极高，易导致系统臃肿，属于专业工具（如HandBrake、ShanaEncoder）的领域  
**替代方案**: 推荐用户使用专业转码工具，本系统仅做媒体管理

### 6.16 权限与安全管理模块 🟢 MVP简化版

**模块名称**: SecurityManager / 安全管理器  
**功能定位**: 支撑功能层 - 系统安全基石  
**核心职责**: 提供简单管理员密码、数据加密等基础安全能力  
**实现阶段**: 第一阶段（MVP）简化版  
**说明**: Windows单机软件，无需复杂RBAC权限系统，仅保留简单管理员密码即可

#### 6.16.1 用户认证体系

**认证方式**：

| 方式 | 说明 | 适用场景 |
|-----|------|---------|
| 本地认证 | 用户名+密码 | 单用户/家庭使用 |
| JWT Token | API访问令牌 | 第三方集成 |
| API Key | 应用级认证 | 自动化脚本 |

#### 6.16.2 权限控制模型

**RBAC权限模型**：

| 角色 | 权限范围 |
|-----|---------|
| admin | 所有权限（系统管理、用户管理、配置修改）|
| operator | 操作权限（扫描、识别、整理、下载管理）|
| viewer | 只读权限（查看媒体库、统计报表）|
| guest | 受限访问（仅查看指定内容）|

#### 6.16.3 审计日志

**审计事件类型**：

| 类别 | 事件 |
|-----|------|
| 认证 | login / logout / password_change / token_refresh |
| 用户 | user_create / user_update / user_delete / role_change |
| 媒体 | file_scan / file_organize / file_delete / metadata_update |
| 下载 | download_start / download_complete / download_cancel |
| 配置 | config_view / config_update / config_export |
| 系统 | backup_create / restore_execute / service_restart |

#### 6.16.4 数据安全

**敏感数据加密**：

| 数据类型 | 加密方式 | 密钥管理 |
|---------|---------|---------|
| 数据库密码 | AES-256-GCM | 环境变量 |
| API密钥 | AES-256-GCM | 密钥文件 |
| 用户密码 | bcrypt | 自动处理 |
| 备份文件 | AES-256-GCM | 备份密钥 |
| 会话令牌 | JWT签名 | JWT密钥 |

### 6.17 多语言国际化模块 ❌ 延后实现

**模块名称**: I18nService / 国际化服务  
**功能定位**: 支撑功能层 - 全球化支持  
**核心职责**: 提供界面多语言、媒体信息多语言、时区/日期格式适配  
**实现阶段**: ❌ 延后实现  
**说明**: 初期仅支持简体中文，后续通过社区贡献扩展多语言支持

#### 6.17.1 国际化架构

**语言支持范围**：

| 类型 | 说明 |
|-----|------|
| 界面语言 | Web界面、通知消息、日志输出 |
| 媒体信息语言 | 标题、简介、类型标签 |
| 日期时间格式 | 按地区习惯显示 |
| 数字格式 | 千分位、小数点、货币 |

**支持语言列表**：

| 语言代码 | 语言名称 | 完成度 |
|---------|---------|--------|
| zh-CN | 简体中文 | 100% |
| zh-TW | 繁体中文 | 100% |
| en-US | 英语（美国）| 100% |
| ja-JP | 日语 | 80% |
| ko-KR | 韩语 | 80% |
| de-DE | 德语 | 60% |
| fr-FR | 法语 | 60% |
| es-ES | 西班牙语 | 60% |

#### 6.17.2 语言包管理

**语言包结构**：

```
locales/
├── zh-CN/
│   ├── common.json      # 通用文本
│   ├── media.json       # 媒体相关
│   ├── download.json    # 下载相关
│   ├── settings.json    # 设置相关
│   └── errors.json      # 错误信息
├── en-US/
│   ├── common.json
│   ├── media.json
│   ├── download.json
│   ├── settings.json
│   └── errors.json
└── ...
```

#### 6.17.3 媒体信息多语言

**数据源多语言支持**：

| 数据源 | 多语言支持 | 配置方式 |
|-------|-----------|---------|
| TMDB | ✅ | `language=zh-CN` |
| 豆瓣 | ✅ | 自动返回中文 |
| TVDB | ✅ | `language=zh` |
| AniDB | ⚠️ | 有限支持 |

---

## 七、Windows 绿色部署方案

### 7.1 绿色部署设计原则

**核心目标**：实现应用与 Windows 系统的完全隔离，不对系统服务、注册表、环境变量造成任何变更。

| 原则 | 说明 | 实现方式 |
|-----|------|---------|
| **零注册表写入** | 不修改 Windows 注册表 | 使用本地配置文件替代注册表存储 |
| **零系统服务** | 不安装 Windows 服务 | 使用独立进程 + 启动脚本管理 |
| **零环境变量** | 不修改系统 PATH 等变量 | 使用相对路径和本地环境脚本 |
| **零系统目录** | 不写入 Windows/System32 等目录 | 所有文件集中在应用目录 |
| **便携自包含** | 所有依赖打包在应用目录 | Python 嵌入式 + 依赖本地安装 |

### 7.2 目录结构设计

```
MediaService/                          # 应用根目录
├── app/                               # 应用核心代码
│   ├── core/                          # 核心业务逻辑
│   ├── modules/                       # 功能模块
│   ├── api/                           # API 接口
│   └── web/                           # Web 界面
├── data/                              # 数据目录（运行时创建）
│   ├── db/                            # SQLite 数据库
│   ├── cache/                         # 缓存文件
│   ├── logs/                          # 日志文件
│   ├── temp/                          # 临时文件
│   └── backups/                       # 备份文件
├── config/                            # 配置文件目录
│   ├── app.yaml                       # 主配置
│   ├── naming_rules.yaml              # 命名规则
│   └── ...                            # 其他配置
├── python/                            # 嵌入式 Python
│   ├── python.exe                     # Python 解释器
│   ├── python3.dll                    # Python 核心 DLL
│   ├── Lib/                           # 标准库
│   ├── Lib/site-packages/             # 第三方依赖
│   └── Scripts/                       # 脚本工具
├── runtime/                           # 运行时依赖
│   ├── ffmpeg/                        # FFmpeg 工具
│   ├── mediainfo/                     # MediaInfo 工具
│   └── ...                            # 其他工具
├── scripts/                           # 批处理脚本
│   ├── start.bat                      # 启动脚本
│   ├── stop.bat                       # 停止脚本
│   ├── install.bat                    # 安装脚本（创建启动项）
│   ├── uninstall.bat                  # 卸载脚本（移除启动项）
│   ├── status.bat                     # 状态检查脚本
│   └── service.vbs                    # Windows 启动辅助脚本
├── logs/                              # 应用日志目录
├── MediaService.exe                   # 启动器（可选，PyInstaller 打包）
├── README.md                          # 使用说明
└── LICENSE                            # 许可证
```

### 7.3 嵌入式 Python 环境

#### 7.3.1 Python 嵌入式版本部署

**获取嵌入式 Python**：
```powershell
# 下载地址：https://www.python.org/downloads/windows/
# 选择 "Windows embeddable package (64-bit)"
# 版本：Python 3.11.x (与开发版本一致)
```

**本地 pip 安装配置**：
```ini
; python/python311._pth 文件内容
python311.zip
.
Lib\site-packages

; 添加以下行启用 pip
import site
```

**依赖安装脚本** (`scripts/setup_deps.bat`)：
```batch
@echo off
chcp 65001 >nul
title MediaService - 安装依赖

set "APP_DIR=%~dp0.."
set "PYTHON=%APP_DIR%\python\python.exe"
set "PIP=%APP_DIR%\python\Scripts\pip.exe"

echo [INFO] 正在安装 Python 依赖...

"%PYTHON%" -m ensurepip --upgrade
"%PIP%" install --upgrade pip

"%PIP%" install -r "%APP_DIR%equirements.txt" --target="%APP_DIR%\python\Lib\site-packages"

echo [INFO] 依赖安装完成
pause
```

**requirements.txt**（核心依赖）：
```
fastapi>=0.104.0
uvicorn[standard]>=0.24.0
pydantic>=2.0.0
sqlalchemy>=2.0.0
alembic>=1.12.0
aiofiles>=23.0.0
httpx>=0.25.0
watchdog>=3.0.0
pyyaml>=6.0
loguru>=0.7.0
jinja2>=3.1.0
python-multipart>=0.0.6
websockets>=12.0
psutil>=5.9.0
```

### 7.4 启动与停止机制

#### 7.4.1 应用启动脚本 (`scripts/start.bat`)

```batch
@echo off
chcp 65001 >nul
setlocal EnableDelayedExpansion

:: 设置应用目录
set "APP_DIR=%~dp0.."
set "APP_DIR=%APP_DIR:\=/%"
set "PYTHON=%APP_DIR%/python/python.exe"
set "APP_SCRIPT=%APP_DIR%/app/main.py"
set "PID_FILE=%APP_DIR%/data/app.pid"
set "LOG_FILE=%APP_DIR%/logs/service.log"

:: 创建必要目录
if not exist "%APP_DIR%/data" mkdir "%APP_DIR%/data"
if not exist "%APP_DIR%/logs" mkdir "%APP_DIR%/logs"
if not exist "%APP_DIR%/data/db" mkdir "%APP_DIR%/data/db"
if not exist "%APP_DIR%/data/cache" mkdir "%APP_DIR%/data/cache"
if not exist "%APP_DIR%/data/temp" mkdir "%APP_DIR%/data/temp"

:: 检查是否已在运行
call :check_running
if %ERRORLEVEL% == 1 (
    echo [WARNING] 服务已在运行中
    exit /b 1
)

echo [INFO] 正在启动 MediaService...
echo [INFO] 应用目录: %APP_DIR%

:: 设置环境变量（仅当前进程）
set "MEDIA_SERVICE_HOME=%APP_DIR%"
set "PYTHONPATH=%APP_DIR%/app;%APP_DIR%/python/Lib/site-packages"
set "PATH=%APP_DIR%/python;%APP_DIR%/runtime/ffmpeg;%PATH%"

:: 启动应用（后台运行）
start /B "" "%PYTHON%" "%APP_SCRIPT%" --config "%APP_DIR%/config/app.yaml" >> "%LOG_FILE%" 2>&1

:: 获取 PID 并保存
for /f "tokens=2" %%a in ('tasklist ^| findstr /i "python.exe" ^| findstr /i "%APP_SCRIPT%"') do (
    echo %%a > "%PID_FILE%"
    echo [INFO] 服务已启动，PID: %%a
    goto :started
)

:started
timeout /t 2 >nul

:: 验证启动状态
call :check_running
if %ERRORLEVEL% == 1 (
    echo [SUCCESS] 服务启动成功
    echo [INFO] 访问地址: http://localhost:8000
) else (
    echo [ERROR] 服务启动失败，请检查日志: %LOG_FILE%
    exit /b 1
)

exit /b 0

:check_running
if exist "%PID_FILE%" (
    set /p PID=<"%PID_FILE%"
    tasklist /FI "PID eq !PID!" 2>nul | findstr /i "python.exe" >nul
    if !ERRORLEVEL! == 0 exit /b 1
)
exit /b 0
```

#### 7.4.2 应用停止脚本 (`scripts/stop.bat`)

```batch
@echo off
chcp 65001 >nul
setlocal EnableDelayedExpansion

set "APP_DIR=%~dp0.."
set "PID_FILE=%APP_DIR%/data/app.pid"

echo [INFO] 正在停止 MediaService...

if not exist "%PID_FILE%" (
    echo [WARNING] 未找到 PID 文件，尝试查找进程...
    call :kill_by_name
    exit /b 0
)

set /p PID=<"%PID_FILE%"
echo [INFO] 找到服务 PID: %PID%

:: 尝试优雅终止
taskkill /PID %PID% /T /FI "STATUS eq RUNNING" >nul 2>&1
timeout /t 3 >nul

:: 检查是否仍在运行
tasklist /FI "PID eq %PID%" 2>nul | findstr /i "python.exe" >nul
if %ERRORLEVEL% == 0 (
    echo [WARNING] 进程未响应，强制终止...
    taskkill /F /PID %PID% /T >nul 2>&1
)

del "%PID_FILE%" 2>nul
echo [SUCCESS] 服务已停止
exit /b 0

:kill_by_name
:: 通过进程名查找并终止
for /f "tokens=2" %%a in ('tasklist ^| findstr /i "python.exe"') do (
    taskkill /F /PID %%a /T >nul 2>&1
)
echo [SUCCESS] 已清理所有 Python 进程
exit /b 0
```

### 7.5 系统启动集成方案

#### 7.5.1 方案一：启动文件夹方式（推荐）

**安装脚本** (`scripts/install.bat`)：
```batch
@echo off
chcp 65001 >nul
setlocal EnableDelayedExpansion

set "APP_DIR=%~dp0.."
set "STARTUP_DIR=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup"
set "SCRIPT_NAME=MediaService-Start.vbs"

echo ========================================
echo    MediaService 安装程序
echo ========================================
echo.

:: 创建启动脚本
echo [INFO] 创建启动脚本...
(
echo Set WshShell = CreateObject^("WScript.Shell"^)
echo WshShell.Run """%APP_DIR%\scripts\start.bat""", 0, False
echo Set WshShell = Nothing
) > "%STARTUP_DIR%\%SCRIPT_NAME%"

echo [SUCCESS] 已添加到系统启动项
echo [INFO] 启动脚本位置: %STARTUP_DIR%\%SCRIPT_NAME%
echo.

:: 创建桌面快捷方式（可选）
echo [INFO] 创建桌面快捷方式...
set "DESKTOP=%USERPROFILE%\Desktop"
(
echo Set oWS = WScript.CreateObject^("WScript.Shell"^)
echo sLinkFile = "%DESKTOP%\MediaService.lnk"
echo Set oLink = oWS.CreateShortcut^(sLinkFile^)
echo oLink.TargetPath = "%APP_DIR%\scripts\start.bat"
echo oLink.WorkingDirectory = "%APP_DIR%\scripts"
echo oLink.IconLocation = "%APP_DIR%ppssets\icon.ico"
echo oLink.Description = "启动 MediaService"
echo oLink.Save
) > "%TEMP%\CreateShortcut.vbs"
cscript //nologo "%TEMP%\CreateShortcut.vbs"
del "%TEMP%\CreateShortcut.vbs"

echo [SUCCESS] 安装完成
echo.
echo 安装内容：
echo   - 系统启动项: %STARTUP_DIR%\%SCRIPT_NAME%
echo   - 桌面快捷方式: %DESKTOP%\MediaService.lnk
echo.
pause
```

**卸载脚本** (`scripts/uninstall.bat`)：
```batch
@echo off
chcp 65001 >nul

set "STARTUP_DIR=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup"
set "SCRIPT_NAME=MediaService-Start.vbs"
set "DESKTOP=%USERPROFILE%\Desktop"

echo ========================================
echo    MediaService 卸载程序
echo ========================================
echo.

:: 停止服务
call "%~dp0stop.bat"

:: 移除启动项
if exist "%STARTUP_DIR%\%SCRIPT_NAME%" (
    del "%STARTUP_DIR%\%SCRIPT_NAME%"
    echo [SUCCESS] 已移除系统启动项
) else (
    echo [INFO] 启动项不存在
)

:: 移除桌面快捷方式
if exist "%DESKTOP%\MediaService.lnk" (
    del "%DESKTOP%\MediaService.lnk"
    echo [SUCCESS] 已移除桌面快捷方式
)

echo.
echo [SUCCESS] 卸载完成
echo [INFO] 应用文件仍保留在: %~dp0..
echo [INFO] 如需完全删除，请手动删除应用目录
echo.
pause
```

### 7.6 配置文件设计

#### 7.6.1 主配置文件 (`config/app.yaml`)

```yaml
# MediaService 主配置文件
# 所有路径均使用相对路径，确保绿色部署

app:
  name: "MediaService"
  version: "1.3.0"
  debug: false

  # 目录配置（相对于应用根目录）
  paths:
    data: "./data"
    logs: "./logs"
    temp: "./data/temp"
    cache: "./data/cache"
    db: "./data/db"
    backups: "./data/backups"

  # 运行时文件
  runtime:
    pid_file: "./data/app.pid"
    lock_file: "./data/app.lock"

# 服务器配置
server:
  host: "127.0.0.1"
  port: 8000
  workers: 1  # 绿色部署使用单进程
  reload: false

# 数据库配置（SQLite，本地文件）
database:
  url: "sqlite:///./data/db/media_service.db"
  echo: false
  pool_size: 5

# 日志配置
logging:
  level: "INFO"
  format: "{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name} | {message}"
  rotation: "10 MB"
  retention: "30 days"
  files:
    app: "./logs/app.log"
    error: "./logs/error.log"
    access: "./logs/access.log"

# 扫描配置
scanner:
  watch_paths:
    - "D:/Downloads"  # 用户可修改为实际路径
  recursive: true
  interval: 300  # 秒

# 其他模块配置...
```

---

## 八、前端界面功能设计

### 8.1 功能模块总览

| 模块 | 功能数量 | 优先级 | 说明 |
|-----|---------|--------|------|
| 仪表盘 | 5 | P0 | 数据概览与快捷操作 |
| 媒体库管理 | 12 | P0 | 媒体文件浏览与管理 |
| 扫描管理 | 8 | P0 | 扫描任务与监控配置 |
| 识别管理 | 10 | P0 | 识别任务与结果管理 |
| 整理管理 | 8 | P0 | 整理任务与规则配置 |
| 下载管理 | 10 | P1 | 下载任务与RSS订阅 |
| 系统管理 | 15 | P1 | 进程/配置/用户管理 |
| 监控告警 | 8 | P2 | 监控图表与告警规则 |
| 数据库管理 | 10 | P1 | 数据库操作与维护 |
| **合计** | **76** | - | - |

### 8.2 仪表盘模块

#### 8.2.1 数据概览卡片

| 功能点 | 说明 | 数据来源 |
|-------|------|---------|
| 媒体统计 | 总文件数、总容量、识别率 | media_files表统计 |
| 类型分布 | 电影/剧集/动漫占比饼图 | media_files.media_type分组 |
| 质量分布 | 1080p/4K/720p分布柱状图 | 分辨率字段统计 |
| 增长趋势 | 近30天新增文件趋势折线图 | scan_history表 |
| 待处理提醒 | 待识别/待整理/下载中数量 | 各任务表统计 |

#### 8.2.2 快捷操作

| 功能点 | 操作 | 跳转目标 |
|-------|------|---------|
| 快速扫描 | 一键触发目录扫描 | 扫描管理页 |
| 查看待识别 | 查看未识别文件列表 | 识别管理页 |
| 查看下载进度 | 查看活跃下载任务 | 下载管理页 |

### 8.3 媒体库管理

#### 8.3.1 媒体文件列表

| 功能点 | 说明 | 相关API |
|-------|------|--------|
| 列表展示 | 表格展示媒体文件基本信息 | GET /api/media/files |
| 分页加载 | 支持分页，每页50/100/200条 | 分页参数 |
| 排序功能 | 按文件名/大小/时间/评分排序 | sort参数 |
| 筛选功能 | 按类型/年份/质量/识别状态筛选 | filter参数 |
| 搜索功能 | 关键词搜索文件名/标题 | search参数 |
| 列自定义 | 显示/隐藏列，调整列宽 | 前端配置 |

#### 8.3.2 媒体详情

| 功能点 | 说明 | 数据来源 |
|-------|------|---------|
| 基本信息 | 文件名/路径/大小/格式 | media_files表 |
| 元数据展示 | 标题/年份/剧情/演职员 | recognition_results表 |
| 海报展示 | 显示电影/剧集海报 | 图片URL |
| 识别结果对比 | 显示多个数据源的识别结果 | recognition_results表 |
| 操作历史 | 扫描/识别/整理历史 | operation_logs表 |
| 手动识别 | 手动输入媒体ID进行识别 | POST /api/recognition/manual |

#### 8.3.3 批量操作

| 功能点 | 说明 | 批量限制 |
|-------|------|---------|
| 批量识别 | 选择多个文件批量识别 | 最大50个 |
| 批量整理 | 选择多个文件批量整理 | 最大20个 |
| 批量删除 | 删除数据库记录（不删文件） | 最大100个 |
| 批量导出 | 导出媒体信息为Excel/CSV | 无限制 |

### 8.4 扫描管理

#### 8.4.1 扫描任务管理

| 功能点 | 说明 | 相关API |
|-------|------|--------|
| 任务列表 | 显示历史扫描任务 | GET /api/scan/tasks |
| 状态查看 | 显示任务进度/结果/耗时 | scan_history表 |
| 任务详情 | 查看任务扫描的文件明细 | scan_detail_logs表 |
| 取消任务 | 取消进行中的扫描任务 | POST /api/scan/{id}/cancel |
| 重新扫描 | 对失败文件重新扫描 | POST /api/scan/retry |

#### 8.4.2 手动触发扫描

| 功能点 | 说明 | 相关API |
|-------|------|--------|
| 目录选择 | 选择要扫描的目录 | 文件选择器 |
| 扫描选项 | 递归/增量/强制扫描选项 | POST /api/scan |
| 扫描预览 | 预览将要扫描的文件数量 | 预扫描API |
| 任务提交 | 提交扫描任务 | POST /api/scan/trigger |
| 实时进度 | WebSocket实时显示扫描进度 | WS /ws/scan/{id} |

#### 8.4.3 监控路径配置

| 功能点 | 说明 | 数据来源 |
|-------|------|---------|
| 路径列表 | 显示已配置的监控目录 | scanner_config |
| 添加路径 | 新增目录监控 | POST /api/config/scanner |
| 编辑路径 | 修改监控配置 | PUT /api/config/scanner |
| 删除路径 | 移除目录监控 | DELETE /api/config/scanner |
| 启用/禁用 | 临时启用或禁用监控 | 开关控制 |

### 8.5 识别管理

#### 8.5.1 识别任务管理

| 功能点 | 说明 | 相关API |
|-------|------|--------|
| 待识别列表 | 显示未识别或识别失败的文件 | GET /api/recognition/pending |
| 识别中列表 | 显示正在识别的文件 | GET /api/recognition/processing |
| 识别历史 | 显示识别记录和结果 | GET /api/recognition/history |
| 结果确认 | 确认或修正识别结果 | POST /api/recognition/confirm |

#### 8.5.2 手动识别

| 功能点 | 说明 | 相关API |
|-------|------|--------|
| 搜索媒体 | 在TMDB/豆瓣搜索媒体 | GET /api/search |
| 搜索结果展示 | 显示搜索结果列表 | 搜索结果 |
| 选择匹配结果 | 选择正确的识别结果 | POST /api/recognition/select |
| 手动输入ID | 直接输入TMDB/豆瓣ID | POST /api/recognition/manual |

#### 8.5.3 识别设置

| 功能点 | 说明 | 配置项 |
|-------|------|--------|
| 识别模式 | 自动/手动模式切换 | recognition.mode |
| 数据源优先级 | 调整TMDB/豆瓣优先级 | recognition.sources |
| AI识别开关 | 启用/禁用AI识别 | ai_recognition.enabled |
| 置信度阈值 | 设置自动确认阈值 | recognition.confidence_threshold |

### 8.6 整理管理

#### 8.6.1 整理任务管理

| 功能点 | 说明 | 相关API |
|-------|------|--------|
| 待整理列表 | 显示已识别待整理的文件 | GET /api/organize/pending |
| 整理中列表 | 显示正在整理的任务 | GET /api/organize/processing |
| 整理历史 | 显示整理记录 | GET /api/organize/history |
| 整理预览 | 预览整理后的路径和文件名 | POST /api/organize/preview |
| 执行整理 | 执行整理操作 | POST /api/organize/execute |

#### 8.6.2 整理规则配置

| 功能点 | 说明 | 配置项 |
|-------|------|--------|
| 命名规则编辑 | 编辑Jinja2命名模板 | naming_rules |
| 目录规则配置 | 配置目标目录结构 | directory_rules |
| 动作类型选择 | 移动/重命名/硬链接 | organize.action_type |
| 冲突处理策略 | 跳过/覆盖/重命名 | organize.conflict_strategy |
| 规则测试 | 测试命名规则效果 | 实时预览 |

#### 8.6.3 未识别文件管理

| 功能点 | 说明 | 相关API |
|-------|------|--------|
| 未识别分类查看 | 按状态查看未识别文件 | GET /api/undefined/files |
| 重新识别 | 对未识别文件重新识别 | POST /api/recognition/retry |
| 批量标记 | 标记为忽略或待处理 | POST /api/undefined/mark |
| 文件重整理 | 对整理后的文件重新整理 | POST /api/organize/reorganize |

### 8.7 下载管理

#### 8.7.1 下载任务管理

| 功能点 | 说明 | 相关API |
|-------|------|--------|
| 任务列表 | 显示所有下载任务 | GET /api/download/tasks |
| 状态筛选 | 按状态筛选任务 | filter参数 |
| 添加任务 | 添加磁力/Torrent/RSS | POST /api/download/tasks |
| 暂停/恢复 | 控制下载状态 | POST /api/download/{id}/pause |
| 删除任务 | 删除下载任务 | DELETE /api/download/{id} |
| 查看详情 | 显示下载详情和进度 | GET /api/download/{id} |

#### 8.7.2 下载器配置

| 功能点 | 说明 | 配置项 |
|-------|------|--------|
| 下载器选择 | qBittorrent/Transmission等 | downloader.type |
| 连接配置 | API地址/端口/认证 | downloader.connection |
| 下载路径 | 默认下载保存路径 | downloader.save_path |
| 限速设置 | 上传/下载速度限制 | downloader.speed_limit |

#### 8.7.3 RSS订阅管理

| 功能点 | 说明 | 相关API |
|-------|------|--------|
| RSS源列表 | 管理RSS订阅源 | GET /api/rss/sources |
| 添加RSS源 | 新增RSS订阅 | POST /api/rss/sources |
| 编辑RSS源 | 修改RSS配置 | PUT /api/rss/sources |
| 删除RSS源 | 移除RSS订阅 | DELETE /api/rss/sources |
| 订阅规则 | 设置自动下载规则 | POST /api/rss/rules |

### 8.8 系统管理

#### 8.8.1 进程管理

| 功能点 | 说明 | 相关API |
|-------|------|--------|
| 服务状态查看 | 显示进程状态/PID/运行时长 | GET /api/process/status |
| 启动服务 | 启动应用进程 | POST /api/process/control |
| 停止服务 | 停止应用进程 | POST /api/process/control |
| 重启服务 | 重启应用进程 | POST /api/process/control |
| 实时日志 | WebSocket查看应用日志 | WS /api/process/logs/stream |
| 日志筛选 | 按级别/时间筛选日志 | GET /api/process/logs |

#### 8.8.2 配置管理

| 功能点 | 说明 | 相关API |
|-------|------|--------|
| 配置分类浏览 | 按模块浏览配置 | GET /api/config |
| 配置编辑 | 编辑YAML配置 | PUT /api/config/{key} |
| 配置导入 | 导入配置文件 | POST /api/config/import |
| 配置导出 | 导出配置文件 | GET /api/config/export |
| 配置历史 | 查看配置变更历史 | GET /api/config/history |
| 配置回滚 | 回滚到历史版本 | POST /api/config/rollback |
| 热重载 | 触发配置热重载 | POST /api/config/reload |

#### 8.8.3 用户管理

| 功能点 | 说明 | 相关API |
|-------|------|--------|
| 用户列表 | 显示系统用户 | GET /api/users |
| 添加用户 | 创建新用户 | POST /api/users |
| 编辑用户 | 修改用户信息 | PUT /api/users/{id} |
| 删除用户 | 删除用户 | DELETE /api/users/{id} |
| 角色分配 | 设置用户角色 | PUT /api/users/{id}/role |
| 密码重置 | 重置用户密码 | POST /api/users/{id}/reset-password |

#### 8.8.4 系统信息

| 功能点 | 说明 | 数据来源 |
|-------|------|---------|
| 版本信息 | 显示当前版本/更新日志 | 系统信息 |
| 系统状态 | CPU/内存/磁盘使用 | psutil采集 |
| 数据库状态 | 连接池/查询性能 | SQLAlchemy |
| 任务队列状态 | 队列长度/处理速度 | 任务管理器 |
| 检查更新 | 检测新版本 | 版本检查API |

### 8.9 监控告警

#### 8.9.1 监控仪表盘

| 功能点 | 说明 | 数据来源 |
|-------|------|---------|
| 系统资源图表 | CPU/内存/磁盘趋势 | metrics_time_series表 |
| 业务指标图表 | 扫描/识别/下载统计 | 业务统计表 |
| 实时指标 | 当前QPS/响应时间 | 实时监控 |
| 历史趋势 | 7天/30天趋势对比 | 历史数据 |

#### 8.9.2 告警管理

| 功能点 | 说明 | 相关API |
|-------|------|--------|
| 告警规则列表 | 显示告警规则配置 | GET /api/alert/rules |
| 添加告警规则 | 新建告警规则 | POST /api/alert/rules |
| 编辑告警规则 | 修改告警条件 | PUT /api/alert/rules/{id} |
| 删除告警规则 | 移除告警规则 | DELETE /api/alert/rules/{id} |
| 告警历史 | 查看历史告警 | GET /api/alert/history |
| 告警通知配置 | 配置通知渠道 | POST /api/alert/channels |

### 8.10 数据库管理

#### 8.10.1 数据库管理界面

| 功能点 | 说明 | 相关表/操作 |
|-------|------|-----------|
| 数据库状态 | 显示连接状态/大小/表数量 | PRAGMA/统计查询 |
| 表结构查看 | 查看各表结构和索引 | schema查询 |
| 数据浏览 | 分页浏览表数据 | SELECT查询 |
| SQL查询 | 执行自定义SQL（只读） | 受限查询 |
| 数据导出 | 导出表数据为SQL/CSV | 导出功能 |
| 数据清理 | 清理过期日志/历史数据 | DELETE操作 |

#### 8.10.2 数据表管理

| 表名 | 管理功能 | 操作 |
|-----|---------|------|
| media_files | 查看/编辑/删除 | CRUD |
| recognition_results | 查看/确认/删除 | CRUD |
| organize_tasks | 查看/重试/取消 | 任务管理 |
| download_tasks | 查看/暂停/删除 | 任务管理 |
| scan_history | 查看/导出 | 查询导出 |
| notification_logs | 查看/清理 | 查询清理 |
| operation_logs | 查看/导出/清理 | 审计功能 |
| config_history | 查看/回滚 | 版本管理 |

#### 8.10.3 数据库维护

| 功能点 | 说明 | 操作 |
|-------|------|------|
| VACUUM优化 | 数据库压缩优化 | VACUUM命令 |
| 备份数据库 | 手动备份数据库 | 文件复制 |
| 恢复数据库 | 从备份恢复 | 文件替换 |
| 迁移检查 | 检查数据库迁移状态 | Alembic |
| 执行迁移 | 执行数据库升级 | Alembic upgrade |

### 8.11 功能优先级汇总

#### P0 - 核心功能（必须实现）

| 模块 | 功能点数量 | 关键功能 |
|-----|-----------|---------|
| 仪表盘 | 5 | 统计卡片、待处理提醒 |
| 媒体库 | 12 | 列表、详情、搜索、批量操作 |
| 扫描管理 | 8 | 手动扫描、任务列表、监控配置 |
| 识别管理 | 10 | 待识别列表、手动识别、结果确认 |
| 整理管理 | 8 | 待整理列表、整理预览、规则配置 |
| 系统管理 | 15 | 进程管理、配置编辑、日志查看 |
| **小计** | **58** | - |

#### P1 - 重要功能（建议实现）

| 模块 | 功能点数量 | 关键功能 |
|-----|-----------|---------|
| 下载管理 | 10 | 任务管理、下载器配置、RSS订阅 |
| 系统管理-用户 | 6 | 用户管理、权限控制 |
| 数据库管理 | 10 | 数据浏览、SQL查询、备份恢复 |
| **小计** | **26** | - |

#### P2 - 增强功能（可延后）

| 模块 | 功能点数量 | 关键功能 |
|-----|-----------|---------|
| 监控告警 | 8 | 监控图表、告警规则、通知配置 |
| **小计** | **8** | - |

**总计：92个功能点**

### 8.12 界面设计原则

#### 8.12.1 布局设计

- **响应式布局**：适配1920x1080及以上分辨率
- **侧边栏导航**：固定左侧，支持折叠
- **面包屑导航**：显示当前页面位置
- **标签页设计**：支持多标签页切换

#### 8.12.2 交互设计

- **实时反馈**：操作后立即显示结果或加载状态
- **批量操作**：支持表格批量选择和操作
- **拖拽支持**：文件拖拽上传、排序调整
- **快捷键**：支持常用操作快捷键

#### 8.12.3 视觉设计

- **暗色主题**：默认暗色主题，保护眼睛
- **色彩规范**：主色#409EFF，成功#67C23A，警告#E6A23C，危险#F56C6C
- **字体规范**：中文使用PingFang SC，英文使用Inter
- **间距规范**：基础间距8px，组件间距16px

---

## 附录A：术语表

| 术语 | 说明 |
|-----|------|
| P2P | Peer-to-Peer，点对点传输 |
| RSS | Really Simple Syndication，简易信息聚合 |
| TMDB | The Movie Database，电影数据库 |
| IMDB | Internet Movie Database，互联网电影数据库 |
| API | Application Programming Interface，应用程序接口 |
| Webhook | HTTP回调接口 |
| LLM | Large Language Model，大语言模型 |
| SHA-256 | 安全哈希算法，用于文件完整性校验 |
| FFmpeg | 开源多媒体处理框架 |
| OVA | Original Video Animation，原创动画录影带 |
| NFO | 信息文件，包含媒体元数据 |
| SDK | Software Development Kit，软件开发工具包 |
| Token | AI模型处理文本的最小单位 |
| Prompt | 发送给AI模型的指令或问题 |
| Temperature | AI模型生成文本的随机性参数 |

---

## 附录B：非功能性需求（NFR）

### B.1 性能需求

| 指标 | 目标值 |
|-----|--------|
| 文件扫描速度 | ≥500 文件/秒 |
| API响应时间 | P99 < 200ms |
| 并发处理能力 | ≥50 个同时任务 |
| 内存占用 | 空闲 < 200MB |

### B.2 可靠性需求

| 指标 | 目标值 |
|-----|--------|
| 系统可用性 | ≥99.5% |
| 故障恢复时间 | < 5 分钟 |
| 任务成功率 | ≥95% |

### B.3 安全性需求

- 数据传输：HTTPS/WSS 加密
- 敏感信息：AES-256-GCM 加密存储
- 密码安全：bcrypt 哈希

---

## 附录C：错误处理与降级策略

### C.1 网络异常处理
- API超时：指数退避重试
- AI服务不可用：降级到规则匹配

### C.2 文件系统异常处理
- 磁盘空间不足：暂停新任务，发送警告
- 文件被占用：延迟重试

---

## 附录D：核心业务流程状态机

### D.1 文件生命周期状态
```
[扫描发现] → [待识别] → [识别中] → [识别成功] → [待整理] → [整理中] → [已完成]
```

### D.2 下载任务状态机
```
[pending] → [queued] → [downloading] → [completed]
```

---

## 附录E：API接口契约

### E.1 扫描接口
- POST `/api/scan` - 触发目录扫描
- GET `/api/scan/{task_id}` - 获取扫描任务状态

### E.2 进程管理接口
- GET `/api/process/status` - 获取进程状态
- POST `/api/process/control` - 控制进程

---

## 附录F：测试策略

### F.1 单元测试
- 覆盖率目标：≥80%
- 重点模块：文件扫描、命名规则、识别逻辑

### F.2 集成测试
- 扫描+识别+整理完整流程
- 数据源API mock测试

### F.3 E2E测试
- 完整整理流程
- 下载管理流程

---

## 附录G：部署与运维指南

### G.1 升级机制
1. 预检查
2. 备份当前版本
3. 执行升级
4. 验证功能

### G.2 备份还原
```batch
scriptsackup.bat --full
scriptsestore.bat --backup-file backup.zip
```

### G.3 日志管理

**日志文件位置**：
- 应用日志：`logs/app.log`
- 错误日志：`logs/error.log`
- 访问日志：`logs/access.log`

**日志轮转策略**：
- 单个日志文件最大 10MB
- 保留最近 30 天的日志
- 自动压缩历史日志

### G.4 常见问题排查

| 问题 | 排查步骤 | 解决方案 |
|-----|---------|---------|
| 服务无法启动 | 检查端口占用、查看错误日志 | 更换端口或关闭占用程序 |
| 扫描无结果 | 检查路径权限、验证文件格式 | 添加扫描路径、检查文件扩展名 |
| 识别失败 | 检查网络连接、验证API密钥 | 配置代理、更新API密钥 |
| 整理失败 | 检查磁盘空间、验证目标路径 | 清理磁盘、创建目标目录 |

---

## 附录H：第三方服务管理

### H.1 TMDB API

**接口限制**：
- Rate Limit: 40 requests/10 seconds (认证后)
- 未认证限制: 20 requests/10 seconds

**缓存策略**：
- 电影信息缓存 24 小时
- 剧集信息缓存 12 小时
- 搜索请求缓存 1 小时

**配置示例**：
```yaml
tmdb:
  api_key: "your_api_key_here"
  language: "zh-CN"
  cache_enabled: true
  cache_ttl: 86400  # 24小时
```

### H.2 AI服务

**多厂商负载均衡策略**：

| 优先级 | 服务商 | 模型 | 适用场景 |
|-------|--------|------|---------|
| 1 | OpenAI | GPT-4o | 复杂识别任务 |
| 2 | Kimi | moonshot-v1-8k | 常规识别任务 |
| 3 | DeepSeek | deepseek-chat | 备用方案 |

**成本控制策略**：
- 每日预算限制：$10
- 单次请求最大 Token：2000
- 失败自动降级到规则匹配

**配置示例**：
```yaml
ai_recognition:
  enabled: true
  daily_budget: 10.0
  max_tokens: 2000
  providers:
    - name: "openai"
      priority: 1
      model: "gpt-4o"
    - name: "kimi"
      priority: 2
      model: "moonshot-v1-8k"
```

---

## 附录I：用户交互设计规范

### I.1 错误码规范

| 错误码 | 说明 | HTTP状态码 | 处理建议 |
|-------|------|-----------|---------|
| SCAN_IN_PROGRESS | 已有扫描任务进行中 | 409 | 等待当前扫描完成 |
| DISK_FULL | 磁盘空间不足 | 507 | 清理磁盘空间 |
| PATH_NOT_FOUND | 路径不存在 | 404 | 检查路径配置 |
| PERMISSION_DENIED | 权限不足 | 403 | 检查文件/目录权限 |
| API_RATE_LIMIT | API限流 | 429 | 稍后重试 |
| AI_SERVICE_ERROR | AI服务异常 | 503 | 切换到备用AI服务 |
| DUPLICATE_FILE | 重复文件 | 409 | 检查重复处理策略 |
| INVALID_NAMING_RULE | 命名规则无效 | 400 | 检查Jinja2语法 |

### I.2 通知模板

**扫描完成通知**：
```
标题：扫描完成
内容：本次扫描发现 {new_files} 个新文件，{updated_files} 个更新文件
时间：{scan_time}
```

**下载完成通知**：
```
标题：下载完成 - {media_title}
内容：{media_title} 下载已完成，保存至 {save_path}
大小：{file_size}
耗时：{download_duration}
```

**低磁盘空间警告**：
```
标题：⚠️ 磁盘空间不足
内容：磁盘 {drive} 剩余空间仅 {free_space}，建议及时清理
使用率：{usage_percent}%
```

### I.3 界面响应时间规范

| 操作类型 | 最大响应时间 | 加载状态 |
|---------|-------------|---------|
| 页面切换 | < 300ms | 骨架屏 |
| 数据查询 | < 500ms | 加载动画 |
| 文件操作 | < 2s | 进度条 |
| 批量操作 | < 5s | 进度百分比 |
| 扫描任务 | 实时 | WebSocket推送 |

---

## 附录J：发布检查清单

### J.1 代码检查

- [ ] 单元测试通过率 ≥ 90%
- [ ] 代码覆盖率 ≥ 80%
- [ ] 静态检查无严重问题（Pylint/Flake8）
- [ ] 类型检查通过（mypy）
- [ ] 安全扫描无高危漏洞（Bandit）

### J.2 功能检查

- [ ] E2E测试通过（关键流程）
- [ ] 性能测试达标（扫描500文件/秒）
- [ ] 内存泄漏测试通过
- [ ] 并发测试通过（50并发任务）
- [ ] 兼容性测试（Windows 10/11）

### J.3 文档检查

- [ ] API文档完整（OpenAPI/Swagger）
- [ ] 用户手册更新
- [ ] 更新日志（CHANGELOG）完整
- [ ] 部署文档准确

### J.4 发布检查

- [ ] 版本号正确（语义化版本）
- [ ] 安装包测试通过（干净环境）
- [ ] 升级测试通过（从上一版本）
- [ ] 回滚方案准备就绪
- [ ] 监控告警配置验证

### J.5 发布后验证

- [ ] 核心功能可用性检查
- [ ] 错误日志监控（24小时）
- [ ] 性能指标监控（48小时）
- [ ] 用户反馈收集渠道就绪

---

## 附录K：数据库迁移指南

### K.1 Alembic 迁移命令

```bash
# 创建新迁移
alembic revision --autogenerate -m "add user table"

# 升级到最新版本
alembic upgrade head

# 降级到指定版本
alembic downgrade -1

# 查看当前版本
alembic current

# 查看历史版本
alembic history
```

### K.2 迁移最佳实践

1. **每个迁移只做一件事**：保持迁移的原子性
2. **测试迁移脚本**：在测试环境验证迁移
3. **备份数据**：生产环境迁移前必须备份
4. **记录执行时间**：大表迁移需评估停机时间

---

## 附录L：性能优化指南

### L.1 数据库优化

**索引优化**：
```sql
-- 常用查询索引
CREATE INDEX idx_media_files_type ON media_files(media_type);
CREATE INDEX idx_recognition_results_confidence ON recognition_results(confidence);
```

**查询优化**：
- 使用 EXPLAIN 分析慢查询
- 避免 SELECT *，只查询需要的字段
- 批量操作使用事务

### L.2 缓存策略

**多级缓存架构**：
```
L1: 内存缓存 (LRU Cache)
L2: 本地文件缓存
L3: 数据库缓存
```

**缓存失效策略**：
- 定时失效（TTL）
- 主动失效（数据变更时）
- 懒加载（按需加载）

---

## 附录M：安全加固指南

### M.1 网络安全

- 启用 HTTPS（生产环境）
- 配置防火墙规则
- 限制 API 访问频率
- 使用 CORS 白名单

### M.2 数据安全

- 敏感配置加密存储
- 数据库文件权限控制（600）
- 定期更换 API 密钥
- 审计日志保留 180 天

### M.3 代码安全

- 依赖包定期更新
- 禁用调试模式（生产）
- 输入验证和过滤
- SQL 注入防护（使用 ORM）

---

*本文档版本: v1.6*
*最后更新: 2026-03-12*
