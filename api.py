import json  
from openai import OpenAI

client = OpenAI(
    api_key="sk-zkgnhawsdghsmbkeqozsbrguyxblkehoxniouisfusdvgiow", # 从https://cloud.siliconflow.cn/account/ak获取
    base_url="https://api.siliconflow.cn/v1"
)

response = client.chat.completions.create(
        model="Pro/deepseek-ai/DeepSeek-R1",
        messages=[
            {"role": "system", "content": ""},
            {"role": "user", "content": ""}
        ],
        
    )

print(response.choices[0].message.content)