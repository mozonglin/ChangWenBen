import os
import sys
from main import ensure_directories
from app import app
from app_config import configure_app
from flask_cors import CORS

# 启用CORS
CORS(app, resources={r"/*": {"origins": "*"}})

if __name__ == '__main__':
    # 确保目录存在
    ensure_directories()
    
    # 配置应用程序
    configure_app(app)
    
    # 启动应用
    print("正在启动服务...")
    app.run(host='0.0.0.0', debug=True)
    
    print("应用启动在 http://localhost:5000/")
    print("使用Ctrl+C停止应用") 