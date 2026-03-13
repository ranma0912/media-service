import re

# 读取文件
with open(r'c:\Users\ranma\CodeGeeXProjects\media-service\frontend\src\views\ScanManagement.vue', 'r', encoding='utf-8') as f:
    content = f.read()

# 替换错误的反斜杠转义
content = content.replace("path.includes(''')", "path.includes('\\\\')")
content = content.replace(" ? ''", " ? '\\\\'")

# 写回文件
with open(r'c:\Users\ranma\CodeGeeXProjects\media-service\frontend\src\views\ScanManagement.vue', 'w', encoding='utf-8') as f:
    f.write(content)

print("修复完成")
