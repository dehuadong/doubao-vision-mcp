好的，我整理一份完整的、最终版的方案，包含所有文件和配置，开箱即用。

---

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

### 1️⃣ 安装 uv

```bash
# macOS / Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# 或使用 Homebrew (macOS)
brew install uv

# Windows (PowerShell)
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
```

验证安装：
```bash
uv --version
```

---

### 2️⃣ 创建项目

```bash
mkdir doubao-vision-mcp
cd doubao-vision-mcp
```

---

### 3️⃣ 创建项目文件
 

---

### 4️⃣ 安装依赖

```bash
uv sync
```

---

### 5️⃣ 设置环境变量

```bash
# 必须设置
export DOUBAO_API_KEY="你的火山引擎 API Key"

# 可选（默认值如下）
export DOUBAO_MODEL="doubao-seed-2.0-pro"
export DOUBAO_ENDPOINT="https://ark.cn-beijing.volces.com/api/v3/chat/completions"
```

---

### 6️⃣ 测试运行

```bash
# 方式一： 
python3 server.py 

# 方式二： 
uv run python server.py
```

如果没有报错，说明服务启动正常（会等待 MCP 协议通信，按 `Ctrl+C` 退出）。

---

## 🔧 配置 Claude Code

在 Claude Code 的 MCP 配置文件（`~/.claude.json` 或项目根目录的 `.mcp.json`）中配置。

### 方式一：在配置中设置环境变量（推荐 ✅）

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

### 方式二：使用系统环境变量

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

识别图片内容。

**参数**：

| 参数 | 类型 | 必填 | 描述 |
|------|------|------|------|
| `image` | string | ✅ | 本地图片路径（绝对或相对路径）或网络 URL |
| `prompt` | string | ❌ | 提问内容，默认为 "描述这张图片" |

**返回**：模型生成的文本描述

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
├── pyproject.toml          # uv 项目配置
├── uv.lock                 # 依赖锁定文件（uv sync 自动生成）
├── server.py               # 主服务代码
└── README.md               # 本文档
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