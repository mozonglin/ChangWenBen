import os
import json
import asyncio
import nest_asyncio
from flask import Flask, render_template, request, jsonify, send_file, redirect, Response, stream_with_context, send_from_directory
from process_request import load_prompt_by_id, process_user_input, process_request_with_prompt_id
from agent_system import analyze_data_with_role_id
import time
import uuid
from datetime import datetime
from werkzeug.utils import secure_filename
from openai import OpenAI

# 应用nest_asyncio以允许在已有事件循环中运行asyncio.run()
nest_asyncio.apply()

app = Flask(__name__, static_folder='static', template_folder='templates')

# 设置全局编码为UTF-8
import sys

import locale
import codecs

# 尝试设置系统默认编码
if hasattr(sys, 'setdefaultencoding'):
    sys.setdefaultencoding('utf-8')

# 设置标准输出编码
if hasattr(sys.stdout, 'encoding') and sys.stdout.encoding != 'utf-8':
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    else:
        sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer)

# 设置标准错误编码
if hasattr(sys.stderr, 'encoding') and sys.stderr.encoding != 'utf-8':
    if hasattr(sys.stderr, 'reconfigure'):
        sys.stderr.reconfigure(encoding='utf-8')
    else:
        sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer)

# 设置Flask JSON配置，确保Unicode字符正确处理
app.json.ensure_ascii = False
app.config['JSON_AS_ASCII'] = False
app.config['JSONIFY_PRETTYPRINT_REGULAR'] = False

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

# 创建OpenAI客户端
try:
    # 尝试从环境变量获取API密钥
    api_key = os.getenv('OPENAI_API_KEY')
    
    # 如果环境变量中没有，使用默认值（此处应替换为您的API密钥）
    if not api_key:
        # 警告: 请勿在生产环境中直接硬编码API密钥
        # 这里仅作为示例，建议使用环境变量或配置文件存储API密钥
        api_key = "您的API密钥"  # 替换为您的真实API密钥
    
    # 创建OpenAI客户端
    import sys
    # 设置默认编码为UTF-8
    if sys.getdefaultencoding() != 'utf-8':
        reload_module = False
        try:
            # Python 2
            import imp
            reload_module = True
            imp.reload(sys)
            sys.setdefaultencoding('utf-8')
        except (ImportError, AttributeError):
            # Python 3
            pass
        
        if reload_module:
            print("已将系统默认编码设置为UTF-8")
    
    openai_client = OpenAI(api_key=api_key)
    print("OpenAI API客户端创建成功")
except Exception as e:
    print(f"创建OpenAI客户端时出错: {str(e)}")
    print("将使用模拟实现")
    openai_client = None

# 使用一个更简单的模拟实现，仅在无法连接真实API时使用
def generate_mock_streaming_response(message, model="gpt-3.5-turbo"):
    """生成一个模拟的流式响应"""
    # 确保消息是UTF-8编码的
    if isinstance(message, bytes):
        message = message.decode('utf-8', errors='replace')
    elif not isinstance(message, str):
        message = str(message)
    
    # 构建回复文本（仅使用ASCII字符，避免编码问题）
    safe_message = ""
    for char in message:
        if ord(char) < 128:  # 仅保留ASCII字符
            safe_message += char
        else:
            safe_message += "?"  # 替换非ASCII字符
    
    response_text = f"You sent: {safe_message}\n\nThis is a simulated response because we cannot connect to the real API.\n\nModel: {model}"
    
    print(f"生成模拟响应: {response_text[:30]}...")
    
    # 返回完整的响应结果
    full_response = response_text
    
    # 逐字符输出
    for char in response_text:
        time.sleep(0.01)  # 添加延迟使其像真实流式API
        try:
            chunk_data = {
                "choices": [
                    {
                        "delta": {
                            "content": char
                        }
                    }
                ]
            }
            # 确保JSON编码正确处理ASCII
            json_str = json.dumps(chunk_data)  # 不需要ensure_ascii=False，因为我们只用ASCII
            yield f"data: {json_str}\n\n"
        except Exception as e:
            print(f"模拟响应JSON编码错误: {str(e)}")
            # 最后的后备选项，直接使用硬编码的安全输出
            yield "data: {\"choices\":[{\"delta\":{\"content\":\"?\"}}]}\n\n"
    
    # 流结束标记
    yield "data: [DONE]\n\n"
    
    return full_response

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
    """处理图片上传并返回分析结果"""
    try:
        # 检查是否有图片文件
        if 'image' not in request.files:
            return jsonify({"success": False, "message": "未找到图片文件"}), 400
        
        image_file = request.files['image']
        conversation_id = request.form.get('conversation_id')
        mode = request.form.get('mode', 'normal')
        
        # 检查文件名是否合法
        if image_file.filename == '':
            return jsonify({"success": False, "message": "未选择图片"}), 400
        
        # 如果没有会话ID，创建一个新的
        if not conversation_id:
            conversation_id = str(uuid.uuid4())
        
        # 记录详细的请求信息
        file_size = 0
        try:
            # 获取文件大小、类型和其他元数据
            file_size = len(image_file.read())
            # 重置文件指针
            image_file.seek(0)
            file_type = image_file.content_type
            print(f"收到图片分析请求: filename={image_file.filename}, size={file_size/1024:.2f}KB, type={file_type}, conversation_id={conversation_id}, mode={mode}")
        except Exception as e:
            print(f"读取图片元数据时出错: {str(e)}")
        
        # 确保上传目录存在
        uploads_dir = 'static/uploads'  # 修改为static下的uploads目录
        os.makedirs(uploads_dir, exist_ok=True)
        
        upload_dir = os.path.join(uploads_dir, conversation_id)
        os.makedirs(upload_dir, exist_ok=True)
        
        # 保存图片文件
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        # 确保文件名是安全的
        safe_filename = secure_filename(image_file.filename)
        # 转换为ASCII安全的文件名，如果包含非ASCII字符
        safe_filename = "".join(c for c in safe_filename if ord(c) < 128)
        if not safe_filename:
            safe_filename = f"image_{timestamp}.jpg"
        
        filename = f"{timestamp}_{safe_filename}"
        file_path = os.path.join(upload_dir, filename)
        try:
            image_file.save(file_path)
            print(f"图片已保存到: {file_path}")
            # 检查文件是否真的已经保存
            if not os.path.exists(file_path):
                raise Exception("文件保存失败，路径不存在")
            if os.path.getsize(file_path) == 0:
                raise Exception("保存的文件大小为0字节")
        except Exception as save_error:
            print(f"保存图片文件时出错: {str(save_error)}")
            return jsonify({"success": False, "message": f"保存图片文件失败: {str(save_error)}"}), 500
        
        # 构建会话文件路径
        conversation_file = os.path.join('conversations', f"{conversation_id}.json")
        
        # 加载现有的会话历史或创建新的
        if os.path.exists(conversation_file):
            with open(conversation_file, 'r', encoding='utf-8') as f:
                try:
                    conversation_data = json.load(f)
                    # 检查返回的数据类型，处理不同格式
                    if isinstance(conversation_data, dict) and 'messages' in conversation_data:
                        messages = conversation_data.get('messages', [])
                    elif isinstance(conversation_data, list):
                        # 如果直接是消息列表
                        messages = conversation_data
                    else:
                        # 其他情况，使用空列表
                        messages = []
                except json.JSONDecodeError:
                    messages = []
        else:
            messages = []
            
        # 添加用户图片消息到历史
        image_url = f"{request.url_root}static/uploads/{conversation_id}/{filename}"
        messages.append({
            "role": "user",
            "content": f"[上传图片]",
            "timestamp": datetime.now().isoformat(),
            "image": image_url
        })
        
        # 分析图片
        if True:  # 总是尝试使用API
            try:
                print("开始分析图片...")
                
                # 读取图片文件并转为base64
                try:
                    from PIL import Image
                    import io
                    import base64
                    
                    def convert_image_to_base64(file_path):
                        """将图片转换为base64编码"""
                        try:
                            # 使用原始格式打开图片
                            with Image.open(file_path) as img:
                                # 获取文件格式
                                img_format = img.format if img.format else 'JPEG'
                                content_type = f"image/{img_format.lower()}"
                                
                                # 保存到内存
                                byte_arr = io.BytesIO()
                                img.save(byte_arr, format=img_format)
                                byte_arr = byte_arr.getvalue()
                                
                                # 转换为base64
                                base64_str = base64.b64encode(byte_arr).decode('utf-8')
                                return base64_str, content_type
                        except Exception as e:
                            print(f"转换图片到base64时出错: {str(e)}")
                            
                            # 备用方法：直接读取二进制数据
                            with open(file_path, "rb") as f:
                                binary_data = f.read()
                                base64_str = base64.b64encode(binary_data).decode('utf-8')
                                # 猜测content_type
                                ext = file_path.split('.')[-1].lower()
                                if ext in ['jpg', 'jpeg']:
                                    content_type = 'image/jpeg'
                                elif ext == 'png':
                                    content_type = 'image/png'
                                elif ext == 'gif':
                                    content_type = 'image/gif'
                                else:
                                    content_type = 'image/jpeg'  # 默认
                                    
                                return base64_str, content_type
                    
                    # 转换图片到base64
                    base64_image, content_type = convert_image_to_base64(file_path)
                    print(f"成功读取图片数据并转换为base64，长度: {len(base64_image)}")
                    
                    # 构建完整的base64 URL
                    data_url = f"data:{content_type};base64,{base64_image}"
                    print(f"创建了base64数据URL，content_type: {content_type}")
                    
                except Exception as read_error:
                    print(f"读取图片文件时出错: {str(read_error)}")
                    raise Exception(f"读取图片文件失败: {str(read_error)}")
                
                # 使用与api1.py相同的API调用方式
                try:
                    # 创建OpenAI客户端
                    from openai import OpenAI
                    
                    print("使用Qwen2-VL模型分析图片")
                    
                    # 使用与api1.py相同的API密钥和基础URL
                    try:
                        api_client = OpenAI(
                            api_key="sk-zkgnhawsdghsmbkeqozsbrguyxblkehoxniouisfusdvgiow",
                            base_url="https://api.siliconflow.cn/v1"
                        )
                        print("成功创建API客户端")
                    except Exception as client_error:
                        print(f"创建API客户端时出错: {str(client_error)}")
                        raise Exception(f"无法创建API客户端: {str(client_error)}")
                    
                    # 准备分析文本
                    analyze_text = "请详细描述并分析这张图片的内容。"
                    
                    # 使用base64方式传输图片
                    print("使用base64编码方式传输图片...")
                    
                    # 发送API请求
                    print("正在发送API请求...")
                    response = api_client.chat.completions.create(
                        model="Qwen/Qwen2-VL-72B-Instruct",
                        messages=[
                            {
                                "role": "user",
                                "content": [
                                    {
                                        "type": "image_url",
                                        "image_url": {
                                            "url": data_url
                                        }
                                    },
                                    {
                                        "type": "text",
                                        "text": analyze_text
                                    }
                                ]
                            }
                        ],
                        stream=False
                    )
                    print("API请求已成功发送")
                    
                    # 获取响应
                    try:
                        # 检查响应格式并相应处理
                        if hasattr(response.choices[0].message, 'content'):
                            # 新的OpenAI客户端格式
                            analysis_result = response.choices[0].message.content
                        elif isinstance(response.choices[0].message, dict):
                            # 字典格式
                            analysis_result = response.choices[0].message.get('content', '')
                        elif isinstance(response.choices[0].message, list):
                            # 列表格式 - 需要合并内容
                            content_parts = []
                            for item in response.choices[0].message:
                                if isinstance(item, dict) and 'text' in item:
                                    content_parts.append(item['text'])
                                elif isinstance(item, dict) and 'content' in item:
                                    content_parts.append(item['content'])
                            analysis_result = ' '.join(content_parts)
                        else:
                            # 其他情况，尝试直接转换为字符串
                            analysis_result = str(response.choices[0].message)
                            
                        print(f"图片分析完成，结果长度: {len(analysis_result)}")
                        print(f"响应类型: {type(response.choices[0].message)}")
                    except Exception as parse_error:
                        print(f"解析API响应时出错: {str(parse_error)}")
                        print(f"响应详情: {response}")
                        raise Exception(f"无法解析API响应: {str(parse_error)}")
                    
                except Exception as api_error:
                    print(f"API调用失败: {str(api_error)}")
                    
                    # 尝试使用备用方法 - 使用示例URL
                    try:
                        print("尝试使用示例图片URL...")
                        backup_image_url = "https://sf-maas-uat-prod.oss-cn-shanghai.aliyuncs.com/dog.png"
                        
                        response = api_client.chat.completions.create(
                            model="Qwen/Qwen2-VL-72B-Instruct",
                            messages=[
                                {
                                    "role": "user",
                                    "content": [
                                        {
                                            "type": "image_url",
                                            "image_url": {
                                                "url": backup_image_url
                                            }
                                        },
                                        {
                                            "type": "text",
                                            "text": "这是一个测试图片分析。请分析这张图片。"
                                        }
                                    ]
                                }
                            ],
                            stream=False
                        )
                        
                        # 处理测试响应
                        if hasattr(response.choices[0].message, 'content'):
                            test_result = response.choices[0].message.content
                        elif isinstance(response.choices[0].message, dict):
                            test_result = response.choices[0].message.get('content', '测试响应')
                        elif isinstance(response.choices[0].message, list):
                            content_parts = []
                            for item in response.choices[0].message:
                                if isinstance(item, dict) and 'text' in item:
                                    content_parts.append(item['text'])
                                elif isinstance(item, dict) and 'content' in item:
                                    content_parts.append(item['content'])
                            test_result = ' '.join(content_parts)
                        else:
                            test_result = str(response.choices[0].message)
                        
                        print("备用方法测试成功，但无法分析用户图片")
                        
                        # 生成一个包含错误信息的分析结果
                        analysis_result = f"""
## 图片分析失败

很抱歉，无法分析您上传的图片，可能是由于以下原因：

1. 图片格式不受支持
2. 图片内容无法识别
3. 服务器连接问题

### 错误详情
```
{str(api_error)}
```

### 建议
请尝试上传其他格式的图片（如JPG、PNG）或稍后再试。
                        """
                    except Exception as backup_error:
                        print(f"备用方法也失败: {str(backup_error)}")
                        raise api_error  # 重新抛出原始错误
            
            except Exception as e:
                print(f"图片分析出错: {str(e)}")
                import traceback
                traceback.print_exc()
                
                # 使用模拟分析作为后备
                analysis_result = f"""
## 图片分析失败

很抱歉，图片分析API调用失败。

### 错误信息
```
{str(e)}
```

### 图片信息
- 文件名: {safe_filename}
- 上传时间: {timestamp}
- 文件大小: {os.path.getsize(file_path) / 1024:.1f} KB

这是一个模拟的分析结果，因为真实API调用失败。正常情况下，这里会显示通过大模型生成的详细图片分析。
                """
        else:
            # 使用纯ASCII模拟分析
            analysis_result = f"""
## 图片分析结果

我看到了一张图片，文件名为 `{safe_filename}`。

这是一个模拟的分析结果，因为我们没有连接到真实的图片分析API。

### 图片信息
- 文件名: {safe_filename}
- 上传时间: {timestamp}
- 大小: {os.path.getsize(file_path) / 1024:.1f} KB

### 分析摘要
这只是一个示例分析，实际系统会提供更详细的结果。
            """
        
        # 添加AI回复到历史
        messages.append({
            "role": "assistant",
            "content": analysis_result,
            "timestamp": datetime.now().isoformat()
        })
        
        # 保存整个对话历史
        conversation_data = {
            "id": conversation_id,
            "title": f"图片分析: {image_file.filename[:20]}...",
            "preview": f"[图片] {image_file.filename}",
            "messages": messages,
            "last_updated": datetime.now().isoformat()
        }
        
        try:
            with open(conversation_file, 'w', encoding='utf-8') as f:
                json.dump(conversation_data, f, ensure_ascii=False, indent=2)
            print(f"已保存对话历史到: {conversation_file}")
        except Exception as save_error:
            print(f"保存对话历史时出错: {str(save_error)}")
        
        # 返回成功响应
        return jsonify({
            "success": True,
            "response": analysis_result,
            "conversation_id": conversation_id,
            "image_url": f"{request.url_root}static/uploads/{conversation_id}/{filename}"  # 返回图片URL给前端
        })
    
    except Exception as e:
        print(f"处理图片请求时出错: {str(e)}")
        import traceback
        traceback_str = traceback.format_exc()
        print(f"错误详细堆栈: {traceback_str}")
        return jsonify({
            "success": False,
            "message": f"处理图片出错: {str(e)}",
            "traceback": traceback_str[:500]  # 返回部分堆栈信息供调试
        }), 500

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

@app.route('/api_chat_stream', methods=['POST'])
def api_chat_stream():
    """处理聊天请求并返回响应（非流式）"""
    try:
        # 获取请求数据
        request_data = request.json
        message = request_data.get('message', '')
        conversation_id = request_data.get('conversation_id')
        mode = request_data.get('mode', 'normal')
        
        print(f"收到聊天请求: message={message}, conversation_id={conversation_id}, mode={mode}")
        
        # 确保会话目录存在
        os.makedirs('conversations', exist_ok=True)
        
        # 如果没有会话ID，创建一个新的
        if not conversation_id:
            conversation_id = str(uuid.uuid4())
        
        # 构建会话文件路径
        conversation_file = os.path.join('conversations', f"{conversation_id}.json")
        
        # 加载现有的会话历史或创建新的
        if os.path.exists(conversation_file):
            with open(conversation_file, 'r', encoding='utf-8') as f:
                try:
                    conversation_data = json.load(f)
                    messages = conversation_data.get('messages', [])
                except json.JSONDecodeError:
                    messages = []
        else:
            messages = []
        
        # 添加用户消息到历史
        messages.append({
            "role": "user",
            "content": message,
            "timestamp": datetime.now().isoformat()
        })
        
        # 使用模拟响应（不调用实际API）
        response_text = f"""
## 回复

您的消息: {message}

这是一个简单的非流式响应。我们不再使用流式输出，而是直接返回完整的消息。
这样可以避免编码问题，并简化客户端处理逻辑。

### 优点

- 更简单的实现
- 避免编码问题
- 减少网络请求

### 时间戳
{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        """
        
        # 添加AI回复到历史
        messages.append({
            "role": "assistant",
            "content": response_text,
            "timestamp": datetime.now().isoformat()
        })
        
        # 保存整个对话历史
        conversation_data = {
            "id": conversation_id,
            "title": message[:30] + ("..." if len(message) > 30 else ""),
            "preview": message[:50] + ("..." if len(message) > 50 else ""),
            "messages": messages,
            "last_updated": datetime.now().isoformat()
        }
        
        with open(conversation_file, 'w', encoding='utf-8') as f:
            json.dump(conversation_data, f, ensure_ascii=False, indent=2)
        
        # 直接返回JSON响应
        return jsonify({
            "success": True,
            "response": response_text,
            "conversation_id": conversation_id
        })
    
    except Exception as e:
        print(f"处理聊天请求时出错: {str(e)}")
        return jsonify({
            "success": False,
            "message": f"处理请求出错: {str(e)}"
        }), 500

@app.route('/api_load_conversation', methods=['GET'])
def api_load_conversation():
    """加载对话历史"""
    try:
        conversation_id = request.args.get('id')
        if not conversation_id:
            return jsonify({"success": False, "message": "未提供对话ID"})
            
        # 读取对话历史文件
        conversations_dir = 'conversations'
        history_file = os.path.join(conversations_dir, f"{conversation_id}.json")
        
        print(f"尝试加载对话历史文件: {history_file}")
        
        if not os.path.exists(history_file):
            print(f"对话历史文件不存在: {history_file}")
            return jsonify({"success": False, "message": "对话历史不存在"})
            
        with open(history_file, 'r', encoding='utf-8') as f:
            conversation_data = json.load(f)
        
        # 根据文件内容格式处理
        if isinstance(conversation_data, dict) and 'messages' in conversation_data:
            # 新格式：包含元数据和消息数组
            messages = conversation_data.get('messages', [])
            title = conversation_data.get('title', '已保存的对话')
            preview = conversation_data.get('preview', '')
            last_updated = conversation_data.get('last_updated', datetime.now().isoformat())
        elif isinstance(conversation_data, list):
            # 旧格式：直接是消息数组
            messages = conversation_data
            
            # 尝试从消息中提取标题和预览
            title = "已保存的对话"
            preview = ""
            
            for msg in messages:
                if msg.get('role') == 'user' and msg.get('content'):
                    content = msg.get('content')
                    if isinstance(content, str) and not content.startswith('[上传图片'):
                        title = content[:15] + ('...' if len(content) > 15 else '')
                        preview = content[:30] + ('...' if len(content) > 30 else '')
                        break
            
            # 创建新格式的数据结构
            conversation_data = {
                "id": conversation_id,
                "title": title,
                "preview": preview,
                "messages": messages,
                "last_updated": datetime.now().isoformat()
            }
            
            # 保存为新格式
            with open(history_file, 'w', encoding='utf-8') as f:
                json.dump(conversation_data, f, ensure_ascii=False, indent=2)
        else:
            # 无效格式
            print(f"无效的对话历史格式: {type(conversation_data)}")
            return jsonify({"success": False, "message": "对话历史格式无效"})
            
        print(f"成功加载对话历史，消息数量: {len(messages)}")
        return jsonify({
            "success": True,
            "id": conversation_id,
            "title": title,
            "preview": preview,
            "messages": messages,
            "last_updated": conversation_data.get("last_updated", datetime.now().isoformat())
        })
            
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        print(f"加载对话错误详情: {error_details}")
        return jsonify({"success": False, "message": f"加载对话出错: {str(e)}"})

@app.route('/api_delete_conversation', methods=['DELETE'])
def api_delete_conversation():
    """删除对话历史"""
    try:
        # 从查询参数或请求体中获取会话ID
        conversation_id = request.args.get('id')
        
        if not conversation_id and request.is_json:
            # 如果不在查询参数中，则从JSON请求体中获取
            data = request.get_json()
            conversation_id = data.get('conversation_id')
            
        if not conversation_id:
            print("删除对话失败：未提供对话ID")
            return jsonify({"success": False, "message": "未提供对话ID"})
        
        print(f"尝试删除对话: {conversation_id}")
            
        # 删除对话历史文件
        conversations_dir = 'conversations'
        history_file = os.path.join(conversations_dir, f"{conversation_id}.json")
        
        if os.path.exists(history_file):
            os.remove(history_file)
            print(f"已删除对话历史文件: {history_file}")
            
            # 删除关联的上传图片目录
            uploads_dir = os.path.join('static', 'uploads', conversation_id)
            if os.path.exists(uploads_dir) and os.path.isdir(uploads_dir):
                import shutil
                try:
                    shutil.rmtree(uploads_dir)
                    print(f"已删除关联的上传目录: {uploads_dir}")
                except Exception as dir_error:
                    print(f"删除关联的上传目录时出错: {str(dir_error)}")
                    
            return jsonify({
                "success": True,
                "message": "对话历史已删除"
            })
        else:
            print(f"对话历史文件不存在: {history_file}")
            return jsonify({
                "success": False, 
                "message": "对话历史文件不存在"
            })
            
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        print(f"删除对话错误详情: {error_details}")
        return jsonify({"success": False, "message": f"删除对话出错: {str(e)}"})

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

# 添加静态资源路由
@app.route('/static/<path:filename>')
def serve_static(filename):
    return send_from_directory('static', filename)

# 添加上传图片访问路由
@app.route('/static/uploads/<path:conversation_id>/<path:filename>')
def serve_uploads(conversation_id, filename):
    return send_from_directory(os.path.join('static/uploads', conversation_id), filename)

# 确保上传和对话目录存在
def ensure_directories():
    """确保所有必要的目录存在"""
    directories = ['static', 'templates', 'static/uploads', 'conversations']
    for directory in directories:
        os.makedirs(directory, exist_ok=True)
        print(f"确保目录存在: {directory}")

# 初始化时创建必要的目录
ensure_directories()
print("已创建必要的目录")

@app.route('/api_get_conversations', methods=['GET'])
def api_get_conversations():
    """获取所有对话列表"""
    try:
        conversations_dir = 'conversations'
        os.makedirs(conversations_dir, exist_ok=True)
        
        # 获取所有json文件
        conversation_files = [f for f in os.listdir(conversations_dir) if f.endswith('.json')]
        
        # 读取每个文件的基本信息
        conversations = []
        for filename in conversation_files:
            try:
                file_path = os.path.join(conversations_dir, filename)
                conversation_id = filename.split('.')[0]
                
                # 获取文件修改时间
                file_time = os.path.getmtime(file_path)
                time_struct = time.localtime(file_time)
                time_str = time.strftime('%Y-%m-%d %H:%M:%S', time_struct)
                
                # 读取文件内容
                with open(file_path, 'r', encoding='utf-8') as f:
                    try:
                        data = json.load(f)
                        
                        # 如果是新格式（带标题和预览）
                        if isinstance(data, dict) and 'title' in data and 'preview' in data:
                            conversations.append({
                                'id': conversation_id,
                                'title': data.get('title', '未命名对话'),
                                'preview': data.get('preview', ''),
                                'time': data.get('last_updated', time_str)
                            })
                        # 如果是旧格式（纯消息列表）
                        else:
                            # 尝试从消息中提取标题和预览
                            title = "对话记录"
                            preview = ""
                            
                            if isinstance(data, list):
                                for msg in data:
                                    if isinstance(msg, dict) and msg.get('role') == 'user' and msg.get('content'):
                                        content = msg.get('content')
                                        if content and isinstance(content, str) and not content.startswith('[上传图片'):
                                            title = content[:20] + ('...' if len(content) > 20 else '')
                                            preview = content[:50] + ('...' if len(content) > 50 else '')
                                            break
                            
                            conversations.append({
                                'id': conversation_id,
                                'title': title,
                                'preview': preview,
                                'time': time_str
                            })
                    except json.JSONDecodeError:
                        # 文件格式不正确，忽略
                        continue
            except Exception as file_error:
                print(f"读取对话 {filename} 出错: {str(file_error)}")
                continue
        
        # 按时间排序（最新的在前）
        conversations.sort(key=lambda x: x.get('time', ''), reverse=True)
        
        return jsonify({
            "success": True,
            "conversations": conversations
        })
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        print(f"获取对话列表错误: {error_details}")
        return jsonify({"success": False, "message": f"获取对话列表出错: {str(e)}"})

if __name__ == '__main__':
    print("\n" + "="*80)
    print("AI助手系统启动")
    print("="*80)
    
    # 检查系统编码
    import sys
    import locale
    print(f"系统默认编码: {sys.getdefaultencoding()}")
    print(f"本地字符集编码: {locale.getpreferredencoding()}")
    
    if not openai_client:
        print("\n注意: 未检测到有效的OpenAI API密钥")
        print("如需使用真实的AI功能，请设置API密钥:")
        print("方法1: 设置环境变量 OPENAI_API_KEY=你的密钥")
        print("方法2: 编辑app.py文件，在'api_key = \"您的API密钥\"'处填入有效的API密钥")
        print("\n当前将使用模拟实现，响应可能不够智能。\n")
    else:
        print("\nOpenAI API连接成功!\n")
    
    print("启动服务器...")
    print("服务已启动，请在浏览器中访问 http://127.0.0.1:8080")
    
    # 设置Flask应用选项
    try:
        app.run(host="0.0.0.0", port=8080, debug=True)
    except Exception as e:
        print(f"启动服务器时出错: {str(e)}")
        import traceback
        traceback.print_exc() 