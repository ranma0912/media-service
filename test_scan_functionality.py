"""
扫描模块功能性测试
测试文件扫描器、文件监控和调度器的核心功能
"""
import os
import sys
import tempfile
import shutil
from pathlib import Path
from datetime import datetime
import time

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).parent))

from app.modules.scanner.scanner import FileScanner, MEDIA_EXTENSIONS, SUBTITLE_EXTENSIONS
from app.modules.scanner.file_monitor import FileMonitor
from app.core.scheduler import ScanScheduler
from app.db import SessionLocal, MediaFile, ScanPath, ScanHistory
from loguru import logger

# 配置日志
logger.add("tests/test_scan_functionality.log", rotation="10 MB")


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


def create_test_media_files(directory):
    """创建测试用的媒体文件"""
    test_files = []
    
    # 创建视频文件
    video_files = [
        "Movie1.mp4",
        "Movie2.mkv",
        "Movie3.avi"
    ]
    
    for filename in video_files:
        filepath = directory / filename
        filepath.write_text("fake video content" * 1000)
        test_files.append(filepath)
        logger.info(f"创建测试文件: {filepath}")
    
    # 创建字幕文件
    subtitle_files = [
        "Movie1.zh.srt",
        "Movie1.en.srt",
        "Movie2.ass"
    ]
    
    for filename in subtitle_files:
        filepath = directory / filename
        filepath.write_text("fake subtitle content")
        test_files.append(filepath)
        logger.info(f"创建字幕文件: {filepath}")
    
    # 创建关键词库文件
    keyword_files = [
        "keywords.txt",
        "keyword_library.json",
        "naming_rules.csv"
    ]
    
    for filename in keyword_files:
        filepath = directory / filename
        filepath.write_text("keyword content")
        test_files.append(filepath)
        logger.info(f"创建关键词库文件: {filepath}")
    
    return test_files


def test_media_extensions():
    """测试媒体文件扩展名识别"""
    print("\n" + "="*60)
    print("测试1: 媒体文件扩展名识别")
    print("="*60)
    
    results = TestResults()
    
    # 测试支持的媒体扩展名
    test_cases = [
        ("movie.mp4", True, "mp4应该是媒体文件"),
        ("movie.mkv", True, "mkv应该是媒体文件"),
        ("movie.avi", True, "avi应该是媒体文件"),
        ("movie.mov", True, "mov应该是媒体文件"),
        ("movie.srt", False, "srt不应该被识别为媒体文件"),
        ("movie.ass", False, "ass不应该被识别为媒体文件"),
        ("movie.txt", False, "txt不应该被识别为媒体文件"),
    ]
    
    for filename, expected, message in test_cases:
        path = Path(filename)
        actual = path.suffix.lower() in MEDIA_EXTENSIONS
        results.add_result(
            f"识别 {filename}",
            actual == expected,
            message
        )
    
    return results


def test_subtitle_extensions():
    """测试字幕文件扩展名识别"""
    print("\n" + "="*60)
    print("测试2: 字幕文件扩展名识别")
    print("="*60)
    
    results = TestResults()
    
    test_cases = [
        ("subtitle.srt", True, "srt应该是字幕文件"),
        ("subtitle.ass", True, "ass应该是字幕文件"),
        ("subtitle.sub", True, "sub应该是字幕文件"),
        ("subtitle.ssa", True, "ssa应该是字幕文件"),
        ("movie.mp4", False, "mp4不应该被识别为字幕文件"),
        ("movie.txt", False, "txt不应该被识别为字幕文件"),
    ]
    
    for filename, expected, message in test_cases:
        path = Path(filename)
        actual = path.suffix.lower() in SUBTITLE_EXTENSIONS
        results.add_result(
            f"识别 {filename}",
            actual == expected,
            message
        )
    
    return results


def test_file_scanner_initialization():
    """测试文件扫描器初始化"""
    print("\n" + "="*60)
    print("测试3: 文件扫描器初始化")
    print("="*60)
    
    results = TestResults()
    
    # 测试不同参数初始化
    test_cases = [
        (
            {"task_id": 1, "batch_id": "test_batch"},
            "基本初始化"
        ),
        (
            {"ignore_patterns": ["*.temp", "*.bak"]},
            "带忽略模式初始化"
        ),
        (
            {"skip_mode": "keyword"},
            "keyword模式初始化"
        ),
        (
            {"skip_mode": "record"},
            "record模式初始化"
        ),
        (
            {"skip_mode": "none"},
            "none模式初始化"
        ),
    ]
    
    for kwargs, description in test_cases:
        try:
            scanner = FileScanner(**kwargs)
            results.add_result(
                description,
                scanner is not None,
                f"成功创建扫描器实例"
            )
        except Exception as e:
            results.add_result(
                description,
                False,
                f"初始化失败: {str(e)}"
            )
    
    return results


def test_keyword_library_detection():
    """测试关键词库文件检测"""
    print("\n" + "="*60)
    print("测试4: 关键词库文件检测")
    print("="*60)
    
    results = TestResults()
    
    scanner = FileScanner()
    
    test_cases = [
        ("keywords.txt", True, "keywords.txt应该被识别"),
        ("keyword_library.json", True, "keyword_library.json应该被识别"),
        ("naming_rules.csv", True, "naming_rules.csv应该被识别"),
        ("movie.mp4", False, "movie.mp4不应该被识别"),
        ("Movie1.mkv", False, "Movie1.mkv不应该被识别"),
        ("normal_file.txt", False, "normal_file.txt不应该被识别"),
    ]
    
    for filename, expected, description in test_cases:
        path = Path(filename)
        actual = scanner._is_keyword_library_file(path)
        results.add_result(
            description,
            actual == expected,
            f"预期: {expected}, 实际: {actual}"
        )
    
    return results


def test_ignore_patterns():
    """测试忽略模式匹配"""
    print("\n" + "="*60)
    print("测试5: 忽略模式匹配")
    print("="*60)
    
    results = TestResults()
    
    ignore_patterns = ["*.temp", "*.bak", "test_*"]
    scanner = FileScanner(ignore_patterns=ignore_patterns)
    
    test_cases = [
        ("file.temp", True, "file.temp应该被忽略"),
        ("file.bak", True, "file.bak应该被忽略"),
        ("test_file.txt", True, "test_file.txt应该被忽略"),
        ("normal_file.txt", False, "normal_file.txt不应该被忽略"),
        ("movie.mp4", False, "movie.mp4不应该被忽略"),
    ]
    
    for filename, expected, description in test_cases:
        path = Path(filename)
        actual = scanner.should_ignore_file(path)
        results.add_result(
            description,
            actual == expected,
            f"预期: {expected}, 实际: {actual}"
        )
    
    return results


def test_file_monitor_initialization():
    """测试文件监控器初始化"""
    print("\n" + "="*60)
    print("测试6: 文件监控器初始化")
    print("="*60)
    
    results = TestResults()
    
    # 创建临时目录
    with tempfile.TemporaryDirectory() as temp_dir:
        # 测试有效目录
        try:
            monitor = FileMonitor(temp_dir, lambda x, y: None)
            results.add_result(
                "有效目录初始化",
                monitor is not None,
                "成功创建监控器实例"
            )
        except Exception as e:
            results.add_result(
                "有效目录初始化",
                False,
                f"初始化失败: {str(e)}"
            )
        
        # 测试不存在的目录
        try:
            monitor = FileMonitor("/nonexistent/directory", lambda x, y: None)
            results.add_result(
                "不存在目录初始化",
                False,
                "应该抛出异常但没有"
            )
        except FileNotFoundError:
            results.add_result(
                "不存在目录初始化",
                True,
                "正确抛出FileNotFoundError"
            )
        except Exception as e:
            results.add_result(
                "不存在目录初始化",
                False,
                f"抛出了错误的异常: {type(e).__name__}"
            )
    
    return results


def test_file_monitor_lifecycle():
    """测试文件监控器生命周期"""
    print("\n" + "="*60)
    print("测试7: 文件监控器生命周期")
    print("="*60)
    
    results = TestResults()
    
    # 创建临时目录
    with tempfile.TemporaryDirectory() as temp_dir:
        callback_called = []
        
        def test_callback(event_type, file_path):
            callback_called.append((event_type, file_path))
        
        monitor = FileMonitor(temp_dir, test_callback, debounce_seconds=1)
        
        # 测试启动
        try:
            monitor.start()
            results.add_result(
                "启动监控器",
                monitor.is_running,
                "监控器成功启动"
            )
        except Exception as e:
            results.add_result(
                "启动监控器",
                False,
                f"启动失败: {str(e)}"
            )
        
        # 测试停止
        try:
            monitor.stop()
            results.add_result(
                "停止监控器",
                not monitor.is_running,
                "监控器成功停止"
            )
        except Exception as e:
            results.add_result(
                "停止监控器",
                False,
                f"停止失败: {str(e)}"
            )
    
    return results


def test_scheduler_initialization():
    """测试调度器初始化"""
    print("\n" + "="*60)
    print("测试8: 调度器初始化")
    print("="*60)
    
    results = TestResults()
    
    # 测试单例模式
    try:
        scheduler1 = ScanScheduler()
        scheduler2 = ScanScheduler()
        results.add_result(
            "调度器单例模式",
            scheduler1 is scheduler2,
            "两次获取的实例应该是同一个"
        )
    except Exception as e:
        results.add_result(
            "调度器单例模式",
            False,
            f"单例模式测试失败: {str(e)}"
        )
    
    # 测试初始状态
    try:
        scheduler = ScanScheduler()
        results.add_result(
            "调度器初始状态",
            not scheduler.is_running,
            "初始化时应该未运行"
        )
    except Exception as e:
        results.add_result(
            "调度器初始状态",
            False,
            f"初始状态测试失败: {str(e)}"
        )
    
    return results


def test_scheduler_job_management():
    """测试调度器任务管理"""
    print("\n" + "="*60)
    print("测试9: 调度器任务管理")
    print("="*60)
    
    results = TestResults()
    
    scheduler = ScanScheduler()
    
    # 测试添加任务
    try:
        scheduler.add_scheduled_scan(999, 60)  # 60分钟间隔
        results.add_result(
            "添加定时任务",
            True,
            "成功添加定时任务"
        )
    except Exception as e:
        results.add_result(
            "添加定时任务",
            False,
            f"添加任务失败: {str(e)}"
        )
    
    # 测试获取任务状态
    try:
        job_status = scheduler.get_job_status(999)
        results.add_result(
            "获取任务状态",
            job_status is not None,
            f"成功获取任务状态: {job_status}"
        )
    except Exception as e:
        results.add_result(
            "获取任务状态",
            False,
            f"获取状态失败: {str(e)}"
        )
    
    # 测试移除任务
    try:
        scheduler.remove_scheduled_scan(999)
        job_status = scheduler.get_job_status(999)
        results.add_result(
            "移除定时任务",
            job_status is None,
            "成功移除定时任务"
        )
    except Exception as e:
        results.add_result(
            "移除定时任务",
            False,
            f"移除任务失败: {str(e)}"
        )
    
    return results


def test_integration_scanning():
    """集成测试：端到端扫描流程"""
    print("\n" + "="*60)
    print("测试10: 集成测试 - 端到端扫描")
    print("="*60)
    
    results = TestResults()
    
    # 生成唯一的batch_id
    import uuid
    unique_batch_id = f"test_batch_{uuid.uuid4().hex[:8]}"
    
    # 创建临时测试目录
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        # 创建测试文件（只创建媒体文件，不创建字幕文件）
        video_files = [
            "Movie1.mp4",
            "Movie2.mkv",
            "Movie3.avi"
        ]
        
        for filename in video_files:
            filepath = temp_path / filename
            filepath.write_text("fake video content" * 1000)
            logger.info(f"创建测试文件: {filepath}")
        
        results.add_result(
            "创建测试文件",
            len(video_files) == 3,
            f"成功创建 {len(video_files)} 个测试文件"
        )
        
        # 初始化扫描器（不使用task_id，避免与数据库冲突）
        try:
            scanner = FileScanner(
                task_id=None,  # 不使用task_id
                batch_id="test_batch_integration",
                skip_mode="none"
            )
            results.add_result(
                "初始化扫描器",
                scanner is not None,
                "扫描器初始化成功"
            )
        except Exception as e:
            results.add_result(
                "初始化扫描器",
                False,
                f"初始化失败: {str(e)}"
            )
            return results
        
        # 执行扫描（异步）
        try:
            import asyncio
            
            async def run_scan():
                return await scanner.scan_directory(
                    path=str(temp_path),
                    recursive=True,
                    scan_type='full',
                    batch_id=unique_batch_id
                )
            
            scan_result = asyncio.run(run_scan())
            results.add_result(
                "执行扫描",
                scan_result is not None,
                f"扫描完成，发现 {len(scanner.scanned_files)} 个文件"
            )
            
            # 验证扫描结果
            media_files_count = sum(1 for f in scanner.scanned_files if f.suffix.lower() in MEDIA_EXTENSIONS)
            
            results.add_result(
                "验证媒体文件扫描",
                media_files_count == 3,
                f"扫描到 {media_files_count} 个媒体文件（预期3个）"
            )
            
            results.add_result(
                "验证新文件统计",
                len(scanner.new_files) == 3,
                f"新文件数量为 {len(scanner.new_files)}（预期3个）"
            )
            
            results.add_result(
                "验证扫描状态",
                len(scanner.failed_files) == 0,
                f"没有处理失败的文件"
            )
            
        except Exception as e:
            results.add_result(
                "执行扫描",
                False,
                f"扫描失败: {str(e)}"
            )
    
    return results


def main():
    """主测试函数"""
    print("\n" + "="*60)
    print("扫描模块功能性测试")
    print("="*60)
    print(f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60)
    
    # 运行所有测试
    all_results = []
    
    try:
        all_results.append(test_media_extensions())
    except Exception as e:
        logger.error(f"媒体扩展名测试失败: {e}")
        print(f"❌ 媒体扩展名测试失败: {e}")
    
    try:
        all_results.append(test_subtitle_extensions())
    except Exception as e:
        logger.error(f"字幕扩展名测试失败: {e}")
        print(f"❌ 字幕扩展名测试失败: {e}")
    
    try:
        all_results.append(test_file_scanner_initialization())
    except Exception as e:
        logger.error(f"扫描器初始化测试失败: {e}")
        print(f"❌ 扫描器初始化测试失败: {e}")
    
    try:
        all_results.append(test_keyword_library_detection())
    except Exception as e:
        logger.error(f"关键词库检测测试失败: {e}")
        print(f"❌ 关键词库检测测试失败: {e}")
    
    try:
        all_results.append(test_ignore_patterns())
    except Exception as e:
        logger.error(f"忽略模式测试失败: {e}")
        print(f"❌ 忽略模式测试失败: {e}")
    
    try:
        all_results.append(test_file_monitor_initialization())
    except Exception as e:
        logger.error(f"监控器初始化测试失败: {e}")
        print(f"❌ 监控器初始化测试失败: {e}")
    
    try:
        all_results.append(test_file_monitor_lifecycle())
    except Exception as e:
        logger.error(f"监控器生命周期测试失败: {e}")
        print(f"❌ 监控器生命周期测试失败: {e}")
    
    try:
        all_results.append(test_scheduler_initialization())
    except Exception as e:
        logger.error(f"调度器初始化测试失败: {e}")
        print(f"❌ 调度器初始化测试失败: {e}")
    
    try:
        all_results.append(test_scheduler_job_management())
    except Exception as e:
        logger.error(f"调度器任务管理测试失败: {e}")
        print(f"❌ 调度器任务管理测试失败: {e}")
    
    try:
        all_results.append(test_integration_scanning())
    except Exception as e:
        logger.error(f"集成测试失败: {e}")
        print(f"❌ 集成测试失败: {e}")
    
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
    report_path = "tests/SCAN_FUNCTIONALITY_TEST_REPORT.md"
    
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write("# 扫描模块功能性测试报告\n\n")
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
            f.write("✅ **所有测试通过！扫描模块功能正常。**\n")
        else:
            f.write(f"⚠️ **有 {total_failed} 个测试失败，需要修复。**\n")
    
    print(f"\n测试报告已生成: {report_path}")


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)