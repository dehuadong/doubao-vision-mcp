
# Doubao Vision MCP Server

基于 MCP (Model Context Protocol) 的豆包视觉模型服务，为 Claude Code 提供图片识别能力。

## ✨ 功能特性

- 🖼️ **图片识别**：支持本地图片和网络图片 URL
- 🤖 **豆包视觉模型**：使用 `doubao-seed-2.0-pro` 进行图像理解
- 💬 **自定义提问**：可针对图片自由提问
- 📦 **uv 包管理**：快速、隔离、可重现的 Python 环境
- 🔒 **安全**：通过环境变量管理 API 密钥

---

## 📋 前置要求

- Python 3.10 或更高版本
- [uv](https://github.com/astral-sh/uv) 包管理器
- 火山引擎 API Key（开通豆包视觉模型服务）

---

## 🚀 快速开始

### 1️⃣ 克隆项目

```bash
git clone https://github.com/dehuadong/doubao-vision-mcp.git
cd doubao-vision-mcp
```

### 2️⃣ 安装依赖

需要 Python 3.10+ 和 [uv](https://github.com/astral-sh/uv) 包管理器：

```bash
# 安装 uv（如已安装可跳过）
curl -LsSf https://astral.sh/uv/install.sh | sh

# 安装项目依赖
uv sync
```

### 3️⃣ 设置环境变量

```bash
# 必须设置
export DOUBAO_API_KEY="你的火山引擎 API Key"

# 可选（默认值如下）
export DOUBAO_MODEL="doubao-seed-2.0-pro"
export DOUBAO_ENDPOINT="https://ark.cn-beijing.volces.com/api/v3/chat/completions"
export DOUBAO_MAX_TOKENS="1000"
```

### 4️⃣ 测试运行

```bash
uv run python server.py
```

正常启动后会等待 MCP 协议通信（无报错即可，按 `Ctrl+C` 退出）。

---

## 🔧 配置 Claude Code

在 Claude Code 中通过命令行添加，或在项目根目录的 `.mcp.json` 中配置。

### 方式一：使用 claude mcp add 命令（推荐 ✅）

```bash
claude mcp add --transport stdio doubao-vision \
  --env DOUBAO_API_KEY="你的API密钥" \
  -- uv --directory /完整路径/to/doubao-vision-mcp run python server.py
```

### 方式二：使用 .mcp.json 配置文件

在项目根目录创建 `.mcp.json`：

```json
{
  "mcpServers": {
    "doubao-vision": {
      "command": "uv",
      "args": [
        "--directory",
        "/完整路径/to/doubao-vision-mcp",
        "run",
        "python",
        "server.py"
      ],
      "env": {
        "DOUBAO_API_KEY": "你的API密钥",
        "DOUBAO_MODEL": "doubao-seed-2.0-pro"
      }
    }
  }
}
```

### 方式三：使用系统环境变量

如果已经通过 `export` 设置了环境变量，可以省略 `env` 字段：

```json
{
  "mcpServers": {
    "doubao-vision": {
      "command": "uv",
      "args": [
        "--directory",
        "/完整路径/to/doubao-vision-mcp",
        "run",
        "python",
        "server.py"
      ]
    }
  }
}
```

**配置说明**：
- 将 `/完整路径/to/doubao-vision-mcp` 替换为你的实际项目路径
- 推荐方式一，配置集中，不依赖外部环境
- 配置文件权限建议设为 `600`（仅所有者可读写）

---

## 🛠️ 可用工具

### `recognize_image`

使用豆包视觉模型识别图片内容。支持本地文件和网络 URL。

**参数**：

| 参数 | 类型 | 必填 | 描述 |
|------|------|------|------|
| `image` | string | ✅ | 本地图片绝对路径或网络 URL |
| `prompt` | string | ❌ | 对图片的具体提问，会自动拼接到默认分析提示词末尾。不填则仅用默认分析框架进行通用识别 |

**支持格式**：JPEG、PNG、GIF、WebP、BMP、TIFF、ICO、SVG

**返回**：模型按「主要回应 → 详细观察 → 上下文与分析 → 补充说明」结构输出的文本描述

**Prompt 拼接机制**：工具内置默认分析提示词（引导模型结构化输出），不会因为提供 `prompt` 参数而被丢弃。用户传入的 `prompt` 会自动拼接到默认提示词末尾：

- 不传 `prompt` → 仅使用默认分析框架进行通用识别
- 传 `prompt: "图中有什么动物"` → 默认分析框架 + `用户的具体要求：图中有什么动物`

### 环境变量

| 变量 | 必填 | 默认值 | 描述 |
|------|------|------|------|
| `DOUBAO_API_KEY` | ✅ | — | 火山引擎 API Key |
| `DOUBAO_MODEL` | ❌ | `doubao-seed-2.0-pro` | 模型名称 |
| `DOUBAO_ENDPOINT` | ❌ | `https://ark.cn-beijing.volces.com/api/v3/chat/completions` | API 端点 |
| `DOUBAO_MAX_TOKENS` | ❌ | `1000` | 最大输出 token 数 |

---

## 💡 使用示例

在 Claude Code 对话中：

```
调用 recognize_image 工具,识别这张图片：/Users/me/photo.jpg
```

```
这张图里有什么？图片在 https://example.com/cat.png
```

```
调用 recognize_image 工具分析这张图片，告诉我主要颜色和物体：~/Pictures/screenshot.png
```

---

## 📦 项目结构

```
doubao-vision-mcp/
├── server.py                # 主服务代码
├── pyproject.toml           # uv 项目配置
├── README.md                # 本文档
├── 提示词.md                 # 默认分析提示词
└── .gitignore               # Git 忽略规则
```

---

## 🔍 故障排查

### 1. 提示 "请设置环境变量 DOUBAO_API_KEY"

**原因**：未设置或未正确传递 API Key

**解决**：
```bash
export DOUBAO_API_KEY="你的真实密钥"
```
或在 MCP 配置的 `env` 中添加

### 2. API 调用失败 (HTTP 401)

**原因**：API Key 无效或过期

**解决**：检查火山引擎控制台，确认密钥有效且已开通豆包视觉模型服务

### 3. 图片文件不存在

**原因**：路径错误或相对路径问题

**解决**：使用绝对路径

### 4. uv 命令未找到

**原因**：uv 未安装或未加入 PATH

**解决**：重新安装 uv 或重启终端

### 5. ModuleNotFoundError

**原因**：依赖未安装

**解决**：
```bash
uv sync
```

---

## 📚 参考资料

- [MCP 协议文档](https://modelcontextprotocol.io)
- [豆包视觉模型文档](https://www.volcengine.com/docs/82379)
- [uv 包管理器](https://docs.astral.sh/uv/)

---

## 📄 许可证

MIT License

---

**祝你使用愉快！** 🎉