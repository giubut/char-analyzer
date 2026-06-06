# 角色性格变化分析工具

分析小说角色在故事前后的性格变化。不依赖外部 Python 库，打包为单 exe 运行。

## 原理

1. **文本分析** — 从前段文本提取角色人格画像 + 世界观规则
2. **双 Agent 模拟** — 乐观路径和怀疑路径的 Agent 同时代入角色，预测行为
3. **Agent 辩论** — 两个 Agent 互相质疑推理
4. **裁判打分** — 对比预测行为与实际行为，给出可预测性和合理性评分
5. **变化分析 + 未来预测** — 量化角色变化指数，推演发展方向

## 运行方式

### 方式一：直接运行

```bash
pip install pyinstaller  # 仅打包时需要
python main.py
```

### 方式二：打包为 exe

```bash
build.bat
```

双击 `dist\char_analyzer.exe`。

## 使用说明

### 投放文本

界面上的「📂 前段投放文件夹」和「📂 后段投放文件夹」按钮打开对应文件夹，把 .txt 文件拖进去即可自动加载。

- **前段文本**：故事前期角色出场的片段（用于提取人格画像）
- **后段文本**：故事后期角色面临关键抉择的片段（用于分析行为变化）

也可以直接点击「选择」按钮选文件，会自动复制到投放文件夹。

### 分析流程

1. 选好前后段文本，填写角色名
2. 点击「开始分析」
3. 等 5~10 分钟（取决于模型速度和文本长度）
4. 查看分析结果

### API 配置

支持任何 OpenAI 兼容的 API 接口。在「设置」标签页填写：

- **Base URL**：API 地址
- **API Key**：你的密钥
- **模型**：建议选上下文窗口较大的模型（如 Qwen3.5-72B、GPT-4o）

## 文件结构

```
├── main.py               # 主程序、GUI 界面
├── pipeline.py           # 分析管线（串联所有模块）
├── api_client.py         # API 调用（兼容 OpenAI 格式）
├── config.py             # 配置读写、API Key 加密
├── text_analyzer.py      # 文本分析、人格画像
├── scene_selector.py     # 关键场景选择
├── agent_simulator.py    # 双 Agent 模拟
├── debate_engine.py      # Agent 辩论
├── judge.py              # 裁判打分、世界观推演
├── change_analyzer.py    # 变化分析、未来预测
├── report_generator.py   # 报告生成
├── overseer.py           # 步骤跟踪
├── utils.py              # 日志、历史记录
├── build.bat             # 打包脚本
├── char_analyzer.spec    # PyInstaller 配置
└── .gitignore
```

## 运行时产生的文件

| 文件夹 | 用途 | 说明 |
|--------|------|------|
| `dropbox/` | 文本投放 | 拖入 txt 自动加载，分析后自动清空 |
| `logs/` | 日志 | 每次运行记录到文件 |
| `history/` | 分析结果存档 | 按角色+时间保存报告 |
| `config.json` | 配置 | 自动生成，含加密的 API Key |

## 适合场景

- 短篇 / 同人 / 特定情节片段对比（500~20000 字）
- 角色性格转变分析
- 创作合理性评估

## License

MIT
