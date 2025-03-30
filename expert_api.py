import os
import sys
import json
import time
import threading
import asyncio
from flask import Blueprint, jsonify, request, Response, stream_with_context, send_from_directory
from flask_cors import CORS
from functools import wraps

# 将当前目录添加到系统路径，确保可以导入其他模块
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import process_user_input, load_prompt_by_id, run_async
from api2 import generate_prompt_from_user_input, save_prompt_to_json

# 使用Blueprint创建路由组
expert_api = Blueprint('expert_api', __name__, url_prefix='/expert_api')
CORS(expert_api)  # 启用CORS

# 用于存储处理日志的全局字典
processing_logs = {}
# 用于存储处理状态的全局字典
processing_status_dict = {}

# 提供prompt.json文件访问的路由
@expert_api.route('/prompt.json', methods=['GET'])
def expert_prompt_json():
    """提供prompt.json文件访问"""
    return send_from_directory('.', 'prompt.json')

# 拦截print函数的装饰器
def capture_prints(prompt_id):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # 初始化该prompt_id的日志
            processing_logs[prompt_id] = []
            
            # 保存原始的stdout
            original_stdout = sys.stdout
            
            # 创建一个自定义的输出流
            class StdoutInterceptor:
                def write(self, message):
                    # 写入到原始stdout
                    original_stdout.write(message)
                    # 同时记录到日志
                    if prompt_id in processing_logs:
                        processing_logs[prompt_id].append(message)
                    # 立即刷新
                    self.flush()
                
                def flush(self):
                    original_stdout.flush()
            
            # 替换sys.stdout
            sys.stdout = StdoutInterceptor()
            
            try:
                # 执行函数
                result = func(*args, **kwargs)
                return result
            finally:
                # 恢复原始stdout
                sys.stdout = original_stdout
        
        return wrapper
    return decorator

@expert_api.route('/analyze', methods=['POST'])
def analyze():
    """处理提示词分析请求并返回结果"""
    try:
        # 获取prompt_id
        prompt_id = int(request.form.get('prompt_id', 0))
        if prompt_id <= 0:
            return jsonify({"success": False, "message": "无效的提示词ID"})
        
        # 清除之前的日志
        if prompt_id in processing_logs:
            del processing_logs[prompt_id]
        
        # 设置处理状态
        processing_status_dict[prompt_id] = {
            "is_processing": True,
            "start_time": time.time(),
            "result": None
        }
        
        # 执行分析，捕获输出
        result = process_with_logs(prompt_id)
        
        # 更新处理状态
        processing_status_dict[prompt_id]["is_processing"] = False
        processing_status_dict[prompt_id]["result"] = result
        
        # 合并日志和结果
        log_text = "\n".join(processing_logs.get(prompt_id, []))
        
        # 构建格式化的响应
        response = f"""
## 分析结果

### 处理过程：
```
{log_text}
```

### 分析输出：
{result.get('response', '')}
"""
        
        return jsonify({
            "success": True,
            "response": response,
            "raw_result": result
        })
    
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        
        # 更新处理状态为错误
        if prompt_id in processing_status_dict:
            processing_status_dict[prompt_id]["is_processing"] = False
            processing_status_dict[prompt_id]["error"] = str(e)
        
        return jsonify({
            "success": False,
            "message": f"处理提示词出错: {str(e)}",
            "details": error_details
        })

@expert_api.route('/analyze_stream', methods=['GET', 'POST'])
def analyze_stream():
    """流式处理提示词分析请求，实时返回结果"""
    try:
        prompt_id = int(request.form.get('prompt_id', 0))
        if prompt_id <= 0:
            prompt_id = int(request.args.get('prompt_id', 0))
            if prompt_id <= 0:
                return jsonify({"success": False, "message": "无效的提示词ID"})
        
        print(f"接收到SSE连接请求: prompt_id={prompt_id}")
        
        # 执行异步分析
        def generate():
            try:
                # 初始化日志索引
                last_log_index = 0
                
                # 清除之前的日志
                if prompt_id in processing_logs:
                    del processing_logs[prompt_id]
                
                # 设置处理状态
                processing_status_dict[prompt_id] = {
                    "is_processing": True,
                    "start_time": time.time(),
                    "result": None
                }
                
                # 启动分析过程（在后台线程中）
                result_container = {"result": None}
                
                def run_analysis():
                    try:
                        print(f"开始在后台线程中分析 prompt_id={prompt_id}")
                        result = process_with_logs(prompt_id)
                        result_container["result"] = result
                        processing_status_dict[prompt_id]["is_processing"] = False
                        processing_status_dict[prompt_id]["result"] = result
                        print(f"后台分析完成 prompt_id={prompt_id}")
                    except Exception as e:
                        import traceback
                        error_details = traceback.format_exc()
                        print(f"后台分析出错 prompt_id={prompt_id}: {str(e)}")
                        print(error_details)
                        processing_status_dict[prompt_id]["is_processing"] = False
                        processing_status_dict[prompt_id]["error"] = str(e)
                        result_container["result"] = {"success": False, "message": str(e), "details": error_details}
                
                analysis_thread = threading.Thread(target=run_analysis)
                analysis_thread.daemon = True
                analysis_thread.start()
                
                # 发送初始消息
                yield f"data: {json.dumps({'type': 'start', 'message': '开始处理...'})}\n\n"
                
                # 连接保持的最大时间(秒)
                max_duration = 600  # 10分钟
                start_time = time.time()
                last_activity_time = start_time
                
                # 持续检查日志更新并发送
                while (processing_status_dict.get(prompt_id, {}).get("is_processing", False) or 
                       analysis_thread.is_alive()) and time.time() - start_time < max_duration:
                    
                    current_logs = processing_logs.get(prompt_id, [])
                    
                    if last_log_index < len(current_logs):
                        # 有新日志，发送出去
                        new_logs = current_logs[last_log_index:]
                        last_log_index = len(current_logs)
                        last_activity_time = time.time()
                        
                        # 添加调试信息
                        print(f"发送新日志 {len(new_logs)} 条 (prompt_id={prompt_id})")
                        
                        # 单条发送，而不是一次性发送多条
                        for log in new_logs:
                            try:
                                log_json = json.dumps({'type': 'log', 'logs': [log]})
                                yield f"data: {log_json}\n\n"
                            except Exception as e:
                                print(f"发送日志出错: {str(e)}")
                        
                        # 添加一个刷新
                        yield f"data: {json.dumps({'type': 'ping'})}\n\n"
                    elif time.time() - last_activity_time > 10:  # 如果超过10秒没有新活动，发送ping
                        last_activity_time = time.time()
                        yield f"data: {json.dumps({'type': 'ping', 'timestamp': time.time()})}\n\n"
                    
                    # 减少轮询间隔，更快获取日志
                    time.sleep(0.1)  # 从0.5秒减少到0.1秒
                
                # 处理完成，发送最终结果
                if time.time() - start_time >= max_duration:
                    print(f"SSE连接超时 prompt_id={prompt_id}")
                    processing_status_dict[prompt_id]["is_processing"] = False
                    processing_status_dict[prompt_id]["error"] = "连接超时"
                    result = {"success": False, "message": "连接超时，请刷新页面查看结果"}
                else:
                    result = result_container["result"] or {"success": False, "message": "处理被中断"}
                
                # 确保响应内容正确格式化
                if isinstance(result, dict):
                    # 如果是字典，确保包含必要的字段
                    response_content = result.get('response', '')
                    if not response_content and 'raw_result' in result and isinstance(result['raw_result'], dict):
                        response_content = result['raw_result'].get('response', '')
                else:
                    # 如果是其他类型，转换为字符串
                    response_content = str(result)
                
                # 构建最终响应
                final_response = {
                    "type": "complete",
                    "success": True if isinstance(result, dict) and result.get('success', False) else True,
                    "result": {
                        "response": response_content,
                        "raw_result": result if isinstance(result, dict) else {"response": str(result)},
                        "report_file": result.get("report_file", "") if isinstance(result, dict) else "",
                        "report_content": result.get("report_content", "") if isinstance(result, dict) else ""
                    },
                    "logs": processing_logs.get(prompt_id, [])
                }
                
                print(f"发送完成消息 prompt_id={prompt_id}")
                # 调试输出结果的结构
                print(f"结果类型: {type(result)}")
                if isinstance(result, dict):
                    print(f"结果键: {list(result.keys())}")
                    if 'response' in result:
                        print(f"响应前20个字符: {str(result['response'])[:20]}...")
                
                yield f"data: {json.dumps(final_response)}\n\n"
                
            except Exception as e:
                import traceback
                error_details = traceback.format_exc()
                print(f"SSE流处理出错: {str(e)}")
                print(error_details)
                
                error_response = {
                    "type": "error", 
                    "message": str(e),
                    "details": error_details
                }
                yield f"data: {json.dumps(error_response)}\n\n"
        
        # 设置正确的响应头
        return Response(
            stream_with_context(generate()),
            mimetype="text/event-stream",
            headers={
                'Cache-Control': 'no-cache, no-transform',
                'Connection': 'keep-alive',
                'X-Accel-Buffering': 'no',  # 禁用Nginx缓冲
                'Access-Control-Allow-Origin': '*'  # 允许跨域
            }
        )
    
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        print(f"SSE连接建立出错: {str(e)}")
        print(error_details)
        return jsonify({
            "success": False,
            "message": f"建立连接出错: {str(e)}",
            "details": error_details
        })

@capture_prints(0)  # 默认prompt_id为0
def process_with_logs(prompt_id):
    """执行分析过程并捕获输出"""
    # 更新装饰器的prompt_id
    global processing_logs
    processing_logs[prompt_id] = []
    
    print(f"开始处理提示词ID: {prompt_id}")
    sys.stdout.flush()  # 确保立即刷新
    
    print("正在加载提示词信息...")
    sys.stdout.flush()  # 确保立即刷新
    
    # 加载提示词信息
    prompt_info = run_async(load_prompt_by_id(prompt_id))
    
    if not prompt_info:
        print(f"错误: 未找到ID为 {prompt_id} 的提示词")
        sys.stdout.flush()  # 确保立即刷新
        return {"success": False, "message": f"未找到ID为 {prompt_id} 的提示词"}
    
    print(f"已加载提示词: {prompt_info.get('Role', '')} - {prompt_info.get('Action', '')}")
    sys.stdout.flush()  # 确保立即刷新
    
    print("开始分析数据...")
    sys.stdout.flush()  # 确保立即刷新
    
    # 设置文件名
    file_name = f"expert_request_{prompt_id}_{int(time.time())}"
    
    try:
        # 调用处理函数
        result = run_async(process_user_input(None, prompt_id, file_name))
        
        print("分析完成!")
        sys.stdout.flush()  # 确保立即刷新
        
        # 寻找生成的报告文件
        report_file = None
        report_content = ""
        
        # 尝试从结果中获取报告文件路径
        if isinstance(result, dict) and "report_file" in result:
            report_file = result["report_file"]
            print(f"从结果中找到报告文件: {report_file}")
        
        # 如果结果中没有报告文件路径，则尝试在当前目录查找
        if not report_file:
            import glob
            # 查找所有以report开头的md文件，按修改时间排序
            report_files = sorted(
                glob.glob("report*.md"), 
                key=lambda x: os.path.getmtime(x), 
                reverse=True
            )
            if report_files:
                report_file = report_files[0]  # 获取最新的报告文件
                print(f"在目录中找到最新的报告文件: {report_file}")
        
        # 如果找到了报告文件，读取其内容
        if report_file and os.path.exists(report_file):
            try:
                with open(report_file, "r", encoding="utf-8") as f:
                    report_content = f.read()
                print(f"已读取报告文件内容，长度: {len(report_content)} 字符")
            except Exception as e:
                print(f"读取报告文件出错: {str(e)}")
        else:
            print("未找到报告文件")
        
        # 标准化结果格式
        if isinstance(result, dict):
            # 如果找到了报告内容，将其作为response
            if report_content:
                result["response"] = report_content
                
            # 确保结果是标准格式的字典
            if "response" not in result:
                # 尝试获取可能的响应内容
                response_text = ""
                if "result" in result:
                    response_text = str(result["result"])
                elif "message" in result:
                    response_text = str(result["message"]) 
                else:
                    # 使用整个结果作为响应
                    response_text = str(result)
                
                # 构建标准格式
                return {
                    "success": result.get("success", True),
                    "response": response_text,
                    "raw_result": result,
                    "report_file": report_file,
                    "report_content": report_content
                }
            
            # 添加报告文件信息
            result["report_file"] = report_file
            result["report_content"] = report_content
            return result
        else:
            # 如果结果不是字典，包装成标准格式
            return {
                "success": True,
                "response": report_content or str(result),
                "raw_result": {"data": result},
                "report_file": report_file,
                "report_content": report_content
            }
            
    except Exception as e:
        print(f"处理过程中出错: {str(e)}")
        sys.stdout.flush()  # 确保立即刷新
        import traceback
        error_info = traceback.format_exc()
        print(error_info)
        return {
            "success": False, 
            "message": str(e),
            "response": f"处理出错: {str(e)}",
            "error_details": error_info
        }

@expert_api.route('/processing_status/<int:prompt_id>', methods=['GET'])
def processing_status(prompt_id):
    """获取处理状态和当前日志"""
    logs = processing_logs.get(prompt_id, [])
    status = processing_status_dict.get(prompt_id, {"is_processing": False})
    
    return jsonify({
        "prompt_id": prompt_id,
        "logs": logs,
        "log_count": len(logs),
        "is_processing": status.get("is_processing", False),
        "error": status.get("error", None)
    })

@expert_api.route('/auto_generate_prompt', methods=['POST'])
def auto_generate_prompt():
    """根据用户输入自动生成提示词"""
    try:
        # 获取请求数据，支持多种格式
        action_text = None
        
        if request.is_json:
            # JSON请求
            data = request.json
            if data:
                action_text = data.get('action')
        else:
            # 表单请求
            action_text = request.form.get('action')
            
            # 如果表单中没有，尝试从请求参数中获取
            if not action_text:
                action_text = request.args.get('action')
        
        # 打印请求信息以便调试
        print(f"收到生成提示词请求: action_text={action_text}")
        print(f"请求内容类型: {request.content_type}")
        print(f"请求方法: {request.method}")
        
        if not action_text:
            return jsonify({
                "success": False,
                "message": "缺少必要参数: action"
            })
        
        # 生成提示词（使用新的函数）
        generated_prompt = generate_prompt_from_user_input(action_text)
        
        if not generated_prompt:
            return jsonify({
                "success": False,
                "message": "生成提示词失败，请重试"
            })
        
        print(f"成功生成提示词: {generated_prompt.get('Role')}")
        
        # 保存到prompt.json（会自动安排300秒后删除）
        save_success = save_prompt_to_json(generated_prompt)
        
        if not save_success:
            return jsonify({
                "success": False,
                "message": "保存提示词失败"
            })
        
        return jsonify({
            "success": True,
            "prompt": generated_prompt,
            "message": "提示词生成成功，将在分析完成后自动删除"
        })
        
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        print(f"生成提示词出错: {str(e)}")
        print(error_details)
        
        return jsonify({
            "success": False,
            "message": f"生成提示词出错: {str(e)}",
            "details": error_details
        })

@expert_api.route('/prompt/<int:prompt_id>', methods=['GET'])
def get_prompt_by_id(prompt_id):
    """获取特定ID的提示词"""
    try:
        # 读取prompt.json文件
        with open('prompt.json', 'r', encoding='utf-8') as f:
            prompts = json.load(f)
        
        # 查找匹配ID的提示词
        for prompt in prompts:
            if prompt.get('id') == prompt_id:
                return jsonify(prompt)
        
        # 未找到匹配的提示词
        return jsonify({
            "success": False,
            "message": f"未找到ID为 {prompt_id} 的提示词"
        }), 404
        
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        print(f"获取提示词出错: {str(e)}")
        print(error_details)
        
        return jsonify({
            "success": False,
            "message": f"获取提示词出错: {str(e)}",
            "details": error_details
        }), 500

def register_expert_api(app):
    """注册专家API蓝图到应用"""
    app.register_blueprint(expert_api) 