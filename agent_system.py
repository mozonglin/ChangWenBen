import json
import asyncio
from typing import Dict, List, TypedDict
from openai import AsyncOpenAI
import aiofiles
import time

# 配置OpenAI客户端
client = AsyncOpenAI(
    api_key="sk-zkgnhawsdghsmbkeqozsbrguyxblkehoxniouisfusdvgiow",
    base_url="https://api.siliconflow.cn/v1"
)

# 定义状态类型
class AgentState(TypedDict):
    messages: List[Dict]
    next_step: str
    current_data: Dict
    analysis_results: List[Dict]
    prompt_template: Dict
    remaining_items: List[str]

# 工具函数
async def load_json_file(file_path: str) -> Dict:
    """异步加载JSON文件"""
    async with aiofiles.open(file_path, 'r', encoding='utf-8') as f:
        content = await f.read()
        return json.loads(content)

def organize_data_by_dish(data: Dict) -> Dict:
    """将数据按菜品名称整合"""
    if "charts" not in data:
        return data
    
    dish_data = {}
    original_data_structure = {key: value for key, value in data.items() if key != "charts"}
    
    # 遍历所有图表
    for chart in data["charts"]:
        if "values" not in chart:
            continue
        
        # 提取每个value中的名称和数据
        for value in chart["values"]:
            if "name" not in value:
                continue
                
            dish_name = value["name"]
            
            # 如果这个菜品尚未在dish_data中，创建它
            if dish_name not in dish_data:
                dish_data[dish_name] = {
                    **original_data_structure,
                    "dish_name": dish_name,
                    "charts": []
                }
                
            # 找到这个菜品对应的chart是否已经存在
            chart_exists = False
            for existing_chart in dish_data[dish_name]["charts"]:
                if existing_chart["chart_name"] == chart["chart_name"]:
                    # 如果已存在，添加数据点
                    if "values" not in existing_chart:
                        existing_chart["values"] = []
                    existing_chart["values"].append(value)
                    chart_exists = True
                    break
                    
            # 如果不存在，创建新的chart
            if not chart_exists:
                new_chart = {key: val for key, val in chart.items() if key != "values"}
                new_chart["values"] = [value]
                dish_data[dish_name]["charts"].append(new_chart)
    
    # 转换为列表
    return {
        **original_data_structure,
        "organized_by_dish": True,
        "dishes": list(dish_data.values())
    }

def chunk_data(data: Dict, chunk_size: int = 5) -> List[Dict]:
    """将数据分块"""
    # 检查数据是否已经按菜品整合
    if "organized_by_dish" in data and data["organized_by_dish"] and "dishes" in data:
        dishes = data["dishes"]
        chunks = []
        
        # 每个块包含chunk_size个菜品
        for i in range(0, len(dishes), chunk_size):
            chunk = {
                key: value for key, value in data.items() 
                if key not in ["dishes", "organized_by_dish", "charts"]
            }
            chunk["dishes"] = dishes[i:i+chunk_size]
            chunks.append(chunk)
        
        return chunks
    
    # 原来的分块逻辑，用于未整合的数据
    if "charts" not in data:
        return [data]
    
    charts = data["charts"]
    chunks = []
    
    # 如果charts中的每个元素有values字段，按values进行分块
    for chart in charts:
        if "values" in chart:
            values = chart["values"]
            for i in range(0, len(values), chunk_size):
                chart_chunk = {
                    **chart,
                    "values": values[i:i+chunk_size]
                }
                
                # 创建一个完整的数据副本，但只包含当前chart的一个数据块
                chunk = {
                    **data,
                    "charts": [chart_chunk]
                }
                chunks.append(chunk)
        else:
            # 如果chart没有values字段，直接作为一个块
            chunk = {
                **data,
                "charts": [chart]
            }
            chunks.append(chunk)
    
    return chunks

async def get_llm_response(messages: List[Dict], model_name: str = "Pro/deepseek-ai/DeepSeek-R1", json_format: bool = False) -> str:
    """异步获取大模型响应"""
    try:
        if json_format:
            response = await client.chat.completions.create(
                model=model_name,
                messages=messages,
                response_format={"type": "json_object"}
            )
        else:
            response = await client.chat.completions.create(
                model=model_name,
                messages=messages
            )
        return response.choices[0].message.content
    except Exception as e:
        print(f"API调用出错: {str(e)}")
        # 等待一会再重试
        await asyncio.sleep(3)
        try:
            if json_format:
                response = await client.chat.completions.create(
                    model=model_name,
                    messages=messages,
                    response_format={"type": "json_object"}
                )
            else:
                response = await client.chat.completions.create(
                    model=model_name,
                    messages=messages
                )
            return response.choices[0].message.content
        except Exception as e:
            print(f"第二次API调用出错: {str(e)}")
            return f"分析失败: {str(e)}"

def json_to_markdown(json_str: str) -> str:
    """将JSON格式的分析结果转换为Markdown格式，生成美观的输出"""
    try:
        data = json.loads(json_str)
        md_content = []
        
        # 处理可能存在的各种JSON结构
        if isinstance(data, dict):
            # 处理分析标题
            if "分析标题" in data:
                md_content.append(f"## {data['分析标题']}")
                md_content.append("")
            
            # 处理菜品分析（表格形式）
            if "菜品分析" in data and isinstance(data["菜品分析"], list) and len(data["菜品分析"]) > 0:
                md_content.append("### 🍽️ 菜品详细分析")
                md_content.append("")
                
                # 创建表格
                if all(isinstance(item, dict) for item in data["菜品分析"]):
                    # 提取所有可能的表头
                    headers = set()
                    for item in data["菜品分析"]:
                        headers.update(item.keys())
                    
                    headers = ["菜品名称"] + [h for h in headers if h != "菜品名称"]
                    
                    # 表格头
                    md_content.append("| " + " | ".join(headers) + " |")
                    md_content.append("| " + " | ".join(["---" for _ in headers]) + " |")
                    
                    # 表格内容
                    for item in data["菜品分析"]:
                        row = []
                        for header in headers:
                            if header in item:
                                cell_content = str(item[header]).replace("\n", "<br>")
                                row.append(cell_content)
                            else:
                                row.append("-")
                        md_content.append("| " + " | ".join(row) + " |")
                    
                    md_content.append("")
                else:
                    # 非字典结构，使用列表
                    for item in data["菜品分析"]:
                        md_content.append(f"- {item}")
                    md_content.append("")
            
            # 处理整体发现（引用块）
            if "整体发现" in data:
                md_content.append("### 🔍 整体发现")
                md_content.append("")
                md_content.append("> " + str(data["整体发现"]).replace("\n", "\n> "))
                md_content.append("")
            
            # 处理建议（序号列表）
            if "建议" in data:
                md_content.append("### 💡 优化建议")
                md_content.append("")
                
                if isinstance(data["建议"], list):
                    for i, item in enumerate(data["建议"], 1):
                        md_content.append(f"{i}. {item}")
                else:
                    suggestions = str(data["建议"]).split("。")
                    for i, suggestion in enumerate([s for s in suggestions if s.strip()], 1):
                        md_content.append(f"{i}. {suggestion}。")
                
                md_content.append("")
            
            # 处理其他字段
            for key, value in data.items():
                if key not in ["分析标题", "菜品分析", "整体发现", "建议"]:
                    md_content.append(f"### {key}")
                    
                    if isinstance(value, dict):
                        for sub_key, sub_value in value.items():
                            md_content.append(f"#### {sub_key}")
                            if isinstance(sub_value, list):
                                for item in sub_value:
                                    if isinstance(item, dict):
                                        md_content.append("- " + " | ".join(f"{k}: {v}" for k, v in item.items()))
                                    else:
                                        md_content.append(f"- {item}")
                            else:
                                md_content.append(f"{sub_value}")
                            md_content.append("")
                    elif isinstance(value, list):
                        for item in value:
                            if isinstance(item, dict):
                                md_content.append("- " + " | ".join(f"{k}: {v}" for k, v in item.items()))
                            else:
                                md_content.append(f"- {item}")
                    else:
                        md_content.append(f"{value}")
                    md_content.append("")
        
        return "\n".join(md_content)
    except Exception as e:
        print(f"JSON转Markdown出错: {str(e)}")
        return f"格式转换失败: {json_str}"

async def analyze_chunk(chunk: Dict, prompt: Dict) -> Dict:
    """分析单个数据块"""
    # 检查是否是按菜品组织的数据
    if "dishes" in chunk:
        messages = [
            {"role": "system", "content": "你是一个专业的数据分析师，负责分析餐饮行业的各项数据。请根据提供的数据进行深入分析，并给出详细的分析报告。"},
            {"role": "system", "content": f"""
你现在扮演{prompt['Role']}的角色。
你的任务是：{prompt['Action']}
需要考虑的上下文：{prompt['Context']}
特殊要求：{prompt['Exception']}

请对接下来提供的数据进行深入分析。这些数据已经按菜品名称整合，每个菜品包含多个维度的指标数据。
请对每个菜品进行全面分析，确保分析到位。每个菜品都需要详细的分析和建议。

请以JSON格式返回分析结果，格式如下：
{{
  "分析标题": "对当前菜品数据块的简要描述",
  "菜品分析": [
    {{
      "菜品名称": "菜品1",
      "数据指标汇总": "该菜品的所有数据指标概述",
      "分析结论": "对该菜品的综合分析",
      "优化建议": "针对该菜品的具体建议"
    }},
    // 更多菜品...
  ],
  "整体发现": "对当前数据块的整体分析发现",
  "建议": "基于当前数据块的建议"
}}
"""},
            {"role": "user", "content": f"请分析以下按菜品整合的数据：\n{json.dumps(chunk, ensure_ascii=False)}"}
        ]
    else:
        # 原来的分析逻辑
        messages = [
            {"role": "system", "content": "你是一个专业的数据分析师，负责分析餐饮行业的各项数据。请根据提供的数据进行深入分析，并给出详细的分析报告。"},
            {"role": "system", "content": f"""
你现在扮演{prompt['Role']}的角色。
你的任务是：{prompt['Action']}
需要考虑的上下文：{prompt['Context']}
特殊要求：{prompt['Exception']}

请对接下来提供的数据进行深入分析，专注于当前这一部分数据的分析，不需要全局总结。每个菜品都要详细分析到位。
请以JSON格式返回分析结果，格式如下：
{{
  "分析标题": "对当前数据块的简要描述",
  "菜品分析": [
    {{
      "菜品名称": "菜品1",
      "关键指标": "相关指标数据",
      "分析结论": "对该菜品的详细分析",
      "优化建议": "针对该菜品的具体建议"
    }},
    // 更多菜品...
  ],
  "整体发现": "对当前数据块的整体分析发现",
  "建议": "基于当前数据块的建议"
}}
"""},
            {"role": "user", "content": f"请分析以下数据：\n{json.dumps(chunk, ensure_ascii=False)}"}
        ]
    
    # 使用 DeepSeek-V2.5 模型进行数据块分析，返回JSON格式
    analysis = await get_llm_response(messages, model_name="deepseek-ai/DeepSeek-V2.5", json_format=True)
    return {
        "data": chunk,
        "analysis": analysis
    }

async def summarize_chunk_results(chunk_results: List[Dict], prompt: Dict) -> str:
    """使用V3模型对所有数据块的菜品进行总结"""
    # 提取所有菜品信息
    all_dish_info = []
    for result in chunk_results:
        try:
            analysis = json.loads(result["analysis"])
            if "菜品分析" in analysis and isinstance(analysis["菜品分析"], list):
                for dish in analysis["菜品分析"]:
                    if isinstance(dish, dict) and "菜品名称" in dish:
                        all_dish_info.append(dish)
        except Exception as e:
            print(f"处理菜品信息时出错: {str(e)}")
    
    # 为V3模型准备总结请求
    summary_messages = [
        {"role": "system", "content": "你是一个专业的数据分析师，负责分析餐饮行业的各项数据。请根据提供的数据进行深入分析，并给出详细的分析报告。"},
        {"role": "system", "content": f"""
你现在扮演{prompt['Role']}的角色。
你的任务是：{prompt['Action']}
需要考虑的上下文：{prompt['Context']}
特殊要求：{prompt['Exception']}

请对以下菜品数据进行总结归纳，提供一个简洁的标题和对关键菜品及指标的概述。
"""},
        {"role": "user", "content": f"请对以下菜品数据进行总结归纳：\n{json.dumps(all_dish_info, ensure_ascii=False)}"}
    ]
    
    # 使用DeepSeek-V3-1226模型生成总结
    summary = await get_llm_response(summary_messages, model_name="Pro/deepseek-ai/DeepSeek-V3-1226")
    return summary

async def process_file(file_path: str, prompt_data: List[Dict]):
    """处理单个文件"""
    print(f"开始处理文件: {file_path}")
    start_time = time.time()
    
    try:
        # 加载数据
        data = await load_json_file(file_path)
        role_id = data.get("id")
        
        # 获取对应的prompt
        prompt = next((p for p in prompt_data if p["id"] == role_id), None)
        if not prompt:
            print(f"未找到ID {role_id} 对应的prompt")
            return
        
        # 按菜品整合数据
        print(f"正在整合 {file_path} 中的菜品数据")
        organized_data = organize_data_by_dish(data)
        
        # 将整合后的数据分块
        chunks = chunk_data(organized_data)
        print(f"文件 {file_path} 已按菜品整合并分为 {len(chunks)} 个数据块")
        
        # 并行分析所有数据块（使用 DeepSeek-V2.5 模型）
        tasks = [analyze_chunk(chunk, prompt) for chunk in chunks]
        chunk_results = await asyncio.gather(*tasks)
        print(f"文件 {file_path} 的 {len(chunks)} 个数据块分析完成")
        
        # 使用V3模型对所有数据块进行总结
        print(f"使用DeepSeek-V3-1226模型对菜品数据进行总结")
        chunk_summary = await summarize_chunk_results(chunk_results, prompt)
        
        # 保存每个分块的JSON分析结果和V3总结
        detailed_reports = []
        json_reports = []
        
        for i, result in enumerate(chunk_results):
            json_reports.append(result["analysis"])
            # 将JSON转换为Markdown格式
            md_content = json_to_markdown(result["analysis"])
            detailed_reports.append(f"{md_content}\n\n")
        
        # 将所有分块详细分析结果保存到一个文件（原始JSON格式）
        async with aiofiles.open(f"detailed_report_json_{role_id}.json", "w", encoding="utf-8") as f:
            await f.write(json.dumps(json_reports, ensure_ascii=False, indent=2))
        
        # 为R1模型准备宏观摘要请求
        r1_summary_messages = [
            {"role": "system", "content": "你是一个专业的数据分析师，负责分析餐饮行业的各项数据。请根据提供的数据进行深入分析，并给出详细的分析报告。"},
            {"role": "system", "content": f"""
你现在扮演{prompt['Role']}的角色。
你的任务是：{prompt['Action']}
需要考虑的上下文：{prompt['Context']}
特殊要求：{prompt['Exception']}

我们已经对每个菜品的数据块进行了详细分析，并生成了总结。现在需要你提供一份宏观的总结报告，关注整体趋势、关键发现和战略性建议。
不需要再对每个具体菜品进行详细分析，请专注于宏观层面的结论和建议。
"""}
        ]
        
        # 为R1提供V3的总结结果而不是原始数据
        r1_summary_messages.append({
            "role": "user", 
            "content": f"""
我们已经分析了{len(chunks)}个数据块，V3模型对菜品数据的总结如下：

{chunk_summary}

基于这些信息和以下背景：
1. 数据文件: {file_path}
2. 分析角色: {prompt['Role']}
3. 主要任务: {prompt['Action']}

请提供一份宏观层面的总结报告，包含整体趋势分析、关键发现和战略性建议。请专注于宏观层面的结论和建议。
"""
        })
        
        print(f"开始为文件 {file_path} 生成宏观总结报告（使用DeepSeek-R1模型）")
        # 使用 DeepSeek-R1 模型生成宏观总结报告
        macro_report = await get_llm_response(r1_summary_messages, model_name="Pro/deepseek-ai/DeepSeek-R1")
        
        # 合并V3总结、详细分析和宏观总结到一个Markdown文件
        final_report = f"""# {prompt['Role']}分析报告

## 🌟 宏观总结

{macro_report}

## 📊 菜品总览

{chunk_summary}

## 📝 详细分析

{"".join(detailed_reports)}

---
*报告生成时间：{time.strftime("%Y-%m-%d %H:%M:%S")}*
"""
        
        # 保存最终Markdown报告
        async with aiofiles.open(f"report_{role_id}.md", "w", encoding="utf-8") as f:
            await f.write(final_report)
        
        end_time = time.time()
        print(f"完成文件 {file_path} 的分析，用时 {end_time - start_time:.2f} 秒")
        
    except Exception as e:
        print(f"处理文件 {file_path} 时出错: {str(e)}")

async def main():
    """主函数"""
    # 数据文件列表
    data_files = [
        "仓库采购和滞留数据.json",
        "高利润与低利润菜品.json",
        "推广策略.json",
        "指标波动.json"
    ]
    
    try:
        # 加载prompt模板
        prompt_data = await load_json_file("prompt.json")
        
        # 串行处理每个文件，但文件内部并行处理数据块
        for file_path in data_files:
            await process_file(file_path, prompt_data)
            
    except Exception as e:
        print(f"程序执行失败: {str(e)}")

if __name__ == "__main__":
    asyncio.run(main()) 