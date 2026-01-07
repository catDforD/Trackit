#!/bin/bash
# Trackit Web应用启动脚本

echo "🚀 启动 Trackit 习惯追踪助手..."

# 检查虚拟环境
if [ ! -d "venv" ]; then
    echo "⚠️  虚拟环境不存在，正在创建..."
    python -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
else
    source venv/bin/activate
fi

# 清理旧进程
pkill -f "src.app" 2>/dev/null

# 启动应用（端口7862）
echo "📱 正在启动Web界面..."
echo "   访问地址: http://localhost:7862"
echo ""
echo "💡 提示: 按 Ctrl+C 停止应用"
echo ""

python -m src.app --port=7862
