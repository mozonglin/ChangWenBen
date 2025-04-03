#调用R1用json格式进行回复
import json  
from openai import OpenAI
import os
import random
import time
import threading

client = OpenAI(
    api_key="sk-zkgnhawsdghsmbkeqozsbrguyxblkehoxniouisfusdvgiow", 
    base_url="https://api.siliconflow.cn/v1"
)

# 用于存储待删除的提示词ID及其删除时间
pending_deletions = {}

def generate_prompt_from_user_input(user_input):
    """
    根据用户输入生成完整提示词（包含Role、Context和Exception），但保留用户原始输入作为Action
    
    Args:
        user_input: 用户输入的内容
    
    Returns:
        dict: 包含完整提示词信息的字典
    """
    try:
        print(f"开始处理用户输入: {user_input}")
        
        # 读取现有的prompt.json文件，查看其风格
        with open('prompt.json', 'r', encoding='utf-8') as f:
            existing_prompts = json.load(f)
        
        # 构建DeepSeek模型的提示
        # 选择3个示例作为参考
        example_prompts = existing_prompts[:3]
        examples_json = json.dumps(example_prompts, ensure_ascii=False, indent=2)
        
        # 格式化用户输入的Action，确保包含必要提示
        formatted_action = user_input
        if "（注意：不要只查询前10条，要查询所有的数据）" not in formatted_action:
            formatted_action = f"{formatted_action}（注意：不要只查询前10条，要查询所有的数据）"
        
        prompt_message = f"""
你是一位专业的餐饮分析提示词生成专家。请根据用户提供的Action内容，生成匹配的Role、Context和Exception。

用户提供的Action: "{formatted_action}"

请根据以下现有提示词的格式和风格，为此Action生成匹配的角色和上下文信息:
{examples_json}

注意:
1. 不要修改用户提供的Action，直接使用它
2. Role应该是执行该Action的最合适专业角色
3. Context应该提供必要的背景信息和数据来源
4. Context必须包含"南京煊赫门/扑克牌/大餐盒/一次性筷子/毛巾/清水锅底（小锅）/餐巾纸"不纳入统计"这一提示
5. Exception应该说明特殊情况和额外要求

请以JSON格式回复，只包含以下字段:
{{
  "Role": "适合执行该Action的角色名称",
  "Context": "执行Action时的背景和约束条件",
  "Exception": "需要特别考虑的例外情况或额外要求"
}}
"""

        print("正在调用DeepSeek API...")
        # 调用DeepSeek-R1生成提示词
        response = client.chat.completions.create(
            model="Pro/deepseek-ai/DeepSeek-R1",
            messages=[
                {"role": "system", "content": "You are a helpful assistant designed to output JSON."},
                {"role": "user", "content": prompt_message}
            ],
            
            temperature=0.7,  
            max_tokens=16384,
        )
        
        # 检查响应是否有效
        if not response or not response.choices or not response.choices[0].message.content:
            raise ValueError("API返回的响应为空或格式不正确")
            
        # 获取响应内容
        content = response.choices[0].message.content
        print(f"API响应内容(截取): {content[:200]}...")
        
        # 处理可能的```json前缀和后缀
        if content.startswith('```json'):
            content = content[7:]  # 去掉```json前缀
        if content.endswith('```'):
            content = content[:-3]  # 去掉```后缀
        
        # 清理前后可能的空白字符
        content = content.strip()
        
        # 解析响应内容
        try:
            result = json.loads(content)
        except json.JSONDecodeError as e:
            print(f"JSON解析错误: {str(e)}")
            print(f"尝试解析的内容: {content[:200]}...")
            raise ValueError(f"解析API响应内容失败: {str(e)}")
        
        # 添加用户原始Action
        result["Action"] = formatted_action
        
        # 确保生成的提示词包含所有必要字段
        required_fields = ["Role", "Context", "Exception"]
        missing_fields = [field for field in required_fields if field not in result]
        
        if missing_fields:
            print(f"生成的提示词缺少字段: {missing_fields}")
            # 补充缺失的字段
            for field in missing_fields:
                if field == "Role":
                    result["Role"] = "数据分析师"
                elif field == "Context":
                    result["Context"] = "基于餐厅所有数据进行分析。补充:\"南京煊赫门/扑克牌/大餐盒/一次性筷子/毛巾/清水锅底（小锅）/餐巾纸\"不纳入统计"
                elif field == "Exception":
                    result["Exception"] = "需要提供详细的数据支持和具体的改进建议。"
            
        # 生成新的ID
        max_id = max([p.get("id", 0) for p in existing_prompts])
        result["id"] = max_id + 1
        
        print(f"成功生成提示词: {result['Role']} - {result['Action'][:50]}...")
        return result
    
    except Exception as e:
        print(f"生成提示词失败: {str(e)}")
        # 生成一个基本的提示词作为后备
        formatted_action = user_input
        if "（注意：不要只查询前10条，要查询所有的数据）" not in formatted_action:
            formatted_action = f"{formatted_action}（注意：不要只查询前10条，要查询所有的数据）"
            
        return {
            "id": random.randint(1000, 9999),
            "Role": "数据分析师",
            "Action": formatted_action,
            "Context": "基于餐厅所有数据进行分析。补充:\"南京煊赫门/扑克牌/大餐盒/一次性筷子/毛巾/清水锅底（小锅）/餐巾纸\"不纳入统计",
            "Exception": "需要提供详细的数据支持和具体的改进建议。"
        }

def save_prompt_to_json(prompt_data):
    """
    将生成的提示词保存到prompt.json文件
    
    Args:
        prompt_data: 提示词数据
    
    Returns:
        bool: 是否保存成功
    """
    try:
        print(f"尝试保存提示词: ID={prompt_data.get('id')}, Role={prompt_data.get('Role')}")
        
        # 检查提示词数据是否有效
        if not isinstance(prompt_data, dict) or not prompt_data.get('id'):
            print("提示词数据无效，无法保存")
            return False
        
        # 检查prompt.json文件是否存在
        if not os.path.exists('prompt.json'):
            print("prompt.json文件不存在，创建新文件")
            with open('prompt.json', 'w', encoding='utf-8') as f:
                json.dump([], f, ensure_ascii=False, indent=2)
        
        # 读取现有的prompt.json文件
        with open('prompt.json', 'r', encoding='utf-8') as f:
            existing_prompts = json.load(f)
        
        # 添加新的提示词
        existing_prompts.append(prompt_data)
        
        # 写回文件
        with open('prompt.json', 'w', encoding='utf-8') as f:
            json.dump(existing_prompts, f, ensure_ascii=False, indent=2)
        
        print(f"成功保存提示词: ID={prompt_data.get('id')}")
        
        # 不再添加到待删除列表
        # schedule_prompt_deletion(prompt_data.get('id'), 300)
        
        return True
    
    except Exception as e:
        print(f"保存提示词失败: {str(e)}")
        # 尝试创建备份并重新保存
        try:
            if os.path.exists('prompt.json'):
                # 创建备份
                backup_file = f'prompt_backup_{int(time.time())}.json'
                with open('prompt.json', 'r', encoding='utf-8') as src, open(backup_file, 'w', encoding='utf-8') as dst:
                    dst.write(src.read())
                print(f"已创建备份: {backup_file}")
            
            # 尝试直接写入新文件
            with open('prompt.json', 'w', encoding='utf-8') as f:
                prompts = [prompt_data]
                json.dump(prompts, f, ensure_ascii=False, indent=2)
            print("通过创建新文件方式保存成功")
            
            # 不再添加到待删除列表
            # schedule_prompt_deletion(prompt_data.get('id'), 300)
            
            return True
        except Exception as backup_error:
            print(f"备份和重新保存也失败: {str(backup_error)}")
            return False

def schedule_prompt_deletion(prompt_id, delay_seconds=300):
    """
    安排定时删除提示词
    
    Args:
        prompt_id: 提示词ID
        delay_seconds: 延迟删除的秒数
    """
    if not prompt_id:
        return
    
    print(f"安排删除提示词: ID={prompt_id}, 延迟={delay_seconds}秒")
    
    # 计算删除时间
    delete_time = time.time() + delay_seconds
    
    # 将提示词ID和删除时间添加到待删除列表
    pending_deletions[prompt_id] = delete_time
    
    # 启动定时器线程执行删除
    timer = threading.Timer(delay_seconds, remove_prompt_by_id, args=[prompt_id])
    timer.daemon = True  # 设置为守护线程，避免阻止程序退出
    timer.start()

def remove_prompt_by_id(prompt_id):
    """
    从prompt.json文件中删除指定ID的提示词
    
    Args:
        prompt_id: 要删除的提示词ID
    
    Returns:
        bool: 是否删除成功
    """
    try:
        print(f"尝试删除提示词: ID={prompt_id}")
        
        # 从待删除列表中移除
        if prompt_id in pending_deletions:
            del pending_deletions[prompt_id]
        
        # 检查文件是否存在
        if not os.path.exists('prompt.json'):
            print(f"提示词文件不存在，无法删除ID={prompt_id}的提示词")
            return False
        
        # 读取现有的prompt.json文件
        with open('prompt.json', 'r', encoding='utf-8') as f:
            existing_prompts = json.load(f)
        
        # 过滤掉要删除的提示词
        updated_prompts = [p for p in existing_prompts if p.get("id") != prompt_id]
        
        # 如果长度相同，说明没有找到要删除的ID
        if len(updated_prompts) == len(existing_prompts):
            print(f"未找到ID为{prompt_id}的提示词")
            return False
        
        # 写回文件
        with open('prompt.json', 'w', encoding='utf-8') as f:
            json.dump(updated_prompts, f, ensure_ascii=False, indent=2)
        
        print(f"成功删除ID为{prompt_id}的提示词")
        return True
    
    except Exception as e:
        print(f"删除提示词失败: {str(e)}")
        return False

# 测试代码，直接运行时执行
if __name__ == "__main__":
    # 测试生成提示词
    test_input = "分析最近的销售趋势"
    generated_prompt = generate_prompt_from_user_input(test_input)
    print("生成的提示词:")
    print(json.dumps(generated_prompt, ensure_ascii=False, indent=2))
    
    # 测试保存提示词
    save_result = save_prompt_to_json(generated_prompt)
    print(f"保存结果: {save_result}")
    
    # 等待10秒后检查是否仍在待删除列表中
    print("等待10秒...")
    time.sleep(10)
    print(f"待删除提示词: {pending_deletions}")
    
    # 注意: 完整测试300秒延迟删除需要等待较长时间