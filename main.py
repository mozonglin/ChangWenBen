import os
import sys
from app import app
from app_config import configure_app

# 确保目录存在
def ensure_directories():
    """确保必要的目录存在"""
    dirs = ['templates', 'static', 'static/uploads', 'conversations']
    for directory in dirs:
        os.makedirs(directory, exist_ok=True)

if __name__ == '__main__':
    # 确保目录存在
    ensure_directories()
    
    # 应用配置
    configure_app(app)
    
    # 启动应用
    app.run(debug=True, host='0.0.0.0', port=5000) 