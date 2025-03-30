import os
import json
import asyncio
import nest_asyncio
from flask import Flask, render_template, request, jsonify, send_file, redirect
from process_request import load_prompt_by_id, process_user_input, process_request_with_prompt_id
from agent_system import analyze_data_with_role_id
import time

# 应用nest_asyncio以允许在已有事件循环中运行asyncio.run()
nest_asyncio.apply()

app = Flask(__name__)

# 确保模板和静态文件目录存在
os.makedirs('templates', exist_ok=True)
os.makedirs('static', exist_ok=True)
os.makedirs('static/uploads', exist_ok=True)
os.makedirs('conversations', exist_ok=True)

# 使用异步函数包装，避免直接使用asyncio.run()
async def async_load_prompt_by_id(prompt_id):
    return await load_prompt_by_id(prompt_id)

async def async_process_user_input(user_data, prompt_id, file_name):
    return await process_user_input(user_data, prompt_id, file_name)

# 使用异步函数执行器
def run_async(coro):
    loop = asyncio.get_event_loop()
    return loop.run_until_complete(coro)

# 加载所有prompt信息供前端选择
def load_all_prompts():
    try:
        with open("prompt.json", "r", encoding="utf-8") as f:
            prompts = json.load(f)
        return prompts
    except Exception as e:
        print(f"加载prompt列表失败: {str(e)}")
        return []

@app.route('/')
def index():
    # 重定向到助理页面
    return redirect('/助理.html')

@app.route('/analyze', methods=['POST'])
def analyze():
    try:
        # 获取请求数据，现在只需要prompt_id
        prompt_id = int(request.form.get('prompt_id'))
        
        # 使用安全的异步执行方式处理分析
        result = run_async(async_process_user_input(None, prompt_id, f"web_request_{prompt_id}"))
        
        # 确保返回json响应
        return jsonify(result)
            
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        print(f"分析错误详情: {error_details}")
        return jsonify({"success": False, "message": f"请求处理出错: {str(e)}"})

@app.route('/get_prompt_info/<int:prompt_id>')
def get_prompt_info(prompt_id):
    try:
        prompt_info = run_async(async_load_prompt_by_id(prompt_id))
        if prompt_info:
            return jsonify({"success": True, "data": prompt_info})
        return jsonify({"success": False, "message": f"找不到ID为 {prompt_id} 的prompt"})
    except Exception as e:
        return jsonify({"success": False, "message": f"获取prompt信息出错: {str(e)}"})

@app.route('/reports/<path:filename>')
def get_report(filename):
    """提供报告文件下载"""
    try:
        return send_file(filename, as_attachment=True)
    except Exception as e:
        return f"报告文件不存在或无法访问: {str(e)}", 404

@app.route('/api_analyze/<int:prompt_id>', methods=['POST'])
def api_analyze(prompt_id):
    """使用原始API进行分析的端点"""
    try:
        # 使用process_request_with_prompt_id处理
        api_result = process_request_with_prompt_id(prompt_id)
        
        if not api_result:
            return jsonify({"success": False, "message": "API处理失败"})
            
        # 保存API结果到文件
        api_filename = f"分析结果_ID{prompt_id}_api.json"
        with open(api_filename, 'w', encoding='utf-8') as f:
            json.dump(api_result, f, ensure_ascii=False, indent=2)
        
        # 构建数据结构以传递给agent_system
        data = {
            "api_result": api_result,
            "prompt_info": run_async(async_load_prompt_by_id(prompt_id)),
            "charts": []
        }
        
        # 如果API结果中有response，提取出来添加到charts中
        if "response" in api_result:
            response_text = api_result["response"]
            data["charts"].append({
                "chart_name": "API分析结果",
                "values": [{"name": "分析结果", "content": response_text}]
            })
        
        # 调用agent_system进行深度分析
        print(f"将API结果传递给agent_system进行深度分析...")
        file_name = f"api_request_{prompt_id}"
        analysis_result = run_async(analyze_data_with_role_id(data, prompt_id, file_name))
        
        if analysis_result:
            return jsonify({
                "success": True, 
                "message": "分析成功",
                "api_result": api_result,
                "agent_result": analysis_result,
                "report_file": analysis_result.get("report_file", ""),
                "api_file": api_filename
            })
        else:
            return jsonify({
                "success": False, 
                "message": "agent_system分析失败",
                "api_result": api_result,
                "api_file": api_filename
            })
        
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        print(f"API分析错误详情: {error_details}")
        return jsonify({"success": False, "message": f"API请求处理出错: {str(e)}"})

@app.route('/api_chat', methods=['POST'])
def api_chat():
    """处理聊天消息的API端点"""
    try:
        data = request.json
        if not data:
            return jsonify({"success": False, "message": "请求数据为空"})
            
        message = data.get('message')
        conversation_id = data.get('conversation_id')
        history = data.get('history', [])
        mode = data.get('mode', 'deepseek-v3')  # 默认使用DeepSeek-V3
        
        print(f"收到请求：消息='{message}'，模式='{mode}'")
        
        # 根据模式选择不同的模型
        try:
            # 使用API可能会失败，添加异常处理
            from openai import OpenAI
            client = OpenAI(
                api_key="sk-zkgnhawsdghsmbkeqozsbrguyxblkehoxniouisfusdvgiow", 
                base_url="https://api.siliconflow.cn/v1"
            )
            
            # 根据模式选择合适的模型
            model_name = "Pro/deepseek-ai/DeepSeek-R1" if mode == 'deepseek-r1' else "Pro/deepseek-ai/DeepSeek-V3"
            system_prompt = "你是数据分析专家，用Markdown输出结果" if mode == 'deepseek-r1' else "你是一个助手，简洁地用Markdown回答问题"
            max_tokens = 16384 if mode == 'deepseek-r1' else 8192
            
            # 处理历史消息，限制最多10条
            history_messages = []
            if history:
                for msg in history[-10:]:
                    if msg.get('role') and msg.get('content'):
                        history_messages.append({"role": msg["role"], "content": msg["content"]})
            
            # 构建API请求消息
            messages = [
                {"role": "system", "content": system_prompt}
            ]
            messages.extend(history_messages)
            messages.append({"role": "user", "content": message})
            
            print(f"调用API，模型={model_name}，系统提示词='{system_prompt}'")
            
            # 调用API
            response = client.chat.completions.create(  
                model=model_name,  
                messages=messages,  
                temperature=0.7,  
                max_tokens=max_tokens,
                stream=False
            )
            ai_response = response.choices[0].message.content
            print(f"API返回成功，响应长度={len(ai_response)}")
            
            # 存储对话历史
            save_conversation(conversation_id, message, ai_response, history)
            
            return jsonify({
                "success": True,
                "response": ai_response,
                "conversation_id": conversation_id
            })
        except Exception as api_error:
            # API调用失败，返回模拟响应
            print(f"API调用失败: {str(api_error)}，使用模拟响应")
            
            # 根据不同模式返回不同模拟响应
            if mode == 'deepseek-r1':
                ai_response = f"""## 深度思考模式回答（模拟）

这是使用**DeepSeek-R1**模型的模拟回答，因为API调用失败：{str(api_error)}

### 您的问题
{message}

### 分析结果
根据您的问题，我们可以从多个角度进行分析：

1. **主要观点**
   - 这是关键点1
   - 这是关键点2
   - 这是关键点3

2. **数据支持**
   ```python
   import pandas as pd
   
   # 数据分析示例
   data = {'类别': ['A', 'B', 'C'], 
           '数值': [10, 20, 30]}
   df = pd.DataFrame(data)
   print(df)
   ```

3. **结论**
   综合以上分析，我们可以得出以下结论...

【注意：这是模拟响应，实际API调用失败】"""
            else:
                ai_response = f"""这是普通模式下的模拟回答。您问的问题是"{message}"。

API调用失败：{str(api_error)}

我们可以这样回答：
- 第一点
- 第二点
- 第三点

【注意：这是模拟响应，实际API调用失败】"""
            
            # 存储对话历史
            save_conversation(conversation_id, message, ai_response, history)
            
            return jsonify({
                "success": True,
                "response": ai_response,
                "conversation_id": conversation_id,
                "is_mock": True
            })
            
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        print(f"API聊天错误详情: {error_details}")
        return jsonify({"success": False, "message": f"处理聊天消息出错: {str(e)}"})

@app.route('/api_image', methods=['POST'])
def api_image():
    """处理图片上传和分析的API端点"""
    try:
        if 'image' not in request.files:
            return jsonify({"success": False, "message": "没有上传图片"})
            
        image_file = request.files['image']
        conversation_id = request.form.get('conversation_id')
        
        if not image_file.filename:
            return jsonify({"success": False, "message": "图片文件名为空"})
            
        # 保存上传的图片
        upload_dir = os.path.join('static', 'uploads')
        os.makedirs(upload_dir, exist_ok=True)
        
        # 生成唯一文件名
        filename = f"{int(time.time())}_{image_file.filename}"
        file_path = os.path.join(upload_dir, filename)
        image_file.save(file_path)
        
        print(f"图片已保存: {file_path}")
        
        try:
            # 使用多模态模型分析图片
            from openai import OpenAI
            client = OpenAI(
                api_key="sk-zkgnhawsdghsmbkeqozsbrguyxblkehoxniouisfusdvgiow", 
                base_url="https://api.siliconflow.cn/v1"
            )
            
            with open(file_path, "rb") as img_file:
                # 图片转base64
                import base64
                image_base64 = base64.b64encode(img_file.read()).decode('utf-8')
            
                print("调用图片分析API...")
                response = client.chat.completions.create(
                    model="Qwen/Qwen2-VL-72B-Instruct",
                    messages=[
                        {
                            "role": "user",
                            "content": [
                                {
                                    "type": "image_url",
                                    "image_url": {
                                        "url": f"data:image/jpeg;base64,{image_base64}"
                                    }
                                },
                                {
                                    "type": "text",
                                    "text": "详细描述这张图片的内容，用中文回答，使用Markdown格式。"
                                }
                            ]
                        }
                    ],
                    stream=False
                )
                
            ai_response = response.choices[0].message.content
            print(f"图片分析完成，响应长度={len(ai_response)}")
            
        except Exception as api_error:
            # API调用失败，返回模拟响应
            print(f"图片分析API调用失败: {str(api_error)}，使用模拟响应")
            ai_response = f"""## 图片分析结果（模拟）

这是对您上传的图片 `{os.path.basename(file_path)}` 的模拟分析结果。

**注意：API调用失败，无法提供真实分析**
错误信息: {str(api_error)}

1. **图片信息**
   - 文件名: {os.path.basename(file_path)}
   - 上传时间: {time.strftime('%Y-%m-%d %H:%M:%S')}

2. **常规分析**
   这通常会包含对图片内容的详细描述，但由于API调用失败，无法提供。

您可以稍后重试，或者直接在对话中描述图片内容，我们可以基于您的描述进行讨论。
"""
        
        # 保存到对话历史
        save_image_message(conversation_id, file_path, ai_response)
        
        return jsonify({
            "success": True,
            "response": ai_response,
            "image_path": f"/static/uploads/{filename}",
            "conversation_id": conversation_id
        })
        
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        print(f"图片处理错误详情: {error_details}")
        return jsonify({"success": False, "message": f"处理图片出错: {str(e)}"})

@app.route('/api_test', methods=['GET'])
def api_test():
    """用于测试API是否正常工作的简单端点"""
    return jsonify({
        "success": True,
        "message": "API端点正常工作",
        "time": time.strftime('%Y-%m-%d %H:%M:%S')
    })

@app.route('/api_test_chat', methods=['GET'])
def api_test_chat():
    """用于测试聊天API的简单端点"""
    message = request.args.get('message', '你好，请介绍自己')
    mode = request.args.get('mode', 'normal')
    
    try:
        print(f"测试聊天 - 消息: '{message}', 模式: {mode}")
        
        # 简单的模拟响应 - 不调用真实API
        if mode == 'deepthink':
            response = f"""## 测试响应（深度思考模式）

这是一个测试响应，用于验证API端点是否正常工作。

### 您的测试消息
{message}

### 分析
这是一个测试分析，不调用真实的AI模型。

1. **测试点1**
   - 子点A
   - 子点B

2. **测试点2**
   ```python
   # 这是一段测试代码
   print("Hello, API test!")
   ```

时间戳: {time.strftime('%Y-%m-%d %H:%M:%S')}"""
        else:
            response = f"""## 测试响应（普通模式）

这是一个测试响应，用于验证API端点是否正常工作。您的测试消息是: "{message}"

- 测试回复1
- 测试回复2
- 测试回复3

时间戳: {time.strftime('%Y-%m-%d %H:%M:%S')}"""
        
        return jsonify({
            "success": True,
            "response": response,
            "conversation_id": "test_conversation",
            "is_test": True
        })
        
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        print(f"测试聊天API错误: {error_details}")
        return jsonify({
            "success": False,
            "message": f"测试聊天API出错: {str(e)}"
        })

def save_conversation(conversation_id, user_message, ai_response, history):
    """保存对话历史"""
    try:
        conversations_dir = 'conversations'
        os.makedirs(conversations_dir, exist_ok=True)
        
        # 构建新的历史记录
        new_history = history.copy() if history else []
        new_history.append({"role": "user", "content": user_message})
        new_history.append({"role": "assistant", "content": ai_response})
        
        # 保存到文件
        with open(f"{conversations_dir}/{conversation_id}.json", 'w', encoding='utf-8') as f:
            json.dump(new_history, f, ensure_ascii=False, indent=2)
            
    except Exception as e:
        print(f"保存对话历史出错: {str(e)}")

def save_image_message(conversation_id, image_path, ai_response):
    """保存图片消息到对话历史"""
    try:
        conversations_dir = 'conversations'
        os.makedirs(conversations_dir, exist_ok=True)
        
        # 读取现有历史（如果有）
        history_file = f"{conversations_dir}/{conversation_id}.json"
        
        if os.path.exists(history_file):
            with open(history_file, 'r', encoding='utf-8') as f:
                history = json.load(f)
        else:
            history = []
        
        # 添加图片消息和AI响应
        history.append({"role": "user", "content": f"[上传了图片: {os.path.basename(image_path)}]", "image": image_path})
        history.append({"role": "assistant", "content": ai_response})
        
        # 保存到文件
        with open(history_file, 'w', encoding='utf-8') as f:
            json.dump(history, f, ensure_ascii=False, indent=2)
            
    except Exception as e:
        print(f"保存图片消息出错: {str(e)}")

@app.route('/助理.html')
def assistant_page():
    """助理页面路由"""
    return render_template('助理.html')

if __name__ == '__main__':
    # 确保必要的目录存在
    os.makedirs('templates', exist_ok=True)
    os.makedirs('static', exist_ok=True)
    os.makedirs('static/uploads', exist_ok=True)
    os.makedirs('conversations', exist_ok=True)
    
    print("="*80)
    print("AI助手服务已启动")
    print("请访问: http://127.0.0.1:5000/助理.html")
    print("="*80)
    
    # 启动Flask应用
    app.run(host='0.0.0.0', port=5000, debug=True, threaded=True) 