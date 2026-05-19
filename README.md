# AI聊天系统

一个可扩展的AI聊天系统，支持插件、脚本和**多模型切换**。

## 项目结构

```
ai_chat_system/
├── backend/                 # 后端代码
│   ├── app/
│   │   ├── main.py         # FastAPI主程序
│   │   ├── models/         # 数据库模型
│   │   ├── routes/         # API路由
│   │   ├── services/       # 业务服务
│   │   │   ├── llm_service.py      # AI对话服务（支持多模型）
│   │   │   ├── tts_service.py      # 语音合成服务
│   │   │   └── model_registry.py   # 模型注册表（模型广场核心）
│   │   ├── plugins/        # 插件系统
│   │   └── scripts/        # 脚本系统
│   └── requirements.txt    # Python依赖
├── frontend/               # 前端代码
│   └── index.html          # 聊天界面（含模型选择器）
├── plugins/                # 用户插件目录
└── scripts/                # 用户脚本目录
```

## 快速开始

### 1. 安装依赖

```bash
cd backend
pip install -r requirements.txt
```

### 2. 配置环境变量

```bash
cd backend
copy .env.example .env
```

编辑 `.env` 文件，填入你的API密钥：
- `DEEPSEEK_API_KEY`: DeepSeek API密钥（默认使用）
- `OPENAI_API_KEY`: OpenAI API密钥（用于TTS语音合成）
- `DASHSCOPE_API_KEY`: 阿里云通义千问API密钥（可选）
- `ZHIPU_API_KEY`: 智谱AI API密钥（可选）
- `BAIDU_API_KEY`: 百度文心API密钥（可选）

### 3. 启动后端服务

```bash
cd backend
C:\Trae\PyCharm_\.venv\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8001
```

服务将在 `http://localhost:8001` 启动

### 4. 打开前端

在浏览器中打开 `frontend/index.html`

## 模型广场

系统支持多个AI模型，可以在运行时动态切换：

| 提供商 | 模型 | 特点 |
|--------|------|------|
| DeepSeek | deepseek-v4-flash | 快速响应，成本低（默认） |
| DeepSeek | deepseek-v4-pro | 更强的推理能力 |
| OpenAI | gpt-4o | 最强模型，多模态支持 |
| OpenAI | gpt-4o-mini | 轻量级，速度快 |
| 阿里云 | qwen-plus | 中文能力强 |
| 阿里云 | qwen-max | 通义千问最强版本 |
| 智谱AI | glm-4 | 智谱AI最新模型 |
| 百度 | ernie-4.0 | 文心一言最强版本 |

### 如何切换模型

1. **前端界面**：点击聊天界面顶部的"模型广场"按钮，选择想要的模型
2. **下拉选择器**：在聊天输入框上方直接选择模型
3. **API调用**：通过 `POST /api/models/switch` 接口切换

### 添加新模型

编辑 `backend/app/services/model_registry.py`，在 `_register_default_models()` 方法中添加新模型配置：

```python
self.register(ModelConfig(
    id="your-model-id",
    name="你的模型名称",
    provider="提供商名称",
    model_name="模型名称",
    base_url="API地址",
    api_key_env="API_KEY环境变量名",
    description="模型描述",
    enabled=True,
    features=["特性1", "特性2"]
))
```

## 创建插件

在 `plugins/` 目录创建Python文件，继承 `BasePlugin` 类：

```python
from app.plugins.plugin_base import BasePlugin

class MyPlugin(BasePlugin):
    async def on_message_received(self, message: str, user_id: str):
        # 你的逻辑
        return {"type": "custom", "data": "value"}
```

## 创建脚本

在 `scripts/` 目录创建Python文件，继承 `BaseScript` 类：

```python
from app.scripts.script_base import BaseScript

class MyScript(BaseScript):
    async def run(self, args=None):
        # 你的逻辑
        return {"success": True, "message": "完成"}
```

## API接口

### 聊天接口
- `POST /api/chat/send` - 发送消息
- `GET /api/chat/history/{user_id}` - 获取聊天历史

### 模型广场接口
- `GET /api/models/list` - 获取所有可用模型
- `GET /api/models/current` - 获取当前使用的模型
- `POST /api/models/switch` - 切换模型
- `GET /api/models/providers` - 获取所有提供商列表

### 插件和脚本接口
- `GET /api/plugins` - 列出插件
- `POST /api/scripts/run` - 运行脚本

### 系统接口
- `GET /` - 系统信息
- `GET /health` - 健康检查

## 技术栈

- **后端**: FastAPI (Python)
- **数据库**: SQLite + SQLAlchemy
- **AI模型**: 多模型支持（DeepSeek、OpenAI、通义千问等）
- **语音合成**: OpenAI TTS
- **前端**: 原生HTML/CSS/JavaScript
