# 餐饮数据分析专家系统

这是一个基于DeepSeek大语言模型的智能餐饮数据分析系统，支持实时对话、自动生成专业分析提示词，并提供深度分析报告。系统集成了多种模式和功能，旨在帮助餐饮企业进行数据驱动决策。

## 📋 功能特点

### 🔹 专家模式
- **自动提示词生成**：直接输入需求，系统自动生成专业分析提示词
- **实时分析流程**：通过SSE连接展示分析过程的实时日志
- **多级AI分析**：使用DeepSeek系列模型进行多层次数据分析
- **深度报告生成**：输出包含宏观总结和详细分析的Markdown格式报告
- **提示词自动管理**：临时生成的提示词在分析完成后自动删除(300秒)

### 🔹 助理模式
- **智能对话**：支持自然语言交互和历史对话保存
- **图像处理**：支持图片上传和基于图像内容的分析
- **对话流式响应**：实时流式显示AI回复内容

### 🔹 界面设计
- **自适应布局**：消息气泡宽度根据内容长度自动调整
- **代码高亮**：自动识别并高亮显示代码块
- **Markdown渲染**：支持富文本格式的分析报告展示
- **实时状态反馈**：清晰展示处理状态和错误信息

## 🔧 系统架构

```
餐饮数据分析专家系统
├── 前端
│   ├── static/
│   │   ├── expert.js - 专家模式前端逻辑
│   │   ├── expert.css - 专家模式样式
│   │   └── ...
│   └── templates/
│       ├── 专家.html - 专家模式界面
│       ├── 助理.html - 助理模式界面
│       └── ...
├── 后端核心
│   ├── app.py - Flask应用主入口
│   ├── expert_api.py - 专家模式API接口
│   ├── routes.py - 路由配置
│   └── app_config.py - 应用配置
├── 数据处理
│   ├── process_request.py - 请求处理模块
│   ├── agent_system.py - AI分析引擎核心
│   └── api2.py - 提示词生成和管理
└── 数据存储
    ├── prompt.json - 预设分析提示词库
    └── conversations/ - 对话历史存储
```

### 主要模块说明

- **app.py**：Flask应用主入口，集成各个模块和API
- **expert_api.py**：专家模式的API接口，包含数据分析和提示词处理
- **agent_system.py**：AI分析引擎，负责数据处理、模型调用和报告生成
- **api2.py**：提示词生成和管理，包含自动创建和定时删除功能
- **process_request.py**：请求处理模块，负责用户输入处理和API调用

## 🚀 技术实现

### DeepSeek模型集成
- **DeepSeek-R1**：用于生成分析提示词和最终宏观报告
- **DeepSeek-V2.5**：用于分块数据分析
- **DeepSeek-V3-1226**：用于多维数据整合和总结

### 流式处理与实时反馈
- 使用**Server-Sent Events (SSE)**实现分析过程的实时日志展示
- 前端通过**EventSource**接收实时更新并动态渲染

### 异步处理
- 利用**asyncio**处理并发请求和API调用
- 使用**threading**模块创建后台任务，如定时删除提示词

### 提示词自动生成流程
1. 用户输入需求内容
2. 系统通过DeepSeek-R1生成专业的分析提示词
3. 生成的提示词包含Role(角色)、Action(动作)、Context(上下文)和Exception(异常处理)
4. 提示词自动保存并用于数据分析
5. 分析完成300秒后，临时提示词自动删除

### 数据分析引擎流程
1. 数据预处理与整合
2. 按菜品分块并行处理
3. 多级模型分析和结果整合
4. 生成最终Markdown格式报告

## 📦 安装部署

### 环境要求
- Python 3.8+
- Flask 2.0+
- OpenAI API SDK

### 安装步骤

1. 克隆仓库
```bash
git clone <仓库地址>
cd <项目目录>
```

2. 安装依赖
```bash
pip install -r requirements.txt
```

3. 启动应用
```bash
python run.py
```

4. 访问应用
- 专家模式：http://localhost:5000/mobo/专家.html
- 助理模式：http://localhost:5000/mobo/助理.html

## 🖥️ 使用说明

### 专家模式

1. **直接输入分析需求**
   - 在对话框输入您需要分析的内容，如"分析最近三个月热销菜品"
   - 系统会自动将其转换为专业的分析提示词

2. **查看实时分析过程**
   - 系统会展示正在处理的提示词内容
   - 实时显示分析日志，包括API调用、数据处理等步骤

3. **获取分析报告**
   - 分析完成后，系统会生成完整的Markdown格式报告
   - 报告包含宏观总结和详细分析结果

### 助理模式

1. **自然语言对话**
   - 可以用自然语言提问或请求帮助
   - 系统会保存对话历史，方便后续查阅

2. **上传图片分析**
   - 支持上传图片并基于图片内容进行分析
   - 可以与文字描述结合使用

## 🤝 贡献与开发

### 代码结构
项目遵循模块化设计，各功能模块相对独立，便于扩展和维护：
- `app.py`：应用入口和主要API
- `expert_api.py`：专家模式API
- `agent_system.py`：AI分析引擎
- `api2.py`：提示词生成与管理
- `static/`：前端资源
- `templates/`：HTML模板

### 扩展功能
1. 添加新的分析模型：在`agent_system.py`中集成新的模型API调用
2. 扩展提示词功能：修改`api2.py`中的提示词生成逻辑
3. 自定义UI：修改相应的HTML模板和CSS样式

## 📄 许可证
本项目采用 MIT 许可证，详见 LICENSE 文件。

## 🔗 相关链接
- [DeepSeek AI官网](https://www.deepseek.com/)
- [Flask文档](https://flask.palletsprojects.com/)
- [OpenAI API文档](https://platform.openai.com/docs/api-reference)

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

# API空结果重试机制

## 概述

本文档描述当前端调用`process_user_input`函数时，遇到API返回charts为空的情况下，系统的执行流程和重试机制。

## 执行流程

当前端传递ID参数给`process_user_input`函数时，如果API返回的结果中charts数组为空，系统将按照以下流程进行处理：

```
前端 -> process_user_input(prompt_id=xxx) -> process_request_with_prompt_id -> process_request -> API返回空charts -> 重试机制启动
```

具体执行流程：

1. **前端调用**：前端只传递prompt_id参数给`process_user_input`函数
2. **加载Prompt**：系统异步加载对应ID的prompt信息
3. **API调用**：系统使用`process_request_with_prompt_id`函数调用原始API
4. **检测空结果**：
   - 在`process_request`函数中，如果检测到返回结果中charts为空，会自动重试（默认3次）
   - 如果`process_request`重试后仍未获得有效结果，`process_request_with_prompt_id`会再次调用`retry_until_valid_result`函数
5. **深度重试**：`retry_until_valid_result`函数会固定重试4次，尝试获取有效数据
6. **返回结果**：重试成功或失败后，将最终结果返回给前端

## 重试机制详解

系统实现了双层重试机制，确保尽可能获取到有效的API结果：

### 第一层重试（process_request函数）

```python
# 检查返回的结果是否包含空的charts数组
if not data.get('charts') or len(data.get('charts', [])) == 0:
    print(f"API返回结果中charts为空，重试中...")
    attempt += 1
    if attempt < max_retries:
        print(f"等待 {retry_delay} 秒后重试...")
        import time
        time.sleep(retry_delay)
    continue
```

- 当初次调用API返回空charts时，尝试重新发送相同请求
- 默认重试3次，每次重试间隔2秒

### 第二层重试（retry_until_valid_result函数）

```python
# 检查API返回结果，如果charts为空，重试获取有效数据
if result and (not result.get('charts') or len(result.get('charts', [])) == 0):
    result = retry_until_valid_result(result)
```

- 当第一层重试失败后，启动第二层重试
- 使用固定的4次重试次数
- 使用原始会话ID，但发送更简单的请求："请生成一份报表"
- 每次重试间隔2秒

## 使用示例

以下是模拟前端调用的示例代码：

```python
# 创建一个异步函数来调用API
async def call_api(prompt_id):
    result = await process_user_input(
        prompt_id=prompt_id,
        file_name=f"frontend_request_{prompt_id}"
    )
    return result

# 使用事件循环运行异步函数
loop = asyncio.get_event_loop()
try:
    result = loop.run_until_complete(call_api(123))  # 替换为实际的prompt ID
finally:
    # 清理任务
    pending_tasks = asyncio.all_tasks(loop)
    for task in pending_tasks:
        task.cancel()
```

## 测试工具

为了测试这个重试机制，我们提供了几个测试脚本：

1. `frontend_simulation.py` - 模拟前端调用process_user_input的命令行工具
2. `test_api_retry.py` - 批量测试多个ID的工具
3. `test_empty_charts_retry.py` - 专门测试重试功能的工具

使用方法：
```bash
# 模拟前端调用（推荐）
python frontend_simulation.py [prompt_id]

# 批量测试多个ID
python test_api_retry.py [id1] [id2] ...

# 测试重试功能
python test_empty_charts_retry.py 