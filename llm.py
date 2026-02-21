import httpx
from typing import List, Dict, AsyncGenerator
from config import DEEPSEEK_API_KEY, DEEPSEEK_API_URL

async def stream_llm_response(messages: List[Dict], model: str = "deepseek-chat") -> AsyncGenerator[str, None]:
    if not DEEPSEEK_API_KEY:
        yield "错误：未配置DEEPSEEK_API_KEY，请在.env文件中设置。"
        return
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}"
    }
    
    payload = {
        "model": model,
        "messages": messages,
        "stream": True
    }
    
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            async with client.stream("POST", DEEPSEEK_API_URL, headers=headers, json=payload) as response:
                if response.status_code != 200:
                    error_text = await response.aread()
                    yield f"错误：API请求失败，状态码 {response.status_code}，{error_text.decode()}"
                    return
                
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        data = line[6:]
                        if data == "[DONE]":
                            break
                        try:
                            import json
                            json_data = json.loads(data)
                            if "choices" in json_data and len(json_data["choices"]) > 0:
                                delta = json_data["choices"][0].get("delta", {})
                                content = delta.get("content", "")
                                if content:
                                    yield content
                        except json.JSONDecodeError:
                            continue
    except httpx.TimeoutException:
        yield "错误：请求超时，请稍后重试。"
    except Exception as e:
        yield f"错误：{str(e)}"
