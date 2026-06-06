# draw-image — Claude Code AI 绘图 Skill

> **English readers: see [README.md](README.md) for the full English tutorial.**

一个 Claude Code 技能插件：让你（或你的 AI 助手）通过你自己的图像生成 API 账号来画图。
只需编辑一个 YAML 文件完成配置，一行命令完成绘图，零代码。

**支持的服务商：**
[火山方舟 ARK（豆包 Seedream）](https://console.volcengine.com/ark) ·
[OpenAI（GPT-image-1 / DALL·E 3）](https://platform.openai.com) ·
[阿里云百炼（通义万相）](https://bailian.console.aliyun.com) ·
以及任意 OpenAI 兼容接口（Replicate、Together、OpenRouter 等）

---

## 五分钟快速上手

```bash
# 1. 安装 Python 依赖
pip install -r requirements.txt

# 2. 首次运行——自动从模板创建 config.yaml
python scripts/draw.py --validate-config
# → 提示 "Created config.yaml from template. Next steps: 1. Edit this file..."

# 3. 用文本编辑器打开 config.yaml，把某一个 api_key 替换成你的真实 key
#    （或者设置对应的环境变量——见下方第三步）

# 4. 再次验证
python scripts/draw.py --validate-config
# → "OK: config is valid."

# 5. 生成第一张图
python scripts/draw.py "一只坐在窗边的猫，水彩风格"
# → ~/Pictures/draw-image/20260606_143021_a1b2c3.jpg
```

---

## 第一步 —— 准备工作

| 需要什么 | 如何检查 | 去哪里获取 |
|---|---|---|
| **Python 3.8+** | `python --version` | [python.org](https://python.org) |
| **一个 API Key** | — | 选一个下面的服务商 |

至少选一个服务商并获取 API Key：

| 服务商 | 获取 Key 的地方 | 费用参考 |
|---|---|---|
| 火山方舟 ARK | [console.volcengine.com → ARK → API Key 管理](https://console.volcengine.com/ark/region:ark+cn-beijing/openManagement?LLM) | 按张计费，约 ¥0.10–0.50/张 |
| OpenAI | [platform.openai.com → API keys](https://platform.openai.com/api-keys) | 按张计费，约 $0.02–0.08/张 |
| 阿里云百炼 | [bailian.console.aliyun.com → API Keys](https://bailian.console.aliyun.com/) | 按张计费 |

还没拿到 Key 也可以先装完依赖、跑验证——验证器会明确告诉你缺了哪个 Key。

---

## 第二步 —— 安装依赖

```bash
# 在 draw-image/ 目录下执行
pip install -r requirements.txt
```

这会安装 **pyyaml** 和 **pydantic**（必装，约 5 MB）。

| 包名 | 是否必装 | 用途 |
|---|---|---|
| `pyyaml` | ✅ 必装 | 读取 config.yaml |
| `pydantic` | ✅ 必装 | 校验配置 |
| `pypdf` | ⚪ 可选 | `auto_add_provider.py`（PDF → YAML） |
| `aiohttp` | ⚪ 可选 | `--stream` 流式输出 |

> **Windows 用户：** 如果提示 `'pip' 不是内部或外部命令`，请用
> `python -m pip install -r requirements.txt`。

---

## 第三步 —— 获取 API Key

### 选一个服务商

你只需要一个能用的就行。skill 自带了三个预配置好的服务商模板，选你已有账号的那个。

<details>
<summary><b>火山方舟 ARK（推荐国内用户使用）</b></summary>

1. 打开 [console.volcengine.com](https://console.volcengine.com/)。
2. 在产品列表中找到 **方舟（ARK）**。
3. 创建一个**推理接入点**，模型选 `Doubao-Seedream-5.0-lite`。
4. 进入 **API Key 管理** → 创建 Key。
5. 复制 Key（以 `ark-` 开头）。

`config.yaml` 中的默认模型 `doubao-seedream-5-0-260128` 已经配好了。
</details>

<details>
<summary><b>OpenAI</b></summary>

1. 打开 [platform.openai.com/api-keys](https://platform.openai.com/api-keys)。
2. 创建一个新的 Secret Key。
3. 复制 Key（以 `sk-` 开头）。
4. 确保账户有余额——图像生成是独立计费的，和 ChatGPT 订阅无关。
</details>

<details>
<summary><b>阿里云百炼</b></summary>

1. 打开 [bailian.console.aliyun.com](https://bailian.console.aliyun.com/)。
2. 开通 **通义万相（Qwen-image）** 模型。
3. 在控制台创建 API Key。
4. 复制 Key。
</details>

### 填入 Key

用任意文本编辑器打开 `config.yaml`，找到你选的服务商对应的那一块。有两种填法：

**方式 A —— 环境变量（推荐，更安全）：**

保持 `api_key: ${ARK_API_KEY}` 不变，在终端里设置变量：

```bash
# macOS / Linux（加到 ~/.bashrc 或 ~/.zshrc）
export ARK_API_KEY="ark-你的key"

# Windows PowerShell
$env:ARK_API_KEY = "ark-你的key"

# Windows 命令提示符
set ARK_API_KEY=ark-你的key
```

**方式 B —— 直接填入（更简单，但不够安全）：**

把占位符替换成真实 Key：

```yaml
volcengine:
  api_key: ark-你的真实key    # <-- 把 key 贴在这里
```

> ⚠️ `config.yaml` 已加入 `.gitignore`，不会被提交到 Git。但如果选了方式 B，
> 不要把这个文件发给别人。

其他服务商的 Key 同理（用不着的可以保持原样，验证时会提醒你有未展开的变量）。

---

## 第四步 —— 验证配置

```bash
python scripts/draw.py --validate-config
```

一切正常的话：

```
Loading .../config.yaml...
  default_provider: volcengine
  providers: 3
    - volcengine: type=volcengine, model=doubao-seedream-5-0-260128, api_key=ark-***xxxx
    ...

OK: config is valid.
```

如果 Key 缺失或环境变量没设，你会看到明确的提示：

```
config.yaml validation failed:
  - providers.volcengine: api_key placeholder(s) not resolved: ${ARK_API_KEY}.
    Set the matching environment variable(s) or edit config.yaml directly.
```

所有输出中的 API Key 都会被脱敏处理（显示为 `ark-***cdef`），完整的 Key 绝不会出现在日志里。

---

## 第五步 —— 生成第一张图

```bash
python scripts/draw.py "一只坐在窗边的猫，水彩风格"
```

脚本输出保存的路径：

```
/Users/you/Pictures/draw-image/20260606_143021_a1b2c3.jpg
```

Windows 上：

```
C:\Users\you\Pictures\draw-image\20260606_143021_a1b2c3.jpg
```

**图片默认保存在 `~/Pictures/draw-image/`。** 可以用 `--save-dir` 自定义目录。

---

## 日常使用（配合 Claude Code）

配置好之后，你就不需要碰命令行了。直接跟 Claude Code 说话：

> **你：** 给我画一只坐在窗边的猫，水彩风格
>
> **Claude Code：** *（自动调用 draw-image skill）* → `~/Pictures/draw-image/xxx.jpg`
> 画好了！图片在 `~/Pictures/draw-image/xxx.jpg`。

[SKILL.md](SKILL.md) 的 frontmatter 告诉 Claude Code 何时触发这个 skill。
不需要手动 `cd`、不需要关心路径——脚本通过 `__file__` 自动定位自己的位置。

要用其他服务商，告诉 agent：*"用 OpenAI 画个 logo"*——它会自动加 `--provider openai`。

---

## 命令行参考

```
python scripts/draw.py "提示词" [参数]
```

| 参数 | 作用 | 支持范围 |
|---|---|---|
| *`提示词`* | 图片描述（位置参数，必填） | 全部 |
| `--provider NAME` | 选择服务商 | 全部 |
| `--size WxH` 或 `--size 2K` | 输出尺寸 | 全部 |
| `--image 路径/URL` | 单张参考图 | 全部 |
| `--images A B C` | 多张参考图 | 全部 |
| `--sequential` | 组图模式 | 仅 volcengine |
| `--max-images N` | 组图数量上限 | 仅 volcengine |
| `--no-watermark` | 去除水印 | 仅 volcengine |
| `--stream` | 流式实时输出 | 仅 volcengine（需 aiohttp） |
| `--n N` | 生成图片数量 | openai-compatible |
| `--response-format url\|b64_json` | API 返回格式 | 全部 *¹ |
| `--output-format jpeg\|png` | 输出文件格式 | 仅 volcengine |
| `--save-dir 路径` | 自定义保存目录 | 全部 |
| `--json` | 输出结构化 JSON | 全部 |
| `--validate-config` | 只验证配置，不画图 | 全部 |

> *¹ `--response-format`：`url` 从链接下载；`b64_json` 从 base64 解码。
> volcengine 始终返回 URL 并自动下载，此参数对 volcengine 不生效但不会报错。

### JSON 输出

加 `--json` 获取结构化的机器可读输出：

```bash
python scripts/draw.py --json "一只猫"
```

```json
{
  "model": "doubao-seedream-5-0-260128",
  "created": 1718123456,
  "paths": ["/home/you/Pictures/draw-image/20260606_143021_a1b2c3.jpg"],
  "usage": {
    "generated_images": 1,
    "output_tokens": 0,
    "total_tokens": 0,
    "web_search_calls": 0
  }
}
```

---

## 更多示例

```bash
# 文生图（任意服务商）
python scripts/draw.py "赛博朋克城市天际线，黄昏时分"

# 指定服务商
python scripts/draw.py --provider openai "一只狐狸的极简 logo"

# 指定尺寸
python scripts/draw.py --size 3K "壮阔的山脉风景"

# 图生图（拿一张图做参考）
python scripts/draw.py --image ~/猫.jpg "把它画成油画风格"

# 多张参考图（最多 14 张）
python scripts/draw.py --images ~/a.jpg ~/b.jpg ~/c.jpg "融合这三张图的风格"

# 组图模式（volcengine 专属）
python scripts/draw.py --sequential --max-images 4 "四种水果的图标"

# 流式输出（volcengine，需 aiohttp）
python scripts/draw.py --stream "一系列奇幻风景画"

# JSON 输出（给脚本用）
python scripts/draw.py --json "一只猫" | jq .paths[0]

# 自定义保存目录
python scripts/draw.py --save-dir ~/Desktop "一只猫"

# PNG 格式输出（volcengine）
python scripts/draw.py --output-format png "一只猫"

# 去掉水印（volcengine）
python scripts/draw.py --no-watermark "一只猫"
```

---

## 添加更多服务商

### 方式一：纯 YAML（最简单）

如果新服务商的 API 和 OpenAI 一样（`POST /v1/images/generations`），直接在 `config.yaml`
里加一个配置块：

```yaml
  my-new-provider:
    type: openai-compatible
    base_url: https://api.myprovider.com/v1
    api_key: ${MYPROV_API_KEY}
    model: their-model-id
    default_size: 1024x1024
```

如果服务商的字段名不一样，可以做字段映射：

```yaml
    request_fields:
      prompt: your_prompt_field
      size: dimensions
    image_field: image_urls       # 如果参考图字段名不同
    multi_image: true             # 如果要求参考图始终以数组形式发送
```

运行 `python scripts/draw.py --validate-config` 验证即可。不需要写 Python 代码。

### 方式二：PDF → YAML（半自动）

如果你有服务商的 API 文档 PDF：

```bash
python scripts/auto_add_provider.py 路径/文档.pdf --provider-name myprov
```

脚本会输出一个 YAML 块，包含能自动提取的字段，以及需要你手动填写的
`TODO_xxx` 标记。

> ⚠️ **如果 PDF 是扫描件或多栏排版，提取效果会很差**（大部分字段显示为 `TODO_xxx`）。
> 建议优先寻找该服务的在线文档或纯文本说明，直接发给 AI agent 处理。

要直接写入 config.yaml：

```bash
python scripts/auto_add_provider.py 路径/文档.pdf --provider-name myprov --apply --yes
```

### 方式三：自定义 Python Provider（高级）

如果服务商用了 WebSocket、消息队列等非 HTTP 协议，在 `lib/providers/` 下写一个
Python 文件即可。参考 [provider-schema.md](references/provider-schema.md) 和
[adding-a-provider.md](references/adding-a-provider.md)。

---

## 图片保存在哪里

| 平台 | 默认路径 |
|---|---|
| Windows | `C:\Users\<你的用户名>\Pictures\draw-image\` |
| macOS | `/Users/<你的用户名>/Pictures/draw-image/` |
| Linux | `/home/<你的用户名>/Pictures/draw-image/` |

文件命名：`YYYYMMDD_HHMMSS_01_xxxxxx.jpg`（时间戳 + 序号 + 随机后缀）。

修改保存位置有两种方式：

- 在 `config.yaml` 中按服务商设置 `save_dir`
- 命令行加 `--save-dir /自定义/路径`

---

## 安全性

- **Key 绝不出现在聊天记录里。** 用 `api_key: ${ENV_VAR}` 形式，Key 只存在于环境
  变量中，不进任何文件。
- **`config.yaml` 在 `.gitignore` 里。** 只有 `config.example.yaml`（含占位符的模板）
  可以被提交到 Git。
- **错误消息脱敏处理。** 任何 API Key 在错误输出中都会被截断为 `前4位***后4位`
  （如 `ark-***cdef`）。
- **自动复制时发出警告。** 如果 `config.yaml` 不存在，脚本自动从模板复制时会打印
  醒目的编辑提示。

---

## 常见问题

| 症状 | 原因 | 解决方法 |
|---|---|---|
| `'python' 不是内部或外部命令` | 没装 Python 或没加 PATH | 从 [python.org](https://python.org) 安装 Python 3.8+ |
| `ModuleNotFoundError: No module named 'pydantic'` | 依赖没装 | `pip install -r requirements.txt` |
| `config.yaml validation failed: api_key placeholder(s) not resolved` | 环境变量没设 | `export ARK_API_KEY=...` 或在 config.yaml 中直接替换 `${ARK_API_KEY}` |
| `Config not found` | 缺少 config.yaml | 跑一次 `--validate-config`（会自动从模板创建） |
| `AuthenticationError` | Key 无效或过期 | 去服务商控制台重新生成 Key |
| `NotFoundError` | 模型 ID 或接口地址填错了 | 检查 `config.yaml` 里的 `model:` 和 `base_url:` |
| `InvalidParameterError: image size must be at least 3686400 pixels` | 尺寸太小（volcengine 限制） | 用 `--size 2K` 或更大（≥ 370 万像素） |
| `SensitiveContentError` | 提示词被内容审核拦截 | 换个说法重新描述 |
| `RateLimitError` | 请求太频繁 | 等几秒再试 |
| `QuotaExceededError` | 额度用完了 | 去服务商平台充值 |
| `InternalServerError` | 服务商那边出了问题 | 重试；持续报错就联系服务商 |
| `Streaming unavailable`（--stream 时） | 没装 aiohttp | `pip install aiohttp` |
| 图片没出现在预期的位置 | 保存目录不对 | 检查 `--save-dir` 参数或 `config.yaml` 里的 `save_dir` |

---

## 项目结构

```
draw-image/
├── SKILL.md                       # AI agent 操作手册
├── README.md                      # 英文教程（本文件的中文版）
├── README_zh.md                   # 中文教程（你正在看的）
├── config.yaml                    # 你的服务商配置（gitignore）
├── config.example.yaml            # 纯净模板（可提交）
├── requirements.txt               # Python 依赖
├── .gitignore
├── references/
│   ├── provider-schema.md         # 完整 YAML 字段参考
│   ├── adding-a-provider.md       # 详细的服务商接入指南
│   └── providers/                 # 各服务商注意事项
├── scripts/
│   ├── draw.py                    # 主命令行入口
│   ├── validate_config.py         # 配置预检查
│   └── auto_add_provider.py       # PDF → YAML 桥接工具
├── lib/                           # 内部 Python 库
└── tests/
    └── test_self.py               # 自测套件（15 个测试，无需联网）
```

---

## 许可证

MIT.
