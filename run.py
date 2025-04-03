import os
import sys
from flask_cors import CORS
from flask import Flask

# 首先导入app
from app import app

# 启用CORS
CORS(app, resources={r"/*": {"origins": "*"}})

# 手动导入和注册蓝图，确保不会遗漏
from routes import mobo_routes
from expert_api import register_expert_api

# 确保蓝图只注册一次
if 'mobo_routes' not in app.blueprints:
    app.register_blueprint(mobo_routes)
    print("已在run.py中注册mobo_routes蓝图")

# 注册专家API蓝图
register_expert_api(app)

if __name__ == '__main__':
    # 确保目录存在
    from main import ensure_directories
    ensure_directories()
    
    # 启动应用
    print("正在启动服务...")
    app.run(host='0.0.0.0', debug=True)
    
    print("应用启动在 http://localhost:5000/")
    print("使用Ctrl+C停止应用") 