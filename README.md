# Windows 流媒体服务

基于 Python 技术栈开发的本地媒体资源管理工具，帮助用户自动化地扫描、识别、整理和下载媒体资源。

## 功能特性

- 📁 **本地文件扫描** - 自动扫描指定目录，识别媒体文件
- 🔍 **智能识别** - 基于 TMDB 等数据源自动识别媒体信息
- 📂 **智能整理** - 支持自定义命名规则和目录结构
- 📥 **媒体下载** - 集成 P2P 下载工具，支持 RSS 订阅
- 🎨 **Web 界面** - 现代化的 Web 管理界面
- 🔔 **通知服务** - 支持多种通知渠道
- 📊 **数据统计** - 媒体库统计与可视化

## 快速开始

### 环境要求

- Windows 10/11
- Python 3.9+

### 安装步骤

1. 解压发布包到任意目录
2. 运行 `scripts/setup_deps.bat` 安装依赖
3. 运行 `scripts/start.bat` 启动服务
4. 访问 http://localhost:8000

## 目录结构

```
MediaService/
├── app/                   # 应用核心代码
│   ├── core/             # 核心业务逻辑
│   ├── modules/          # 功能模块
│   ├── api/              # API 接口
│   └── web/              # Web 界面
├── data/                 # 数据目录
│   ├── db/               # SQLite 数据库
│   ├── cache/            # 缓存文件
│   ├── logs/             # 日志文件
│   ├── temp/             # 临时文件
│   └── backups/          # 备份文件
├── config/               # 配置文件
├── python/               # 嵌入式 Python
├── scripts/              # 批处理脚本
└── runtime/              # 运行时依赖
```

## 文档

- [技术方案](./Windows流媒体服务_完整技术方案_v1.6.md)
- [API 文档](http://localhost:8000/docs)
- [部署指南](./Windows流媒体服务_完整技术方案_v1.6.md#七windows-绿色部署方案)

## 许可证

MIT License
