import json
import asyncio
from agent_system import analyze_with_role_id, analyze_data_with_role_id

# 示例1：使用特定角色ID分析指定文件
async def analyze_file_example():
    file_path = "高利润与低利润菜品.json"  # 要分析的数据文件路径
    role_id = 10  # 要使用的prompt ID (菜品销售优化顾问)
    
    print(f"使用角色ID {role_id} 分析文件 {file_path}...")
    success = await analyze_with_role_id(file_path, role_id)
    
    if success:
        print(f"分析完成！请查看 report_{role_id}.md 文件获取分析报告")
    else:
        print("分析失败，请检查错误信息")

# 示例2：直接传入数据进行分析
async def analyze_direct_data_example():
    # 示例数据 - 可以是字典或JSON字符串
    sample_data = {
        "restaurant_name": "示例餐厅",
        "date_range": "2023-01-01 至 2023-03-31",
        "charts": [
            {
                "chart_name": "菜品销售数据",
                "values": [
                    {"name": "红烧肉", "sales": 500, "profit": 5000},
                    {"name": "糖醋排骨", "sales": 420, "profit": 3780},
                    {"name": "宫保鸡丁", "sales": 650, "profit": 4550},
                    {"name": "水煮鱼片", "sales": 380, "profit": 4180}
                ]
            }
        ]
    }
    
    # 设置角色ID和文件标识名
    role_id = 10  # 菜品销售优化顾问
    file_name = "api_test_data"
    
    print(f"使用角色ID {role_id} 分析直接传入的数据...")
    result = await analyze_data_with_role_id(sample_data, role_id, file_name)
    
    if result:
        print(f"分析完成！请查看 {result['report_file']} 文件获取分析报告")
        # 可以直接使用result中的分析结果
        print("\n宏观总结摘要:")
        print(result['macro_report'][:150] + "...")  # 打印宏观总结的前150个字符
    else:
        print("分析失败，请检查错误信息")

# 选择运行哪个示例
async def main():
    # 示例1: 分析文件
    await analyze_file_example()
    
    # 示例2: 分析直接传入的数据
    await analyze_direct_data_example()

if __name__ == "__main__":
    asyncio.run(main())