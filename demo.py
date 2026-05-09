import logging
import os
from dotenv import load_dotenv
from src import NL2SQLAgent

# 加载 .env 文件
load_dotenv()

# 配置日志系统
logging.basicConfig(
    level=logging.INFO,  # 设置日志级别：DEBUG < INFO < WARNING < ERROR < CRITICAL
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[
        logging.StreamHandler(), # 输出到控制台
        logging.FileHandler('./logs/app.log', encoding='utf-8')  # 输出到文件
    ]
)

# 从环境变量读取数据库配置
db_config = {
    "provider": os.getenv("DB_PROVIDER", "mysql"),
    "host": os.getenv("DB_HOST", "localhost"),
    "port": int(os.getenv("DB_PORT", "3306")),
    "user": os.getenv("DB_USER", "root"),
    "password": os.getenv("DB_PASSWORD", ""),
    "database": os.getenv("DB_DATABASE", "test")
}

# 从环境变量读取LLM配置
llm_config = {
    "api_key": os.getenv("LLM_API_KEY", ""),
    "model": os.getenv("LLM_MODEL", "gpt-3.5-turbo"),
    "base_url": os.getenv("LLM_BASE_URL", ""),
    "temperature": float(os.getenv("LLM_TEMPERATURE", "0.0")),
    "max_tokens": int(os.getenv("LLM_MAX_TOKENS", "2000")),
    "timeout": int(os.getenv("LLM_TIMEOUT", "60"))
}

agent = NL2SQLAgent(db_config=db_config, llm_config=llm_config)

logger = logging.getLogger(__name__)

result = agent.query("查询一下张三买的所有商品")

if result['success']:
    logger.info("执行的sql语句：%s",result['sql'])
    logger.info("结果为：%s",result['results'])
    logger.info("显示的列为：%s",result['columns'])
    logger.info("总记录数为：%s",result['row_count'])
else:
    logger.error("发生了错误：%s",result['error'])