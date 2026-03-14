# 数据库管理工具

本目录包含数据库管理相关的脚本，用于数据库的初始化、迁移和清理。

## 工具说明

### 1. 数据库编码检查和修复
**文件**: `check_and_fix_encoding.py`

检查项目中所有代码文件的编码，并自动转换为UTF-8。

**功能**:
- 检测Python文件编码
- 检测前端文件（.vue, .js, .scss）编码
- 自动将非UTF-8文件转换为UTF-8
- 为Python文件添加UTF-8编码声明

**使用方法**:
```bash
python scripts/check_and_fix_encoding.py
```

### 2. 数据库清理和重新初始化
**文件**: `clean_and_init_database.py`

清理现有数据库并使用UTF-8编码重新创建。

**功能**:
- 删除现有数据库文件
- 使用UTF-8编码重新创建数据库
- 初始化所有表结构
- 验证数据库创建是否正确

**注意事项**:
- ⚠️ 此操作将删除所有现有数据，不可恢复！
- 无需备份、迁移数据
- 执行前需要确认输入 'YES'

**使用方法**:
```bash
python scripts/clean_and_init_database.py
```

**执行步骤**:
1. 清理现有数据库文件
2. 重新创建数据库（使用UTF-8编码）
3. 初始化所有表结构
4. 验证数据库创建是否正确

### 3. 数据库迁移脚本
**文件**: `migrate_add_file_tasks.py`

添加文件任务表到现有数据库。

**功能**:
- 创建 `file_tasks` 表
- 支持文件级别的扫描、识别、整理流程管理

**使用方法**:
```bash
python scripts/migrate_add_file_tasks.py
```

## 数据库编码说明

### SQLite数据库编码
本项目使用SQLite数据库，默认使用UTF-8编码：

- ✅ **完全支持中文、日文、韩文**等所有Unicode字符
- ✅ **支持emoji等4字节Unicode字符**
- ✅ **无需额外配置**，开箱即用
- ✅ **支持文件路径、文件名、元数据等所有文本字段**

### 编码配置
数据库连接配置在 `app/db/__init__.py` 中：

```python
# SQLite默认使用UTF-8编码，完全支持中文、日文、韩文及emoji等所有Unicode字符
engine = create_engine(
    db_config.url,
    echo=db_config.echo,
    pool_size=db_config.pool_size
)
```

### 与MySQL的对比

| 特性       | SQLite (UTF-8) | MySQL (utf8mb4) |
| ---------- | -------------- | --------------- |
| 中文支持   | ✅ 完全支持     | ✅ 完全支持      |
| 日文/韩文  | ✅ 完全支持     | ✅ 完全支持      |
| Emoji支持  | ✅ 支持         | ✅ 支持          |
| 特殊符号   | ✅ 支持         | ✅ 支持          |
| 配置复杂度 | ✅ 无需配置     | ❌ 需要显式配置  |

**结论**: SQLite的UTF-8编码完全满足项目需求，支持所有非英语语言。

## Python文件编码规范

所有Python文件应包含UTF-8编码声明：

```python
# -*- coding: utf-8 -*-
"""
模块文档字符串
"""
```

## 配置文件编码规范

所有配置文件（YAML、JSON等）应使用UTF-8编码读写：

```python
# 读取配置
with open(config_file, 'r', encoding='utf-8') as f:
    config_data = yaml.safe_load(f)

# 保存配置
with open(config_file, 'w', encoding='utf-8') as f:
    yaml.dump(config_data, f, allow_unicode=True, default_flow_style=False)
```

## 前端文件编码规范

所有前端文件应保存为UTF-8编码（不带BOM）：
- Vue文件 (.vue)
- JavaScript文件 (.js)
- SCSS文件 (.scss)

## 数据库表结构

项目包含以下数据库表：

### 核心表
- `media_files` - 媒体文件表
- `subtitle_files` - 字幕文件表
- `recognition_results` - 识别结果表
- `organize_tasks` - 整理任务表
- `file_tasks` - 文件任务表

### 扫描相关表
- `scan_history` - 扫描历史表
- `scan_paths` - 扫描路径表
- `scan_progress` - 扫描进度表

### 关键词相关表
- `keyword_libraries` - 关键词库表
- `keyword_rules` - 关键词规则表
- `keyword_mappings` - 关键词映射表
- `season_episode_rules` - 季集提取规则表

### 系统表
- `notification_logs` - 通知日志表
- `config_history` - 配置历史表
- `operation_logs` - 通用操作日志表

## 故障排除

### 数据库文件被锁定
如果遇到 "database is locked" 错误：
1. 确保没有应用程序正在运行
2. 检查是否有其他进程访问数据库
3. 重新执行清理和初始化脚本

### 编码问题
如果遇到字符编码问题：
1. 运行编码检查脚本：`python scripts/check_and_fix_encoding.py`
2. 检查所有Python文件是否包含UTF-8编码声明
3. 确保配置文件使用UTF-8编码

### 表创建失败
如果表创建失败：
1. 检查数据库文件权限
2. 确保数据库目录存在且有写入权限
3. 查看日志文件了解详细错误信息

## 维护建议

1. **定期备份**: 虽然本项目数据库初始化无需备份，但生产环境建议定期备份数据库文件

2. **编码检查**: 在添加新文件后，运行编码检查脚本确保编码统一

3. **清理临时数据**: 定期清理过期的扫描历史和日志数据（如果启用自动清理功能）

4. **监控性能**: 如果数据库文件过大，考虑清理历史数据或优化表结构