"""
检查并修复项目文件的编码问题
确保所有代码文件使用 UTF-8 编码
"""
import sys
from pathlib import Path
import chardet
import os

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def detect_file_encoding(file_path):
    """检测文件编码"""
    try:
        with open(file_path, 'rb') as f:
            raw_data = f.read(1024)  # 读取前1024字节检测编码
            result = chardet.detect(raw_data)
            return result['encoding'], result['confidence']
    except Exception as e:
        return None, 0


def convert_to_utf8(file_path, original_encoding):
    """将文件转换为UTF-8编码"""
    try:
        # 读取原始内容
        with open(file_path, 'r', encoding=original_encoding) as f:
            content = f.read()
        
        # 写入UTF-8编码
        with open(file_path, 'w', encoding='utf-8', newline='') as f:
            f.write(content)
        
        return True
    except Exception as e:
        print(f"转换失败: {file_path}, 错误: {e}")
        return False


def check_python_files(directory):
    """检查Python文件"""
    print("\n=== 检查 Python 文件 ===")
    
    # 需要检查的Python文件
    python_files = [
        'app/main.py',
        'app/api/server.py',
        'app/api/scan.py',
        'app/api/file_tasks.py',
        'app/db/models.py',
        'app/db/session.py',
        'app/core/config.py',
        'app/core/websocket.py',
        'app/modules/scanner/scanner.py',
        'app/modules/recognizer/recognizer.py',
        'app/modules/organizer/organizer.py',
    ]
    
    for file_path_str in python_files:
        file_path = project_root / file_path_str
        if not file_path.exists():
            print(f"⚠ 文件不存在: {file_path_str}")
            continue
        
        encoding, confidence = detect_file_encoding(file_path)
        
        if encoding and encoding.lower() != 'utf-8' and confidence > 0.8:
            print(f"🔧 转换 {file_path_str}: {encoding} (置信度: {confidence:.2f}) -> UTF-8")
            if convert_to_utf8(file_path, encoding):
                print(f"✅ {file_path_str} 转换成功")
            else:
                print(f"❌ {file_path_str} 转换失败")
        elif encoding and encoding.lower() == 'utf-8':
            print(f"✅ {file_path_str}: UTF-8")
        else:
            print(f"⚠ {file_path_str}: 无法检测编码")


def check_frontend_files(directory):
    """检查前端文件"""
    print("\n=== 检查前端文件 ===")
    
    frontend_dir = project_root / 'frontend' / 'src'
    
    # 检查所有 .vue 和 .js 文件
    for file_path in frontend_dir.rglob('*.vue'):
        check_frontend_file(file_path)
    
    for file_path in frontend_dir.rglob('*.js'):
        check_frontend_file(file_path)
    
    for file_path in frontend_dir.rglob('*.scss'):
        check_frontend_file(file_path)


def check_frontend_file(file_path):
    """检查单个前端文件"""
    try:
        relative_path = file_path.relative_to(project_root)
        encoding, confidence = detect_file_encoding(file_path)
        
        if encoding and encoding.lower() != 'utf-8' and confidence > 0.8:
            print(f"🔧 转换 {relative_path}: {encoding} (置信度: {confidence:.2f}) -> UTF-8")
            if convert_to_utf8(file_path, encoding):
                print(f"✅ {relative_path} 转换成功")
            else:
                print(f"❌ {relative_path} 转换失败")
        elif encoding and encoding.lower() == 'utf-8':
            print(f"✅ {relative_path}: UTF-8")
        else:
            print(f"⚠ {relative_path}: 无法检测编码")
    except Exception as e:
        print(f"❌ {file_path}: 检查失败 - {e}")


def add_utf8_header_to_python(file_path):
    """为Python文件添加UTF-8编码声明"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        # 检查是否已有编码声明
        for line in lines[:2]:
            if 'coding' in line and 'utf-8' in line.lower():
                return False  # 已有声明，不需要添加
        
        # 在文件开头添加编码声明
        new_lines = ['# -*- coding: utf-8 -*-\n'] + lines
        
        with open(file_path, 'w', encoding='utf-8', newline='') as f:
            f.writelines(new_lines)
        
        return True
    except Exception as e:
        print(f"添加编码声明失败: {file_path}, 错误: {e}")
        return False


def main():
    """主函数"""
    print("=== 项目文件编码检查与修复 ===")
    print(f"项目根目录: {project_root}")
    
    # 检查 chardet 是否可用
    try:
        import chardet
    except ImportError:
        print("❌ chardet 模块未安装，请运行: pip install chardet")
        return
    
    # 检查Python文件
    check_python_files(project_root)
    
    # 检查前端文件
    check_frontend_files(project_root)
    
    print("\n=== 编码检查完成 ===")


if __name__ == "__main__":
    main()