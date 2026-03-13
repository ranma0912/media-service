
import sys

file_path = r'c:\Users\ranma\CodeGeeXProjects\media-service\frontend\src\views\ScanManagement.vue'

# 读取文件
with open(file_path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

# 找到并删除包含 REPLACE 的行
new_lines = []
for line in lines:
    if '+++++++ REPLACE' not in line:
        new_lines.append(line)

# 写回文件
with open(file_path, 'w', encoding='utf-8') as f:
    f.writelines(new_lines)

print(f"文件已修复: {file_path}")
print(f"删除了 {len(lines) - len(new_lines)} 行")
