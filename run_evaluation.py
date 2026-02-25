"""
快速运行评估模块的脚本
"""

import subprocess
import sys
from pathlib import Path

# 获取项目根目录
project_root = Path(__file__).parent

# 运行评估
print("开始运行ROUGE评估...")
print("=" * 80)

result = subprocess.run(
    [sys.executable, str(project_root / "src" / "step5_evaluation" / "main.py")],
    cwd=str(project_root)
)

if result.returncode == 0:
    print("\n" + "=" * 80)
    print("评估成功完成！")
    print("=" * 80)
else:
    print("\n" + "=" * 80)
    print("评估失败，请查看日志")
    print("=" * 80)
    sys.exit(result.returncode)
