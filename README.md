# 餐饮数据分析系统

这是一个基于Flask的餐饮数据分析系统，使用DeepSeek大语言模型进行数据分析并生成报告。系统提供两种分析模式：原始API分析和DeepSeek大模型深度分析。

## 功能特点

- 基于ID选择不同的分析角色(prompt)
- 支持原始API分析和DeepSeek大模型的深度分析
- 使用DeepSeek大语言模型进行多级分析
- 生成包含宏观总结、菜品总览和详细分析的完整报告
- 简洁的Web界面，支持报告在线查看和下载

## 系统架构

- `app.py`: Flask Web应用，提供用户界面和API
- `process_request.py`: 处理用户输入并调用agent_system
- `agent_system.py`: 数据分析引擎，包含与DeepSeek模型交互的核心逻辑
- `prompt.json`: 不同角色的prompt配置文件

## 安装

1. 克隆仓库

```bash
git clone <仓库地址>
cd <项目目录>
```

2. 安装依赖

```bash
pip install -r requirements.txt
pip install nest-asyncio  # 支持在已有事件循环中嵌套运行新的事件循环
```

## 使用方法

1. 启动Flask应用

```bash
python app.py
```

2. 在浏览器中访问 http://localhost:5000

3. 在Web界面上：
   - 选择分析角色
   - 选择分析模式（DeepSeek分析或API分析）
   - 点击"开始分析"按钮
   - 等待分析完成后查看和下载报告

## 详细运行流程

### 1. DeepSeek分析流程

1. 用户选择prompt_id并点击"开始分析"按钮
2. 前端发送POST请求到`/analyze`端点，传递prompt_id参数
3. Flask调用`app.py`中的`analyze`函数处理请求
   ```python
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
   ```
4. `run_async`函数处理异步操作，执行`async_process_user_input`函数
   ```python
   def run_async(coro):
       loop = asyncio.get_event_loop()
       return loop.run_until_complete(coro)
   ```
5. 调用`process_request.py`中的`process_user_input`函数
   ```python
   async def process_user_input(user_data=None, prompt_id=None, file_name="user_input_data"):
       from agent_system import analyze_data_with_role_id
       
       result = {
           "success": False,
           "message": "",
           "data": None,
           "prompt_info": None
       }
       
       try:
           # 加载prompt信息
           prompt_info = await load_prompt_by_id(prompt_id)
           if not prompt_info:
               result["message"] = f"找不到ID为 {prompt_id} 的prompt"
               return result
               
           result["prompt_info"] = prompt_info
           
           # 如果没有提供用户数据，先调用原始API生成结果
           if user_data is None:
               print(f"没有提供用户数据，使用prompt ID {prompt_id} 调用原始API...")
               api_result = process_request_with_prompt_id(prompt_id)
               
               if not api_result:
                   result["message"] = "原始API调用失败"
                   return result
                   
               # 保存原始API结果到文件
               api_result_file = f"原始API结果_ID{prompt_id}_{file_name}.json"
               save_to_file(api_result, api_result_file)
               print(f"原始API结果已保存到 {api_result_file}")
               
               # 提取API结果作为agent_system的输入数据
               data = {
                   "api_result": api_result,
                   "prompt_info": prompt_info,
                   "charts": []
               }
               
               # 如果API结果中有response，提取出来添加到charts中
               if "response" in api_result:
                   response_text = api_result["response"]
                   data["charts"].append({
                       "chart_name": "API分析结果",
                       "values": [{"name": "分析结果", "content": response_text}]
                   })
           else:
               # 如果提供了用户数据，直接使用
               try:
                   data = json.loads(user_data) if isinstance(user_data, str) else user_data
               except json.JSONDecodeError:
                   data = {
                       "user_input": user_data,
                       "charts": [
                           {
                               "chart_name": "用户数据",
                               "values": [{"name": "用户输入", "content": user_data}]
                           }
                       ]
                   }
           
           # 使用agent_system进行分析
           print(f"使用DeepSeek模型进行深度分析...")
           analysis_result = await analyze_data_with_role_id(data, prompt_id, file_name)
           
           if analysis_result:
               result["success"] = True
               result["message"] = "分析成功"
               result["data"] = analysis_result
               print(f"分析成功，报告已生成: {analysis_result.get('report_file', '')}")
           else:
               result["message"] = "分析失败"
               print("分析失败")
               
           return result
       except Exception as e:
           error_msg = f"处理失败: {str(e)}"
           print(error_msg)
           result["message"] = error_msg
           return result
   ```
6. `process_request_with_prompt_id`函数被调用，使用prompt_id获取Action和Context
   ```python
   def process_request_with_prompt_id(prompt_id, data=None, conv_uid=None):
       # 从prompt.json获取对应ID的prompt信息
       prompt_info = asyncio.run(load_prompt_by_id(prompt_id))
       
       if not prompt_info:
           print(f"找不到ID为 {prompt_id} 的prompt")
           return None
       
       # 构建user_input字符串，使用Action和Context
       user_input = f"Action：{prompt_info['Action']} Context：{prompt_info['Context']}"
       
       # 如果有数据要分析，添加到user_input
       if data:
           if isinstance(data, str):
               user_input += f" 数据：{data}"
           elif isinstance(data, dict):
               user_input += f" 数据：{json.dumps(data, ensure_ascii=False)}"
       
       # 调用原始处理函数
       return process_request(user_input, conv_uid)
   ```
7. `process_request`函数发送HTTP请求到原始API
   ```python
   def process_request(user_input, conv_uid=None):
       # 构造请求参数
       payload = {
           "select_param": "财务报表",
           "chat_mode": "chat_dashboard",
           "model_name": "siliconflow_proxyllm",
           "user_input": user_input,
           "conv_uid": conv_uid or "da89c3b4-0bb7-11f0-acf4-bc2411cbc733"
       }
       
       # 发送请求
       headers = {
           "Content-Type": "application/json",
           "Accept": "text/event-stream"
       }
       
       try:
           response = requests.post(
               "http://149.104.26.64:5670/api/v1/chat/completions",
               json=payload,
               headers=headers,
               stream=True
           )
           
           # 从响应中提取数据部分
           for line in response.iter_lines():
               if line:
                   line = line.decode('utf-8')
                   if line.startswith('data: '):
                       json_data = line[6:]  # 去掉 'data: ' 前缀
                       break
           
           # 解析JSON数据
           data = json.loads(json_data)
           
           return data
       
       except Exception as e:
           print(f"请求处理出错: {e}")
           return None
   ```
8. 获取原始API结果后，调用`agent_system.py`中的`analyze_data_with_role_id`函数进行深度分析
   ```python
   async def analyze_data_with_role_id(data, role_id, file_name=None):
       try:
           # 记录开始分析
           await log_debug(f"开始使用角色ID {role_id} 分析数据", role_id)
           
           # 按菜品名称整合数据
           organized_data = organize_data_by_dish(data)
           
           # 分块处理数据
           data_chunks = chunk_data(organized_data)
           await log_debug(f"数据已分为 {len(data_chunks)} 个块进行处理", role_id)
           
           # 获取prompt模板
           prompt_template = await load_prompt_by_id(role_id)
           if not prompt_template:
               await log_debug(f"找不到ID为 {role_id} 的角色", role_id)
               return None
           
           # 初始化状态
           state = initialize_state(data, prompt_template)
           
           # 第一阶段：菜品数据分析（DeepSeek-V2.5）
           # 产生多个菜品的详细分析结果
           detailed_analysis = await perform_detailed_analysis(data_chunks, prompt_template, role_id)
           
           # 保存详细分析结果
           detailed_report_file = f"detailed_report_json_{role_id}.json"
           await save_json_file(detailed_analysis, detailed_report_file)
           await log_debug(f"详细分析结果已保存到 {detailed_report_file}", role_id)
           
           # 第二阶段：生成菜品数据总结（DeepSeek-V3-1226）
           # 根据详细分析生成概览
           overview = await generate_data_overview(detailed_analysis, prompt_template, role_id)
           await log_debug("菜品数据总结已生成", role_id)
           
           # 第三阶段：生成宏观总结报告（DeepSeek-R1）
           # 生成最终报告
           report = await generate_final_report(overview, detailed_analysis, prompt_template, role_id)
           
           # 保存为Markdown文件
           report_file = file_name or f"report_{role_id}.md"
           await save_markdown_report(report, report_file)
           await log_debug(f"最终报告已保存到 {report_file}", role_id)
           
           # 构建返回结果
           return {
               "success": True,
               "report": report,
               "report_file": report_file,
               "detailed_analysis": detailed_analysis,
               "overview": overview
           }
       
       except Exception as e:
           import traceback
           error_details = traceback.format_exc()
           await log_debug(f"分析出错: {str(e)}\n{error_details}", role_id)
           return None
   ```
9. 分析完成后，结果被返回给前端，包括：
   - `success`: 分析是否成功
   - `message`: 消息说明
   - `data`: 分析结果数据，包含report（报告内容）、report_file（报告文件路径）等
   - `prompt_info`: 使用的prompt信息

### 2. API分析流程

1. 用户选择prompt_id并点击"开始API分析"按钮
2. 前端发送POST请求到`/api_analyze/<prompt_id>`端点
3. 服务器调用`process_request_with_prompt_id(prompt_id)`获取原始API结果
4. 系统将API结果保存到文件`分析结果_ID{prompt_id}_api.json`
5. 构建数据结构传递给agent_system
   ```python
   data = {
       "api_result": api_result,
       "prompt_info": run_async(async_load_prompt_by_id(prompt_id)),
       "charts": []
   }
   ```
6. 如果API结果中包含response，将其提取并添加到charts中
7. 调用`analyze_data_with_role_id(data, prompt_id, file_name)`进行深度分析
   - 使用与DeepSeek分析相同的流程进行深度分析
8. 返回完整的分析结果给前端，包括：
   - 原始API结果 (api_result)
   - agent_system分析结果 (agent_result)
   - 报告文件路径 (report_file)
   - API结果文件路径 (api_file)

## 数据格式

系统接受的数据格式如下：

```json
{
    "restaurant_name": "餐厅名称",
    "date_range": "数据时间范围",
    "charts": [
        {
            "chart_name": "图表名称",
            "values": [
                {"name": "菜品1", "sales": 500, "profit": 5000},
                {"name": "菜品2", "sales": 420, "profit": 3780}
            ]
        }
    ]
}
```

## API接口

系统提供以下API接口：

- `GET /`: 主页，显示Web界面
- `GET /get_prompt_info/<prompt_id>`: 获取指定ID的prompt信息
- `POST /analyze`: 提交数据进行DeepSeek分析
- `POST /api_analyze/<prompt_id>`: 使用原始API进行分析
- `GET /reports/<filename>`: 下载指定的报告文件

## 核心函数参数说明

### process_user_input
```python
async def process_user_input(user_data=None, prompt_id=None, file_name="user_input_data"):
    """
    参数:
        user_data: 用户输入的数据（可选，如果为None，会先调用原始API生成结果）
        prompt_id: 要使用的prompt ID
        file_name: 用于标识此次分析的文件名
    
    返回:
        包含分析结果的字典
    """
```

### analyze_data_with_role_id
```python
async def analyze_data_with_role_id(data, role_id, file_name=None):
    """
    参数:
        data: 要分析的数据字典
        role_id: 角色ID（用于加载prompt）
        file_name: 报告文件名（可选）
    
    返回:
        包含分析结果的字典
    """
```

### get_llm_response
```python
async def get_llm_response(messages, model_name="Pro/deepseek-ai/DeepSeek-R1", json_format=False, role_id="system"):
    """
    参数:
        messages: 会话消息列表
        model_name: 使用的模型名称
        json_format: 是否要求返回JSON格式
        role_id: 角色ID（用于日志）
    
    返回:
        模型响应的文本内容
    """
``` 