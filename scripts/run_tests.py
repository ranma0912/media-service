"""
MediaService 项目测试脚本
"""
import sys
import json
import requests
from datetime import datetime
from pathlib import Path


def print_section(title):
    """打印测试区块标题"""
    print("")
    print("="*70)
    print(f"  {title}")
    print("="*70)
    print("")


def print_result(test_name, success, message=""):
    """打印测试结果"""
    status = "PASS" if success else "FAIL"
    print(f"{status} {test_name}")
    if message:
        print(f"    {message}")


def test_project_structure():
    """测试项目结构"""


def print_result(test_name, success, message=""):
    """打印测试结果"""
    status = "✅ PASS" if success else "❌ FAIL"
    print(f"{status} {test_name}")
    if message:
        print(f"    {message}")


def test_project_structure():
    """测试项目结构"""
    print_section("1. 项目结构测试")

    project_root = Path(__file__).parent.parent
    required_dirs = [
        "app", "app/api", "app/core", "app/db", "app/modules",
        "frontend", "frontend/src", "config", "data", "logs", "scripts"
    ]

    for dir_name in required_dirs:
        dir_path = project_root / dir_name
        print_result(
            f"目录存在: {dir_name}",
            dir_path.exists(),
            f"路径: {dir_path}" if dir_path.exists() else "目录不存在"
        )

    required_files = [
        "requirements.txt", "README.md", "PROJECT_PROGRESS.md",
        "PROJECT_LOG.md", "TEST_PLAN.md", "TEST_REPORT.md"
    ]

    for file_name in required_files:
        file_path = project_root / file_name
        print_result(
            f"文件存在: {file_name}",
            file_path.exists(),
            f"路径: {file_path}" if file_path.exists() else "文件不存在"
        )


def test_backend_service():
    """测试后端服务"""
    print_section("2. 后端服务测试")

    try:
        response = requests.get("http://localhost:8000/health", timeout=5)
        if response.status_code == 200:
            data = response.json()
            print_result(
                "后端服务健康检查",
                True,
                f"状态: {data.get('status')}, 版本: {data.get('version')}"
            )

            # 测试API端点
            endpoints = [
                "/api/media/stats",
                "/api/statistics/recognition",
                "/api/statistics/organize",
                "/api/statistics/media",
                "/api/statistics/overview"
            ]

            for endpoint in endpoints:
                try:
                    response = requests.get(f"http://localhost:8000{endpoint}", timeout=10)
                    print_result(
                        f"API端点: {endpoint}",
                        response.status_code == 200,
                        f"状态码: {response.status_code}"
                    )
                except Exception as e:
                    print_result(f"API端点: {endpoint}", False, f"错误: {str(e)}")
        else:
            print_result("后端服务健康检查", False, f"状态码: {response.status_code}")
    except Exception as e:
        print_result("后端服务连接", False, f"错误: {str(e)}")


def test_database():
    """测试数据库"""
    print_section("3. 数据库测试")

    project_root = Path(__file__).parent.parent
    db_path = project_root / "data" / "media_service.db"

    print_result(
        "数据库文件存在",
        db_path.exists(),
        f"路径: {db_path}" if db_path.exists() else "数据库不存在"
    )

    if db_path.exists():
        size = db_path.stat().st_size / 1024
        print_result("数据库文件大小", size > 0, f"大小: {size:.2f} KB")


def main():
    """主函数"""
    print("
" + "="*70)
    print("  MediaService 项目测试")
    print("="*70 + "
")

    # 运行测试
    test_project_structure()
    test_backend_service()
    test_database()

    # 测试总结
    print("
" + "="*70)
    print("  测试完成")
    print("="*70 + "
")


if __name__ == "__main__":
    main()
