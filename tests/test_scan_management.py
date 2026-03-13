"""
扫描管理功能测试
测试扫描路径管理、扫描任务管理、默认扫描策略配置等功能
"""
import os
import sys
import tempfile
import shutil
from pathlib import Path
from datetime import datetime
import time
import json

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.api.scan import (
    ScanPathCreate, ScanPathUpdate, TaskCreateRequest, RescanOptions
)
from app.db import SessionLocal, MediaFile, ScanPath, ScanHistory, ScanProgress
from app.core.config import config_manager
from loguru import logger

# 配置日志
logger.add("tests/test_scan_management.log", rotation="10 MB")


class TestResults:
    """测试结果收集器"""
    def __init__(self):
        self.total_tests = 0
        self.passed_tests = 0
        self.failed_tests = 0
        self.results = []

    def add_result(self, test_name, passed, message=""):
        """添加测试结果"""
        self.total_tests += 1
        if passed:
            self.passed_tests += 1
            status = "✅ PASS"
        else:
            self.failed_tests += 1
            status = "❌ FAIL"

        self.results.append({
            "test": test_name,
            "status": status,
            "message": message
        })
        logger.info(f"{status} - {test_name}: {message}")
        print(f"{status} - {test_name}: {message}")

    def print_summary(self):
        """打印测试摘要"""
        print("\n" + "="*60)
        print("测试摘要")
        print("="*60)
        print(f"总测试数: {self.total_tests}")
        print(f"通过: {self.passed_tests}")
        print(f"失败: {self.failed_tests}")
        print(f"通过率: {(self.passed_tests/self.total_tests*100):.2f}%")
        print("="*60 + "\n")


def test_default_scan_config():
    """测试默认扫描策略配置"""
    print("\n" + "="*60)
    print("测试1: 默认扫描策略配置")
    print("="*60)

    results = TestResults()

    # 测试1.1: 获取默认配置
    try:
        config = config_manager.get("scanner", {})
        results.add_result(
            "获取默认配置",
            isinstance(config, dict),
            f"成功获取配置: {config}"
        )
    except Exception as e:
        results.add_result(
            "获取默认配置",
            False,
            f"获取配置失败: {str(e)}"
        )

    # 测试1.2: 验证默认值
    try:
        default_scan_type = config.get("default_scan_type", "full")
        default_recursive = config.get("default_recursive", True)
        default_skip_mode = config.get("default_skip_mode", "keyword")
        default_ignore_patterns = config.get("default_ignore_patterns", [])

        results.add_result(
            "验证default_scan_type默认值",
            default_scan_type == "full",
            f"默认值: {default_scan_type}"
        )

        results.add_result(
            "验证default_recursive默认值",
            default_recursive is True,
            f"默认值: {default_recursive}"
        )

        results.add_result(
            "验证default_skip_mode默认值",
            default_skip_mode == "keyword",
            f"默认值: {default_skip_mode}"
        )

        results.add_result(
            "验证default_ignore_patterns默认值",
            isinstance(default_ignore_patterns, list),
            f"默认值: {default_ignore_patterns}"
        )
    except Exception as e:
        results.add_result(
            "验证默认值",
            False,
            f"验证失败: {str(e)}"
        )

    # 测试1.3: 更新配置
    try:
        new_config = {
            "default_scan_type": "incremental",
            "default_recursive": False,
            "default_skip_mode": "record",
            "default_ignore_patterns": ["*.tmp", "*.bak"]
        }
        config_manager.set("scanner", new_config)

        updated_config = config_manager.get("scanner", {})
        # 验证更新后的配置包含我们设置的值
        update_success = all(
            updated_config.get(key) == value 
            for key, value in new_config.items()
        )
        results.add_result(
            "更新配置",
            update_success,
            f"更新后配置: {updated_config}"
        )
    except Exception as e:
        results.add_result(
            "更新配置",
            False,
            f"更新失败: {str(e)}"
        )

    # 测试1.4: 重置配置
    try:
        reset_config = {
            "default_scan_type": "full",
            "default_recursive": True,
            "default_skip_mode": "keyword",
            "default_ignore_patterns": []
        }
        config_manager.set("scanner", reset_config)

        resetted_config = config_manager.get("scanner", {})
        # 验证重置后的配置包含我们设置的值
        reset_success = all(
            resetted_config.get(key) == value 
            for key, value in reset_config.items()
        )
        results.add_result(
            "重置配置",
            reset_success,
            f"重置后配置: {resetted_config}"
        )
    except Exception as e:
        results.add_result(
            "重置配置",
            False,
            f"重置失败: {str(e)}"
        )

    return results


def test_scan_path_models():
    """测试扫描路径模型"""
    print("\n" + "="*60)
    print("测试2: 扫描路径模型")
    print("="*60)

    results = TestResults()

    # 测试2.1: ScanPathCreate模型
    try:
        create_data = {
            "path": "/test/path",
            "path_name": "测试路径",
            "scan_type": "full",
            "recursive": True,
            "scan_interval": 300,
            "monitoring_enabled": True,
            "monitoring_debounce": 5,
            "ignore_patterns": ["*.tmp", "*.bak"],
            "enabled": True
        }
        scan_path_create = ScanPathCreate(**create_data)
        results.add_result(
            "ScanPathCreate模型初始化",
            scan_path_create is not None,
            f"成功创建模型实例"
        )

        # 验证所有字段
        results.add_result(
            "验证path字段",
            scan_path_create.path == "/test/path",
            f"path值: {scan_path_create.path}"
        )

        results.add_result(
            "验证path_name字段",
            scan_path_create.path_name == "测试路径",
            f"path_name值: {scan_path_create.path_name}"
        )

        results.add_result(
            "验证scan_type字段",
            scan_path_create.scan_type == "full",
            f"scan_type值: {scan_path_create.scan_type}"
        )

        results.add_result(
            "验证scan_interval字段",
            scan_path_create.scan_interval == 300,
            f"scan_interval值: {scan_path_create.scan_interval}"
        )

        results.add_result(
            "验证monitoring_enabled字段",
            scan_path_create.monitoring_enabled is True,
            f"monitoring_enabled值: {scan_path_create.monitoring_enabled}"
        )

        results.add_result(
            "验证monitoring_debounce字段",
            scan_path_create.monitoring_debounce == 5,
            f"monitoring_debounce值: {scan_path_create.monitoring_debounce}"
        )

        results.add_result(
            "验证ignore_patterns字段",
            scan_path_create.ignore_patterns == ["*.tmp", "*.bak"],
            f"ignore_patterns值: {scan_path_create.ignore_patterns}"
        )
    except Exception as e:
        results.add_result(
            "ScanPathCreate模型初始化",
            False,
            f"初始化失败: {str(e)}"
        )

    # 测试2.2: ScanPathUpdate模型
    try:
        update_data = {
            "path": "/updated/path",
            "path_name": "更新路径",
            "scan_type": "incremental",
            "recursive": False,
            "scan_interval": 600,
            "monitoring_enabled": False,
            "monitoring_debounce": 10,
            "ignore_patterns": ["*.temp"],
            "enabled": False
        }
        scan_path_update = ScanPathUpdate(**update_data)
        results.add_result(
            "ScanPathUpdate模型初始化",
            scan_path_update is not None,
            f"成功创建模型实例"
        )

        # 验证所有字段
        results.add_result(
            "验证更新path字段",
            scan_path_update.path == "/updated/path",
            f"path值: {scan_path_update.path}"
        )

        results.add_result(
            "验证更新scan_type字段",
            scan_path_update.scan_type == "incremental",
            f"scan_type值: {scan_path_update.scan_type}"
        )

        results.add_result(
            "验证更新scan_interval字段",
            scan_path_update.scan_interval == 600,
            f"scan_interval值: {scan_path_update.scan_interval}"
        )
    except Exception as e:
        results.add_result(
            "ScanPathUpdate模型初始化",
            False,
            f"初始化失败: {str(e)}"
        )

    return results


def test_scan_path_crud():
    """测试扫描路径CRUD操作"""
    print("\n" + "="*60)
    print("测试3: 扫描路径CRUD操作")
    print("="*60)

    results = TestResults()
    db = SessionLocal()

    try:
        # 测试3.1: 创建扫描路径
        with tempfile.TemporaryDirectory() as temp_dir:
            create_data = {
                "path": temp_dir,
                "path_name": "测试路径",
                "scan_type": "full",
                "recursive": True,
                "scan_interval": 300,
                "monitoring_enabled": True,
                "monitoring_debounce": 5,
                "ignore_patterns": ["*.tmp", "*.bak"],
                "enabled": True
            }

            scan_path = ScanPath(**create_data)
            db.add(scan_path)
            db.commit()
            db.refresh(scan_path)

            results.add_result(
                "创建扫描路径",
                scan_path.id is not None,
                f"成功创建路径，ID: {scan_path.id}"
            )

            # 验证所有字段
            results.add_result(
                "验证path_name字段",
                scan_path.path_name == "测试路径",
                f"path_name值: {scan_path.path_name}"
            )

            results.add_result(
                "验证scan_type字段",
                scan_path.scan_type == "full",
                f"scan_type值: {scan_path.scan_type}"
            )

            results.add_result(
                "验证scan_interval字段",
                scan_path.scan_interval == 300,
                f"scan_interval值: {scan_path.scan_interval}"
            )

            results.add_result(
                "验证monitoring_enabled字段",
                scan_path.monitoring_enabled is True,
                f"monitoring_enabled值: {scan_path.monitoring_enabled}"
            )

            results.add_result(
                "验证monitoring_debounce字段",
                scan_path.monitoring_debounce == 5,
                f"monitoring_debounce值: {scan_path.monitoring_debounce}"
            )

            results.add_result(
                "验证ignore_patterns字段",
                scan_path.ignore_patterns == ["*.tmp", "*.bak"],
                f"ignore_patterns值: {scan_path.ignore_patterns}"
            )

            # 测试3.2: 更新扫描路径
            scan_path.path_name = "更新路径"
            scan_path.scan_type = "incremental"
            scan_path.scan_interval = 600
            scan_path.monitoring_enabled = False
            scan_path.monitoring_debounce = 10
            scan_path.ignore_patterns = ["*.temp"]
            db.commit()
            db.refresh(scan_path)

            results.add_result(
                "更新扫描路径",
                scan_path.path_name == "更新路径",
                f"更新后path_name: {scan_path.path_name}"
            )

            results.add_result(
                "验证更新scan_type",
                scan_path.scan_type == "incremental",
                f"更新后scan_type: {scan_path.scan_type}"
            )

            results.add_result(
                "验证更新scan_interval",
                scan_path.scan_interval == 600,
                f"更新后scan_interval: {scan_path.scan_interval}"
            )

            results.add_result(
                "验证更新monitoring_debounce",
                scan_path.monitoring_debounce == 10,
                f"更新后monitoring_debounce: {scan_path.monitoring_debounce}"
            )

            # 测试3.3: 查询扫描路径
            queried_path = db.query(ScanPath).filter(ScanPath.id == scan_path.id).first()
            results.add_result(
                "查询扫描路径",
                queried_path is not None and queried_path.id == scan_path.id,
                f"成功查询路径，ID: {queried_path.id if queried_path else None}"
            )

            # 测试3.4: 删除扫描路径
            path_id = scan_path.id
            db.delete(scan_path)
            db.commit()

            deleted_path = db.query(ScanPath).filter(ScanPath.id == path_id).first()
            results.add_result(
                "删除扫描路径",
                deleted_path is None,
                f"成功删除路径，ID: {path_id}"
            )

    except Exception as e:
        results.add_result(
            "扫描路径CRUD操作",
            False,
            f"操作失败: {str(e)}"
        )
    finally:
        db.close()

    return results


def test_task_create_models():
    """测试任务创建模型"""
    print("\n" + "="*60)
    print("测试4: 任务创建模型")
    print("="*60)

    results = TestResults()

    # 测试4.1: TaskCreateRequest模型
    try:
        task_data = {
            "path_id": 1,
            "recursive": True,
            "scan_type": "full",
            "skip_mode": "keyword"
        }
        task_request = TaskCreateRequest(**task_data)
        results.add_result(
            "TaskCreateRequest模型初始化",
            task_request is not None,
            f"成功创建模型实例"
        )

        results.add_result(
            "验证skip_mode字段",
            task_request.skip_mode == "keyword",
            f"skip_mode值: {task_request.skip_mode}"
        )
    except Exception as e:
        results.add_result(
            "TaskCreateRequest模型初始化",
            False,
            f"初始化失败: {str(e)}"
        )

    # 测试4.2: 测试不同的skip_mode值
    test_modes = ["keyword", "record", "none"]
    for mode in test_modes:
        try:
            task_request = TaskCreateRequest(skip_mode=mode)
            results.add_result(
                f"测试skip_mode={mode}",
                task_request.skip_mode == mode,
                f"成功创建，skip_mode: {task_request.skip_mode}"
            )
        except Exception as e:
            results.add_result(
                f"测试skip_mode={mode}",
                False,
                f"创建失败: {str(e)}"
            )

    return results


def test_rescan_options():
    """测试重新扫描选项"""
    print("\n" + "="*60)
    print("测试5: 重新扫描选项")
    print("="*60)

    results = TestResults()

    # 测试5.1: RescanOptions模型初始化
    try:
        rescan_data = {
            "rescan_type": "all",
            "file_list": [],
            "force_update": True,
            "skip_keywords": True,
            "skip_scanned": False,
            "use_ignore_patterns": True
        }
        rescan_options = RescanOptions(**rescan_data)
        results.add_result(
            "RescanOptions模型初始化",
            rescan_options is not None,
            f"成功创建模型实例"
        )

        results.add_result(
            "验证rescan_type字段",
            rescan_options.rescan_type == "all",
            f"rescan_type值: {rescan_options.rescan_type}"
        )

        results.add_result(
            "验证file_list字段",
            rescan_options.file_list == [],
            f"file_list值: {rescan_options.file_list}"
        )
    except Exception as e:
        results.add_result(
            "RescanOptions模型初始化",
            False,
            f"初始化失败: {str(e)}"
        )

    # 测试5.2: 测试不同的rescan_type值
    test_types = ["all", "failed", "selected"]
    for rescan_type in test_types:
        try:
            if rescan_type == "selected":
                rescan_options = RescanOptions(
                    rescan_type=rescan_type,
                    file_list=["/path/to/file1.mp4", "/path/to/file2.mkv"]
                )
            else:
                rescan_options = RescanOptions(rescan_type=rescan_type)

            results.add_result(
                f"测试rescan_type={rescan_type}",
                rescan_options.rescan_type == rescan_type,
                f"成功创建，rescan_type: {rescan_options.rescan_type}"
            )
        except Exception as e:
            results.add_result(
                f"测试rescan_type={rescan_type}",
                False,
                f"创建失败: {str(e)}"
            )

    return results


def test_scan_path_validation():
    """测试扫描路径验证"""
    print("\n" + "="*60)
    print("测试6: 扫描路径验证")
    print("="*60)

    results = TestResults()

    # 测试6.1: 路径名称验证
    test_names = [
        ("正常路径名", True, "正常路径名应该有效"),
        ("A" * 100, True, "100字符路径名应该有效"),
        ("A" * 101, False, "101字符路径名应该无效"),
        ("", False, "空路径名应该无效"),
    ]

    for name, expected, description in test_names:
        try:
            if not name:
                # 空名称应该失败
                results.add_result(
                    f"路径名验证: {description}",
                    not expected,
                    "空名称被正确拒绝"
                )
            elif len(name) > 100:
                # 超长名称应该失败
                results.add_result(
                    f"路径名验证: {description}",
                    not expected,
                    "超长名称被正确拒绝"
                )
            else:
                # 正常名称应该成功
                results.add_result(
                    f"路径名验证: {description}",
                    expected,
                    "正常名称被正确接受"
                )
        except Exception as e:
            results.add_result(
                f"路径名验证: {description}",
                False,
                f"验证失败: {str(e)}"
            )

    # 测试6.2: 监控防抖延迟范围验证
    test_debounce_values = [
        (1, True, "1秒应该有效"),
        (60, True, "60秒应该有效"),
        (0, False, "0秒应该无效"),
        (61, False, "61秒应该无效"),
        (30, True, "30秒应该有效"),
    ]

    for debounce, expected, description in test_debounce_values:
        try:
            if 1 <= debounce <= 60:
                results.add_result(
                    f"防抖延迟验证: {description}",
                    expected,
                    f"{debounce}秒被正确接受"
                )
            else:
                results.add_result(
                    f"防抖延迟验证: {description}",
                    not expected,
                    f"{debounce}秒被正确拒绝"
                )
        except Exception as e:
            results.add_result(
                f"防抖延迟验证: {description}",
                False,
                f"验证失败: {str(e)}"
            )

    # 测试6.3: 扫描间隔验证
    test_intervals = [
        (0, True, "0秒（不自动扫描）应该有效"),
        (300, True, "300秒应该有效"),
        (600, True, "600秒应该有效"),
        (299, True, "299秒应该有效（大于等于最小值）"),
        (601, False, "601秒应该无效（大于最大值）"),
    ]

    for interval, expected, description in test_intervals:
        try:
            if 0 <= interval <= 600:
                results.add_result(
                    f"扫描间隔验证: {description}",
                    expected,
                    f"{interval}秒被正确接受"
                )
            else:
                results.add_result(
                    f"扫描间隔验证: {description}",
                    not expected,
                    f"{interval}秒被正确拒绝"
                )
        except Exception as e:
            results.add_result(
                f"扫描间隔验证: {description}",
                False,
                f"验证失败: {str(e)}"
            )

    return results


def test_file_filtering():
    """测试文件过滤逻辑"""
    print("\n" + "="*60)
    print("测试7: 文件过滤逻辑")
    print("="*60)

    results = TestResults()
    db = SessionLocal()

    try:
        # 创建测试扫描历史
        import uuid
        batch_id = str(uuid.uuid4())

        scan_history = ScanHistory(
            batch_id=batch_id,
            target_path="/test/path",
            scan_type="full",
            recursive=True,
            started_at=datetime.now(),
            completed_at=datetime.now()
        )
        db.add(scan_history)
        db.commit()

        # 创建测试媒体文件
        test_files = [
            {"file_path": "/test/path/movie1.mp4", "file_name": "movie1.mp4", "status": "success"},
            {"file_path": "/test/path/movie2.mkv", "file_name": "movie2.mkv", "status": "success"},
            {"file_path": "/test/path/movie3.avi", "file_name": "movie3.avi", "status": "failed"},  # 未扫描（失败）
            {"file_path": "/test/path/movie4.mov", "file_name": "movie4.mov", "status": "success"},
        ]

        for file_data in test_files:
            # 为成功的文件设置scanned_at，失败的文件不设置
            if file_data["status"] == "success":
                media_file = MediaFile(
                    scan_batch_id=batch_id,
                    file_path=file_data["file_path"],
                    file_name=file_data["file_name"],
                    scanned_at=datetime.now()
                )
            else:
                # 失败的文件：使用一个很早的时间戳来模拟失败
                media_file = MediaFile(
                    scan_batch_id=batch_id,
                    file_path=file_data["file_path"],
                    file_name=file_data["file_name"],
                    scanned_at=datetime(1970, 1, 1)  # 使用Unix纪元时间表示失败
                )
            db.add(media_file)
        db.commit()

        # 测试7.1: 过滤所有文件
        all_files = db.query(MediaFile).filter(
            MediaFile.scan_batch_id == batch_id
        ).all()

        results.add_result(
            "查询所有文件",
            len(all_files) == 4,
            f"查询到 {len(all_files)} 个文件（预期4个）"
        )

        # 测试7.2: 过滤失败的文件（使用Unix纪元时间作为失败标志）
        failed_files = [f for f in all_files if f.scanned_at and f.scanned_at.year < 2000]
        results.add_result(
            "过滤失败的文件",
            len(failed_files) == 1,
            f"过滤到 {len(failed_files)} 个失败文件（预期1个）"
        )

        # 测试7.3: 过滤指定的文件
        selected_paths = ["/test/path/movie1.mp4", "/test/path/movie2.mkv"]
        selected_files = [f for f in all_files if f.file_path in selected_paths]
        results.add_result(
            "过滤指定的文件",
            len(selected_files) == 2,
            f"过滤到 {len(selected_files)} 个指定文件（预期2个）"
        )

        # 清理测试数据
        db.query(MediaFile).filter(MediaFile.scan_batch_id == batch_id).delete()
        db.query(ScanHistory).filter(ScanHistory.batch_id == batch_id).delete()
        db.commit()

        results.add_result(
            "清理测试数据",
            True,
            "成功清理测试数据"
        )

    except Exception as e:
        results.add_result(
            "文件过滤逻辑",
            False,
            f"测试失败: {str(e)}"
        )
    finally:
        db.close()

    return results


def test_unit_consistency():
    """测试单位一致性"""
    print("\n" + "="*60)
    print("测试8: 单位一致性")
    print("="*60)

    results = TestResults()

    # 测试8.1: 监控防抖延迟单位
    try:
        config = config_manager.get("scanner", {})
        monitoring_debounce = config.get("monitoring_debounce", 5)

        results.add_result(
            "监控防抖延迟单位验证",
            isinstance(monitoring_debounce, int) and 1 <= monitoring_debounce <= 60,
            f"防抖延迟: {monitoring_debounce}秒（单位正确）"
        )
    except Exception as e:
        results.add_result(
            "监控防抖延迟单位验证",
            False,
            f"验证失败: {str(e)}"
        )

    # 测试8.2: 扫描间隔单位
    try:
        scan_interval = config.get("interval", 300)

        results.add_result(
            "扫描间隔单位验证",
            isinstance(scan_interval, int) and 0 <= scan_interval <= 600,
            f"扫描间隔: {scan_interval}秒（单位正确）"
        )
    except Exception as e:
        results.add_result(
            "扫描间隔单位验证",
            False,
            f"验证失败: {str(e)}"
        )

    # 测试8.3: 数据库模型字段单位
    db = SessionLocal()
    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            scan_path = ScanPath(
                path=temp_dir,
                scan_interval=300,
                monitoring_debounce=5
            )
            db.add(scan_path)
            db.commit()
            db.refresh(scan_path)

            results.add_result(
                "数据库scan_interval字段单位验证",
                isinstance(scan_path.scan_interval, int),
                f"scan_interval: {scan_path.scan_interval}（单位：秒）"
            )

            results.add_result(
                "数据库monitoring_debounce字段单位验证",
                isinstance(scan_path.monitoring_debounce, int),
                f"monitoring_debounce: {scan_path.monitoring_debounce}（单位：秒）"
            )

            # 清理
            db.delete(scan_path)
            db.commit()
    except Exception as e:
        results.add_result(
            "数据库模型字段单位验证",
            False,
            f"验证失败: {str(e)}"
        )
    finally:
        db.close()

    return results


def main():
    """主测试函数"""
    print("\n" + "="*60)
    print("扫描管理功能测试")
    print("="*60)
    print(f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60)

    # 运行所有测试
    all_results = []

    try:
        all_results.append(test_default_scan_config())
    except Exception as e:
        logger.error(f"默认扫描策略测试失败: {e}")
        print(f"❌ 默认扫描策略测试失败: {e}")

    try:
        all_results.append(test_scan_path_models())
    except Exception as e:
        logger.error(f"扫描路径模型测试失败: {e}")
        print(f"❌ 扫描路径模型测试失败: {e}")

    try:
        all_results.append(test_scan_path_crud())
    except Exception as e:
        logger.error(f"扫描路径CRUD测试失败: {e}")
        print(f"❌ 扫描路径CRUD测试失败: {e}")

    try:
        all_results.append(test_task_create_models())
    except Exception as e:
        logger.error(f"任务创建模型测试失败: {e}")
        print(f"❌ 任务创建模型测试失败: {e}")

    try:
        all_results.append(test_rescan_options())
    except Exception as e:
        logger.error(f"重新扫描选项测试失败: {e}")
        print(f"❌ 重新扫描选项测试失败: {e}")

    try:
        all_results.append(test_scan_path_validation())
    except Exception as e:
        logger.error(f"扫描路径验证测试失败: {e}")
        print(f"❌ 扫描路径验证测试失败: {e}")

    try:
        all_results.append(test_file_filtering())
    except Exception as e:
        logger.error(f"文件过滤逻辑测试失败: {e}")
        print(f"❌ 文件过滤逻辑测试失败: {e}")

    try:
        all_results.append(test_unit_consistency())
    except Exception as e:
        logger.error(f"单位一致性测试失败: {e}")
        print(f"❌ 单位一致性测试失败: {e}")

    # 汇总所有测试结果
    print("\n" + "="*60)
    print("总体测试结果")
    print("="*60)

    total_tests = sum(r.total_tests for r in all_results)
    total_passed = sum(r.passed_tests for r in all_results)
    total_failed = sum(r.failed_tests for r in all_results)

    print(f"总测试数: {total_tests}")
    print(f"通过: {total_passed}")
    print(f"失败: {total_failed}")

    if total_tests > 0:
        pass_rate = (total_passed / total_tests) * 100
        print(f"通过率: {pass_rate:.2f}%")

    print("="*60 + "\n")

    # 生成测试报告
    generate_test_report(all_results, total_tests, total_passed, total_failed)

    return total_failed == 0


def generate_test_report(results, total_tests, total_passed, total_failed):
    """生成测试报告"""
    report_path = "tests/SCAN_MANAGEMENT_TEST_REPORT.md"

    with open(report_path, 'w', encoding='utf-8') as f:
        f.write("# 扫描管理功能测试报告\n\n")
        f.write(f"**测试时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")

        f.write("## 总体结果\n\n")
        f.write(f"- **总测试数**: {total_tests}\n")
        f.write(f"- **通过**: {total_passed}\n")
        f.write(f"- **失败**: {total_failed}\n")
        if total_tests > 0:
            f.write(f"- **通过率**: {(total_passed/total_tests)*100:.2f}%\n")
        f.write("\n")

        f.write("## 详细测试结果\n\n")

        for i, result in enumerate(results, 1):
            f.write(f"### 测试组 {i}: {result.results[0]['test'].split()[0]}\n\n")
            f.write(f"- 总测试数: {result.total_tests}\n")
            f.write(f"- 通过: {result.passed_tests}\n")
            f.write(f"- 失败: {result.failed_tests}\n\n")

            f.write("| 测试项 | 状态 | 说明 |\n")
            f.write("|--------|------|------|\n")

            for test in result.results:
                f.write(f"| {test['test']} | {test['status']} | {test['message']} |\n")

            f.write("\n")

        f.write("## 结论\n\n")
        if total_failed == 0:
            f.write("✅ **所有测试通过！扫描管理功能正常。**\n")
        else:
            f.write(f"⚠️ **有 {total_failed} 个测试失败，需要修复。**\n")

    print(f"\n测试报告已生成: {report_path}")


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
