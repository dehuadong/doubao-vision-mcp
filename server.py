#!/usr/bin/env python3
"""Doubao Vision MCP Server — 豆包视觉模型 MCP 服务。

通过 MCP 协议为 Claude 提供图片识别能力，支持本地文件和网络 URL。
"""

import asyncio
import base64
import logging
import mimetypes
import os
from pathlib import Path
from typing import Any

import httpx
from mcp.server import Server, NotificationOptions
from mcp.server.models import InitializationOptions
import mcp.server.stdio
import mcp.types as types

# ---------------------------------------------------------------------------
# 配置 — 全部通过环境变量注入
# ---------------------------------------------------------------------------
DOUBAO_API_KEY = os.environ.get("DOUBAO_API_KEY")
DOUBAO_ENDPOINT = os.environ.get(
    "DOUBAO_ENDPOINT",
    "https://ark.cn-beijing.volces.com/api/v3/chat/completions",
)
DOUBAO_MODEL = os.environ.get("DOUBAO_MODEL", "doubao-seed-2.0-pro")
MAX_IMAGE_SIZE = 20 * 1024 * 1024  # 20 MB
MAX_TOKENS = int(os.environ.get("DOUBAO_MAX_TOKENS", "1000"))

VERSION = "0.2.0"

logger = logging.getLogger("doubao-vision-mcp")

# ---------------------------------------------------------------------------
# 默认提示词 — 通用图像分析
# ---------------------------------------------------------------------------
DEFAULT_PROMPT = (
    "你是一位具备全面图像理解能力的高级 AI 视觉助手。你的优势在于适应性——你可以分析任何视觉内容，"
    "并根据用户的具体需求提供定制化的洞察，无论是识别物体、理解上下文、提取信息，还是提供详细描述。\n\n"
    "<task>\n"
    "你的任务是根据用户的具体指令分析所提供的图像，并提供详细、准确的回应以满足其需求。"
    "由于这是一个通用工具，你的分析方法应以用户的提问为导向，而不是遵循预定的模板。\n"
    "</task>\n\n"
    "<approach>\n"
    "首先仔细检查整个图像，了解其包含的内容。识别所有重要元素——物体、人物、文字、符号、"
    "背景以及任何其他视觉组成部分。注意构图、布局以及元素之间的相互关系。"
    "理解上下文——这是什么类型的图像，其用途或来源可能是什么？\n\n"
    "密切关注用户提示中的具体请求。他们究竟要求你做什么？他们是否要求你：\n"
    "- 识别或描述图像中的某个特定内容？\n"
    "- 针对某些特征或品质分析图像？\n"
    "- 提取图像中可见的特定信息或数据？\n"
    "- 理解所展示内容背后的上下文或含义？\n"
    "- 比较图像中的元素？\n"
    "- 根据你的观察做出推断或得出结论？\n\n"
    "根据他们的请求调整你的分析深度和重点。如果他们询问某个具体细节，"
    "则在提供必要上下文的同时重点关注该细节。如果他们要求全面概述，则要做到全面和系统。"
    "如果他们提出具体问题，则直接回答并提供支持性观察。\n\n"
    "考虑对用户具体需求重要的细节。如果分析视觉美学，则关注颜色、构图、光照和风格。"
    "如果提取信息，则要精确、系统地捕捉所有相关数据。"
    "如果识别物体或元素，则要具体说明你看到的内容及其位置。\n\n"
    "在观察中做到准确和诚实。只陈述你能够在图像中自信观察到的内容。"
    "如果有不清楚、模糊或仅凭视觉无法确定的内容，请指出这一点，而不是猜测。"
    "区分直接观察（你能清楚看到的内容）和推断（你根据上下文或常见模式推导出的内容）。\n\n"
    "在有用的情况下提供上下文和解释。不要只是罗列观察结果——帮助用户理解它们的含义或重要性。"
    "如果你注意到某些超出他们具体提问范围的重要或有趣的内容，也请提及，因为这对他们可能有价值。\n\n"
    "根据用户的请求逻辑性地组织你的回应。如果他们问的是直接问题，先清晰回答，再提供支持性细节。"
    "如果他们要求全面分析，则以逐步构建理解的方式组织你的回应。\n"
    "</approach>\n\n"
    "<output_structure>\n"
    "组织你的回应，使其清晰且立即可用：\n\n"
    "以**主要回应**部分开始，直接回应用户的请求。回答他们的问题，提供他们要求的分析，"
    "或提取他们需要的信息。做到清晰和具体。\n\n"
    "接下来是**详细观察**，提供支持你主要回应或提供额外上下文的相关细节。"
    "按逻辑组织这些内容——可以按图像中的位置、按观察类别或按重要性排列。"
    "包括有助于理解或可能对用户有用的具体细节。\n\n"
    "如果合适，包含一个**上下文与分析**部分，在其中解读你的观察或提供洞察。"
    "这是你超越纯粹描述走向理解的环节。图像暗示或传达了什么？你注意到什么模式或关系？"
    "可以得出什么结论？\n\n"
    "如果有其他可能有价值但未被直接请求的观察结果，将它们放在**补充说明**部分。"
    "这可能包括：关于图像质量或技术方面的观察、图像中可能引起兴趣的相关元素、"
    "图像的潜在应用或用途，或可能有帮助的相关分析建议。\n"
    "</output_structure>\n\n"
    "你的目标是通过提供用户所需的确切信息和分析来真正提供帮助，"
    "并以清晰、有条理和富有洞察力的方式呈现。"
    "根据他们的具体情况调整你的回应，而不是将他们的请求强行塞入预定格式。"
)

# ---------------------------------------------------------------------------
# MIME 类型检测 — magic bytes + 扩展名回退
# ---------------------------------------------------------------------------
_MAGIC_SIGNATURES: list[tuple[bytes, str]] = [
    (b"\xff\xd8\xff", "image/jpeg"),
    (b"\x89PNG\r\n\x1a\n", "image/png"),
    (b"GIF87a", "image/gif"),
    (b"GIF89a", "image/gif"),
    (b"RIFF", "image/webp"),       # RIFF....WEBP — checked below
    (b"BM", "image/bmp"),
    (b"\x00\x00\x01\x00", "image/x-icon"),  # ICO
]

def detect_mime_type(data: bytes, *, filepath: str = "") -> str | None:
    """通过文件头魔数检测图片 MIME 类型，失败时回退到扩展名猜测。"""
    # 1) magic bytes
    for magic, mime in _MAGIC_SIGNATURES:
        if data.startswith(magic):
            if mime == "image/webp":
                # 额外校验：RIFF 容器里必须是 WEBP
                if len(data) >= 12 and data[8:12] == b"WEBP":
                    return "image/webp"
                continue  # RIFF 但不是 WEBP，继续尝试其他签名
            return mime

    # 2) TIFF (两种字节序)
    if data.startswith(b"II*\x00") or data.startswith(b"MM\x00*"):
        return "image/tiff"

    # 3) SVG (文本格式)
    text_preview = data[:2048].lstrip()
    if text_preview.startswith(b"<svg") or text_preview.startswith(b"<?xml"):
        return "image/svg+xml"

    # 4) 回退到扩展名
    if filepath:
        mime, _ = mimetypes.guess_type(filepath)
        if mime and mime.startswith("image/"):
            return mime

    return None


# ---------------------------------------------------------------------------
# MCP Server
# ---------------------------------------------------------------------------
app = Server(
    name="doubao-vision-server",
    version=VERSION,
    instructions=(
        "当用户提供图片路径或 URL 并要求识别/描述/分析图片内容时，"
        "请直接调用 recognize_image 工具，将用户提供的图片路径或 URL 填入 image 必选参数。"
    ),
)

@app.list_tools()
async def list_tools() -> list[types.Tool]:
    return [
        types.Tool(
            name="recognize_image",
            title="识别图片",
            description=(
                "使用豆包视觉模型（doubao-seed-2.0-pro）识别图片内容。"
                "支持本地绝对路径和网络 URL。"
                "返回模型的文字描述，可用于物体识别、文字提取、场景理解等。"
                "不支持视频或非图片文件。"
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "image": {
                        "type": "string",
                        "description": (
                            "图片的本地绝对路径（如 /home/user/photo.jpg）"
                            "或网络 URL（如 https://example.com/cat.png）"
                        ),
                    },
                    "prompt": {
                        "type": "string",
                        "description": (
                            "对图片的具体提问，如 '图中有什么物体'、'这张图的主色调是什么'。"
                            "不填则仅使用默认分析框架进行通用识别。"
                            "填写后会自动拼接到默认分析提示词末尾，"
                            "引导模型按「主要回应→详细观察→上下文与分析→补充说明」结构输出。"
                        ),
                        ),
                    },
                },
                "required": ["image"],
            },
            annotations=types.ToolAnnotations(
                title="识别图片",
                readOnlyHint=True,
                openWorldHint=True,
            ),
        )
    ]


@app.call_tool()
async def call_tool(name: str, arguments: Any) -> types.CallToolResult:
    if name != "recognize_image":
        raise ValueError(f"未知工具: {name}")

    if not DOUBAO_API_KEY:
        return _error("未设置 DOUBAO_API_KEY 环境变量。请在 MCP 配置中添加 env 字段，或通过 export 设置。")

    image_input: str | None = arguments.get("image")
    user_prompt: str | None = arguments.get("prompt")
    prompt = _build_prompt(user_prompt)

    if not image_input:
        return _error("缺少必填参数 'image'，请提供图片的本地路径或网络 URL。")

    # ---------- 解析图片 ----------
    try:
        image_data_url = await _resolve_image(image_input)
    except _UserError as exc:
        return _error(str(exc))
    except Exception as exc:
        logger.exception("处理图片时出错")
        return _error(f"处理图片时出错: {exc}")

    # ---------- 调用 Doubao API ----------
    headers = {
        "Authorization": f"Bearer {DOUBAO_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": DOUBAO_MODEL,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": image_data_url}},
                ],
            }
        ],
        "max_tokens": MAX_TOKENS,
    }

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(DOUBAO_ENDPOINT, headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()
            content = data["choices"][0]["message"]["content"]
            return types.CallToolResult(
                content=[types.TextContent(type="text", text=content)],
            )
    except httpx.HTTPStatusError as e:
        logger.error("API HTTP %s: %s", e.response.status_code, e.response.text[:500])
        return _error(
            f"API 调用失败 (HTTP {e.response.status_code})。"
            "请检查 DOUBAO_API_KEY 是否有效，以及模型是否已开通。"
        )
    except httpx.TimeoutException:
        return _error("API 请求超时（60s），请稍后重试或减小图片尺寸。")
    except Exception as exc:
        logger.exception("API 调用未知错误")
        return _error(f"调用 API 时发生未知错误: {exc}")


# ---------------------------------------------------------------------------
# 辅助函数
# ---------------------------------------------------------------------------

class _UserError(Exception):
    """用户侧错误（参数/文件问题），消息直接展示给用户。"""


def _error(message: str) -> types.CallToolResult:
    """构造 MCP 错误结果。"""
    return types.CallToolResult(
        isError=True,
        content=[types.TextContent(type="text", text=message)],
    )


def _build_prompt(user_prompt: str | None) -> str:
    """拼接最终提示词：始终包含默认分析框架，用户问题追加到末尾。"""
    if user_prompt:
        return f"{DEFAULT_PROMPT}\n\n用户的具体要求：{user_prompt}"
    return DEFAULT_PROMPT


async def _resolve_image(raw: str) -> str:
    """将用户输入解析为 data URL 或直接返回原始 URL。

    网络 URL 原样返回（由 API 侧下载）；本地路径读取后编码为 base64 data URL。
    """
    if raw.startswith(("http://", "https://")):
        return raw

    path = Path(raw)
    if not path.exists():
        raise _UserError(f"文件不存在: {raw}")
    if not path.is_file():
        raise _UserError(f"路径不是文件: {raw}")
    if path.stat().st_size > MAX_IMAGE_SIZE:
        raise _UserError(
            f"图片大小超过 {MAX_IMAGE_SIZE // 1024 // 1024} MB 限制，"
            "请压缩后再试。"
        )

    image_bytes = path.read_bytes()
    mime = detect_mime_type(image_bytes, filepath=path.name)
    if not mime:
        raise _UserError(
            "不支持的图片格式。"
            "支持 JPEG、PNG、GIF、WebP、BMP、TIFF、ICO、SVG。"
        )
    b64 = base64.b64encode(image_bytes).decode("utf-8")
    return f"data:{mime};base64,{b64}"


# ---------------------------------------------------------------------------
# 入口
# ---------------------------------------------------------------------------

async def main_async() -> None:
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await app.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="doubao-vision-server",
                server_version=VERSION,
                capabilities=app.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )


def main() -> None:
    asyncio.run(main_async())


if __name__ == "__main__":
    main()
