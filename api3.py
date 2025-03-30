from openai import OpenAI
client = OpenAI(api_key="sk-zkgnhawsdghsmbkeqozsbrguyxblkehoxniouisfusdvgiow", base_url="https://api.siliconflow.cn/v1")
response = client.chat.completions.create(  
    model="Pro/deepseek-ai/DeepSeek-R1",  
    messages=[    
        {"role": "system", "content": "你是数据分析专家，用Markdown输出结果"},  
        {"role": "user", "content": "分析2023年新能源汽车销售数据趋势"}  
    ],  
    temperature=0.7,  
    max_tokens=16384,  
    
)
# 获取响应结果
result = response.choices[0].message.content

# 打印结果
print("分析结果:")
print(result)

