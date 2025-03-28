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
3. 服务器调用`async_process_user_input(None, prompt_id, f"web_request_{prompt_id}")`函数
   - 参数1: user_data=None（表示使用原始API获取数据）
   - 参数2: prompt_id（用户选择的角色ID）
   - 参数3: file_name（生成的文件名前缀）
4. 系统调用`process_request_with_prompt_id(prompt_id)`获取原始API结果
   - 从`prompt.json`读取对应ID的prompt信息（Action和Context）
   - 构建user_input字符串: `f"Action：{prompt_info['Action']} Context：{prompt_info['Context']}"`
   - 发送请求到原始API并获取结果
5. 系统将API结果保存到文件`原始API结果_ID{prompt_id}_{file_name}.json`
6. 构建数据结构传递给agent_system
   ```python
   data = {
       "api_result": api_result,
       "prompt_info": prompt_info,
       "charts": []
   }
   ```
7. 如果API结果中包含response，将其提取并添加到charts中
8. 调用`analyze_data_with_role_id(data, prompt_id, file_name)`进行深度分析
   - 进行数据整合和分块（按菜品名称整合、将数据分成多个小块）
   - 使用DeepSeek-V2.5模型对每个数据块进行分析
   - 使用DeepSeek-V3-1226模型生成菜品数据总结
   - 使用DeepSeek-R1模型生成宏观总结报告
   - 保存详细分析结果到`detailed_report_json_{prompt_id}.json`
   - 保存最终报告到`report_{prompt_id}_{file_name}.md`
9. 返回分析结果给前端，包括success状态、message消息、data数据和prompt_info信息

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