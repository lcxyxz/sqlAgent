# SqlAgent - 自然语言转SQL智能查询系统


## 📖 项目简介

**SqlAgent** 是一个基于大语言模型（LLM）的智能自然语言转SQL系统，旨在降低数据库查询门槛，让非技术人员也能通过日常语言轻松查询数据库。只需输入自然语言问题，系统即可自动转换为准确的SQL查询语句并返回结果。

### ✨ 核心特性

- 🎯 **自然语言转SQL**：将用户问题自动转换为正确的SQL查询语句
- 🔒 **安全可靠**：仅允许SELECT查询，内置多重SQL安全校验机制
- 🗄️ **多数据库支持**：(目前仅支持MySQL数据库)
- 🔄 **Schema自动加载**：从数据库元数据自动加载表结构和关系信息
- 💬 **上下文感知**：基于完整数据库Schema生成精准的SQL查询
- ⚡ **高性能连接池**：使用DBUtils连接池管理，提升并发性能
- 📊 **结果解释**：结构化返回查询结果，便于后续处理
- 🛠️ **模块化设计**：易于扩展新数据库类型或LLM提供商


## 🚀 快速开始

### 环境要求

- Python 3.10+
- OpenAI兼容的LLM API（如OpenAI、通义千问、DeepSeek等）

### 安装步骤

1. **克隆项目**
```bash
git clone https://github.com/your-repo/SqlAgent.git
cd SqlAgent
```

2. **安装依赖**
```bash
pip install -r requirements.txt
```

3. **配置环境变量**
```
将.env.example改名为.env，并填写自己的配置信息
```


### 基本使用

#### 运行demo.py

```python
    python demo.py
```

运行结果示例：<img src="./img/image.png" width="800">

## 📋 功能详解

### 1. 数据库Schema自动加载

系统会自动从数据库的 `INFORMATION_SCHEMA` 中加载：
- 表名和表注释
- 列名、数据类型、主键信息
- 外键关系映射

支持的数据库类型：
- ✅ MySQL（已实现）
- 后续会实现更多数据库

### 2. SQL生成流程

1. **Schema格式化**：将数据库结构转换为LLM可读的文本格式
2. **Prompt构建**：结合用户问题和Schema信息构建提示词
3. **LLM调用**：调用大语言模型生成SQL语句
4. **SQL提取**：从LLM响应中提取合法的SQL语句
5. **安全校验**：验证SQL合法性（仅允许SELECT）
6. **执行查询**：通过连接池执行SQL并返回结果

### 3. 安全机制

- ✅ 仅允许SELECT查询
- ❌ 禁止DROP、TRUNCATE、DELETE、UPDATE等危险操作
- 🔍 SQL语法校验
- ⏱️ 查询超时控制
- 📊 结果集大小限制

### 4. 连接池配置

系统使用 `DBUtils.PooledDB` 实现数据库连接池：

```python
PooledDB(
    creator=pymysql,
    maxconnections=10,   # 最大连接数
    mincached=2,         # 初始化空闲连接数
    maxcached=5,         # 最大闲置连接数
    maxusage=100,        # 单连接最大使用次数
    ping=1,              # 使用前检查连接状态
    blocking=True,       # 连接满时阻塞等待
    reset_session=True   # 归还连接时重置会话
)
```

## 📁 项目结构

```
SqlAgent/
├── src/                          # 源代码目录
│   ├── __init__.py               # 模块初始化
│   ├── nl2sql_agent.py           # 核心Agent类
│   ├── schema.py                 # Schema数据模型
│   ├── schema_loader.py          # Schema加载器
│   └── prompts/                  # Prompt模板目录
│       └── mysql.txt             # MySQL专用Prompt
├── logs/                         # 日志目录
├── requirements.txt              # Python依赖
└── README.md                     # 项目说明
```


## 🛡️ 注意事项

1. **API密钥安全**：不要将API密钥硬编码在代码中，建议使用环境变量或配置文件
2. **数据库权限**：确保数据库用户具有读取 `INFORMATION_SCHEMA` 和执行SELECT的权限
3. **LLM选择**：推荐使用支持中文理解能力强的模型（如通义千问、GPT-4等）
4. **Schema更新**：当数据库结构变更时，需要重新初始化Agent以加载最新Schema
5. **查询复杂度**：过于复杂的自然语言问题可能影响SQL生成准确率，建议优化提问方式

## 上进心
本项目后续会支持更多的厂商。

## 🤝 贡献指南

欢迎提交Issue和Pull Request！

## 📄 许可证

本项目采用MIT许可证

## 🙏 致谢

- [OpenAI](https://openai.com/) - 提供强大的LLM能力
- [DBUtils](https://webwareforpython.github.io/DBUtils/) - 数据库连接池管理
- [PyMySQL](https://github.com/PyMySQL/PyMySQL) - MySQL数据库驱动
- [Pydantic](https://docs.pydantic.dev/) - 数据验证和序列化


## 📧 联系方式

如有问题或建议，请通过以下方式联系：
- 提交Issue
- 发送邮件至：1148656615@qq.com

---

⭐ 如果这个项目对你有帮助，请给个Star支持一下！
