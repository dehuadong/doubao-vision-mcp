#!/usr/bin/env python3
import asyncio
import os
import base64
from pathlib import Path
from typing import Any

import httpx
from mcp.server import Server, NotificationOptions
from mcp.server.models import InitializationOptions
import mcp.server.stdio
import mcp.types as types

DOUBAO_API_KEY = os.environ.get("DOUBAO_API_KEY")
DOUBAO_ENDPOINT = os.environ.get(
    "DOUBAO_ENDPOINT",
    "https://ark.cn-beijing.volces.com/api/v3/chat/completions"
)
DOUBAO_MODEL = os.environ.get("DOUBAO_MODEL", "doubao-seed-2.0-pro")

if not DOUBAO_API_KEY:
    raise RuntimeError("请设置环境变量 DOUBAO_API_KEY")

MAX_IMAGE_SIZE = 20 * 1024 * 1024  # 20MB

app = Server("doubao-vision-server")

@app.list_tools()
async def list_tools() -> list[types.Tool]:
    return [
        types.Tool(
            name="recognize_image",
            description=(
                "使用豆包视觉模型识别图片内容。\n"
                "参数 image 必须提供，值为图片的本地绝对路径（例如 /home/user/photo.jpg）或网络 URL（例如 https://example.com/cat.png）。\n"
                "参数 prompt 为可选提问，默认为 '描述这张图片'。\n"
                "当用户提供图片路径或 URL 时，请直接调用此工具，并将路径/URL 填入 image 参数。"
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "image": {
                        "type": "string",
                        "description": "本地图片绝对路径或网络 URL"
                    },
                    "prompt": {
                        "type": "string",
                        "description": "自定义提问内容，默认为 '描述这张图片'"
                    }
                },
                "required": ["image"]
            }
        )
    ]

@app.call_tool()
async def call_tool(name: str, arguments: Any) -> list[types.TextContent]:
    if name != "recognize_image":
        raise ValueError(f"未知工具: {name}")

    image_input = arguments.get("image")
    prompt = arguments.get("prompt", "描述这张图片")

    if not image_input:
        return [types.TextContent(type="text", text="错误：缺少 'image' 参数")]

    # ---------- 处理图片 ----------
    try:
        if image_input.startswith(("http://", "https://")):
            image_data_url = image_input
        else:
            path = Path(image_input)
            if not path.exists():
                return [types.TextContent(type="text", text=f"错误：文件不存在 - {image_input}")]
            if not path.is_file():
                return [types.TextContent(type="text", text=f"错误：路径不是文件 - {image_input}")]
            if path.stat().st_size > MAX_IMAGE_SIZE:
                return [types.TextContent(
                    type="text",
                    text=f"错误：图片大小超过 {MAX_IMAGE_SIZE//1024//1024}MB 限制"
                )]
            with open(path, "rb") as f:
                image_bytes = f.read()
            mime = detect_mime_type(image_bytes)
            if not mime:
                return [types.TextContent(type="text", text="错误：不支持的图片格式（仅支持 JPEG, PNG, GIF, WebP, BMP）")]
            b64 = base64.b64encode(image_bytes).decode("utf-8")
            image_data_url = f"data:{mime};base64,{b64}"
    except Exception as e:
        return [types.TextContent(type="text", text=f"处理图片时出错: {str(e)}")]

    # ---------- 调用 API ----------
    headers = {
        "Authorization": f"Bearer {DOUBAO_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": DOUBAO_MODEL,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": image_data_url}}
                ]
            }
        ],
        "max_tokens": 1000
    }

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(DOUBAO_ENDPOINT, headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()
            content = data["choices"][0]["message"]["content"]
            return [types.TextContent(type="text", text=content)]
    except httpx.HTTPStatusError as e:
        return [types.TextContent(type="text", text=f"API 调用失败 (HTTP {e.response.status_code}): {e.response.text}")]
    except httpx.TimeoutException:
        return [types.TextContent(type="text", text="错误：API 请求超时")]
    except Exception as e:
        return [types.TextContent(type="text", text=f"未知错误: {str(e)}")]

def detect_mime_type(data: bytes) -> str | None:
    if data.startswith(b'\xff\xd8'):
        return "image/jpeg"
    if data.startswith(b'\x89PNG\r\n\x1a\n'):
        return "image/png"
    if data.startswith(b'GIF87a') or data.startswith(b'GIF89a'):
        return "image/gif"
    if data.startswith(b'RIFF') and data[8:12] == b'WEBP':
        return "image/webp"
    if data.startswith(b'BM'):
        return "image/bmp"
    return None

async def main_async():
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await app.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="doubao-vision-server",
                server_version="0.1.3",
                capabilities=app.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )

def main():
    asyncio.run(main_async())

if __name__ == "__main__":
    main()