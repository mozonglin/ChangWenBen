#点击上传图片

import json  
from openai import OpenAI

client = OpenAI(
    api_key="sk-zkgnhawsdghsmbkeqozsbrguyxblkehoxniouisfusdvgiow", # 从https://cloud.siliconflow.cn/account/ak获取
    base_url="https://api.siliconflow.cn/v1"
)

response = client.chat.completions.create(
        model="Qwen/Qwen2-VL-72B-Instruct",
        messages=[
        {
            "role": "user",
            "content": [
                {
                    "type": "image_url",
                    "image_url": {
                        "url": "https://sf-maas-uat-prod.oss-cn-shanghai.aliyuncs.com/dog.png"
                    }
                },
                {
                    "type": "text",
                    "text": "Describe the image."
                }
            ]
        }],
        stream=True
)

for chunk in response:
    chunk_message = chunk.choices[0].delta.content
    print(chunk_message, end='', flush=True)

#点击深度思考
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
    stream=True
)

for chunk in response:
    chunk_message = chunk.choices[0].delta.content
    if chunk_message!=None:
        print(chunk_message, end='', flush=True)


#未点击深度思考
from openai import OpenAI
client = OpenAI(api_key="sk-zkgnhawsdghsmbkeqozsbrguyxblkehoxniouisfusdvgiow", base_url="https://api.siliconflow.cn/v1")
response = client.chat.completions.create(  
    model="Pro/deepseek-ai/DeepSeek-V3",  
    messages=[    
        {"role": "system", "content": "你是数据分析专家，用Markdown输出结果"},  
        {"role": "user", "content": "分析2023年新能源汽车销售数据趋势"}  
    ],  
    temperature=0.7,  
    max_tokens=16384,  
    stream=True
)

for chunk in response:
    chunk_message = chunk.choices[0].delta.content
    if chunk_message!=None:
        print(chunk_message, end='', flush=True)

#base64形式
{
    "role": "user",
    "content":[
        {
            "type": "image_url",
            "image_url": {
                "url": f"data:image/jpeg;base64,{base64_image}",
                "detail":"low"
            }
        },
        {
            "type": "text",
            "text": "text-prompt here"
        }
    ]
}
#图片base64转换示例
from PIL import Image
import io
import base64
def convert_image_to_webp_base64(input_image_path):
    try:
        with Image.open(input_image_path) as img:
            byte_arr = io.BytesIO()
            img.save(byte_arr, format='webp')
            byte_arr = byte_arr.getvalue()
            base64_str = base64.b64encode(byte_arr).decode('utf-8')
            return base64_str
    except IOError:
        print(f"Error: Unable to open or convert the image {input_image_path}")
        return None

base64_image=convert_image_to_webp_base64(input_image_path)

    