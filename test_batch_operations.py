# -*- coding: utf-8 -*-
"""
测试批量操作接口的类型转换
"""
import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from pydantic import BaseModel, ConfigDict, Field, BeforeValidator
from typing import List, Union, Any, Annotated

# 定义转换函数
def to_int_list(value: Any) -> List[int]:
    """将值转换为整数列表的验证函数"""
    if value is None:
        return []
    if isinstance(value, list):
        result = []
        for item in value:
            if isinstance(item, int):
                result.append(item)
            elif isinstance(item, str):
                try:
                    result.append(int(item))
                except (ValueError, TypeError):
                    raise ValueError(f"无法将字符串 '{item}' 转换为整数")
            elif isinstance(item, float):
                result.append(int(item))
            else:
                raise ValueError(f"不支持的数据类型: {type(item)}")
        return result
    raise ValueError(f"预期的列表类型，得到: {type(value)}")

# 定义可接受int或str的列表类型
IntList = Annotated[List[int], BeforeValidator(to_int_list)]

# 复制BatchFileOperationRequest定义
class BatchFileOperationRequest(BaseModel):
    """批量文件操作请求 - 基于媒体文件ID"""
    model_config = ConfigDict(str_strip_whitespace=True)
    media_file_ids: IntList = Field(default_factory=list, description="媒体文件ID列表")

    def get_int_ids(self) -> List[int]:
        """获取转换后的整数ID列表（兼容旧代码）"""
        # media_file_ids已经通过BeforeValidator转换为整数列表
        return self.media_file_ids


def test_batch_operation_request():
    """测试BatchFileOperationRequest"""
    print("=" * 60)
    print("测试BatchFileOperationRequest类型转换")
    print("=" * 60)

    # 测试1: 纯整数列表
    print("\n测试1: 纯整数列表")
    try:
        request = BatchFileOperationRequest(media_file_ids=[1, 2, 3])
        print(f"  输入: [1, 2, 3]")
        print(f"  输出: {request.media_file_ids}")
        print(f"  类型: {[type(x).__name__ for x in request.media_file_ids]}")
        print("  ✓ 通过")
    except Exception as e:
        print(f"  ✗ 失败: {e}")

    # 测试2: 纯字符串列表
    print("\n测试2: 纯字符串列表")
    try:
        request = BatchFileOperationRequest(media_file_ids=["1", "2", "3"])
        print(f"  输入: ['1', '2', '3']")
        print(f"  输出: {request.media_file_ids}")
        print(f"  类型: {[type(x).__name__ for x in request.media_file_ids]}")
        print("  ✓ 通过")
    except Exception as e:
        print(f"  ✗ 失败: {e}")

    # 测试3: 混合类型列表
    print("\n测试3: 混合类型列表")
    try:
        request = BatchFileOperationRequest(media_file_ids=[1, "2", 3.0, " 4 "])
        print(f"  输入: [1, '2', 3.0, ' 4 ']")
        print(f"  输出: {request.media_file_ids}")
        print(f"  类型: {[type(x).__name__ for x in request.media_file_ids]}")
        print("  ✓ 通过")
    except Exception as e:
        print(f"  ✗ 失败: {e}")

    # 测试4: 空列表
    print("\n测试4: 空列表")
    try:
        request = BatchFileOperationRequest(media_file_ids=[])
        print(f"  输入: []")
        print(f"  输出: {request.media_file_ids}")
        print("  ✓ 通过")
    except Exception as e:
        print(f"  ✗ 失败: {e}")

    # 测试5: 带空格的字符串
    print("\n测试5: 带空格的字符串")
    try:
        request = BatchFileOperationRequest(media_file_ids=[" 1 ", " 2 ", " 3 "])
        print(f"  输入: [' 1 ', ' 2 ', ' 3 ']")
        print(f"  输出: {request.media_file_ids}")
        print("  ✓ 通过")
    except Exception as e:
        print(f"  ✗ 失败: {e}")

    # 测试6: 无效类型
    print("\n测试6: 无效类型（应该失败）")
    try:
        request = BatchFileOperationRequest(media_file_ids=[1, "invalid", 3])
        print(f"  ✗ 应该失败但没有失败")
    except Exception as e:
        print(f"  ✓ 正确捕获错误: {e}")

    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)


if __name__ == "__main__":
    test_batch_operation_request()
