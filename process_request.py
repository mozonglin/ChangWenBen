import json
import requests
import re
import asyncio
from typing import Dict, Any, Optional, Union

async def load_prompt_by_id(id: int):
    """根据ID从prompt.json文件中加载对应的prompt信息"""
    try:
        with open("prompt.json", "r", encoding="utf-8") as f:
            prompts = json.load(f)
            
        # 查找对应ID的prompt
        for prompt in prompts:
            if prompt.get("id") == id:
                return prompt
                
        return None
    except Exception as e:
        print(f"加载prompt失败: {str(e)}")
        return None

def process_request(user_input, conv_uid=None):
    """
    处理用户输入并返回转换后的数据
    
    Args:
        user_input: 用户输入字符串
        conv_uid: 会话ID，如果为None则使用请求中的会话ID
        
    Returns:
        转换后的JSON数据，Unicode已转为中文
    """
    # 构造请求参数
    payload = {
        "select_param": "财务报表",
        "chat_mode": "chat_dashboard",
        "model_name": "siliconflow_proxyllm",
        "user_input": user_input,
        "conv_uid": conv_uid or "da89c3b4-0bb7-11f0-acf4-bc2411cbc733"  # 使用默认值或传入的值
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

def process_request_with_prompt_id(prompt_id, data=None, conv_uid=None):
    """
    根据prompt ID获取Action和Context，并使用它们处理请求
    
    Args:
        prompt_id: prompt.json中的ID值
        data: 要分析的数据（可选）
        conv_uid: 会话ID（可选）
        
    Returns:
        转换后的JSON数据
    """
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

def save_to_file(data, filename):
    """
    将数据保存到文件
    
    Args:
        data: JSON数据
        filename: 文件名
    """
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

async def process_user_input(user_data=None, prompt_id=None, file_name="user_input_data"):
    """处理用户输入，并使用对应的prompt ID进行分析
    
    参数:
        user_data: 用户输入的数据（可选，如果为None，会先调用原始API生成结果）
        prompt_id: 要使用的prompt ID
        file_name: 用于标识此次分析的文件名
        
    返回:
        包含分析结果的字典
    """
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
            
            data = api_result
            print(f"将API结果传递给agent_system进行深度分析...")
        else:
            # 如果提供了用户数据，直接使用
            try:
                # 如果已经是JSON字符串，直接解析
                data = json.loads(user_data) if isinstance(user_data, str) else user_data
            except json.JSONDecodeError:
                # 如果不是有效的JSON，尝试构建一个简单的数据结构
                data = user_data
        
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

# 用于直接测试此模块
if __name__ == "__main__":
    # 测试根据ID获取prompt并处理请求
    prompt_id = 10  # 例如，使用ID为10的prompt（菜品销售优化顾问）
    
    # 示例1：直接使用ID处理请求
    print(f"使用ID {prompt_id} 的prompt进行处理...")
    result = process_request_with_prompt_id(prompt_id)
    
    if result:
        # 保存到文件
        save_to_file(result, f"分析结果_ID{prompt_id}.json")
        print(f"数据已保存到 分析结果_ID{prompt_id}.json")
        
        # 打印转换后的数据示例
        print("\n处理后的数据示例:")
        print(json.dumps(result, ensure_ascii=False, indent=2)[:500] + "...")
    
    # 示例2：使用ID和示例数据处理请求
    sample_data = {
        "restaurant_name": "测试餐厅",
        "charts": [
            {
                "chart_name": "菜品销售数据",
                "values": [
                    {"name": "红烧肉", "sales": 500, "profit": 5000},
                    {"name": "糖醋排骨", "sales": 420, "profit": 3780}
                ]
            }
        ]
    }
    
    print(f"\n使用ID {prompt_id} 的prompt和示例数据进行处理...")
    result_with_data = process_request_with_prompt_id(prompt_id, sample_data)
    
    if result_with_data:
        # 保存到文件
        save_to_file(result_with_data, f"分析结果_ID{prompt_id}_带数据.json")
        print(f"数据已保存到 分析结果_ID{prompt_id}_带数据.json")
        
    # 示例3：使用process_user_input函数进行测试
    async def test_process_user_input():
        # 测试不提供用户数据，由函数自动调用API
        print("\n测试不提供用户数据，自动调用API并进行深度分析...")
        result = await process_user_input(None, prompt_id, "auto_api_test")
        if result["success"]:
            print(f"自动API处理+深度分析成功:")
            print(f"角色: {result['prompt_info']['Role']}")
            print(f"报告文件: {result['data']['report_file']}")
        else:
            print(f"自动API处理+深度分析失败: {result['message']}")
        
        # 使用ID和示例数据调用process_user_input
        print("\n使用ID和样例数据进行测试...")
        result = await process_user_input(sample_data, prompt_id, "test_process")
        if result["success"]:
            print(f"样例数据分析成功:")
            print(f"角色: {result['prompt_info']['Role']}")
            print(f"报告文件: {result['data']['report_file']}")
        else:
            print(f"样例数据分析失败: {result['message']}")
            
    # 执行示例3
    asyncio.run(test_process_user_input()) 