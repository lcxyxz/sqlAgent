"""
NL2SQL Agent
"""
import textwrap
from .schema_loader import BaseSchemaLoader,MySQLSchemaLoader,SQLiteSchemaLoader
from .schema import SchemaModel
import os
import time
from typing import Dict, Any, List, Optional
from logging import getLogger
from dbutils.pooled_db import PooledDB
import pymysql
# 创建模块级别的日志记录器
logger = getLogger(__name__)


class NL2SQLAgent:
    """NL2SQL Agent"""
    def __init__(self, db_config: Dict[str, Any], llm_config: Dict[str, Any] = None):
        """初始化NL2SQLAgent
        Args:
            db_config (Dict[str, Any]): 数据库配置
            llm_config (Dict[str, Any], optional): LLM配置. Defaults to None.
            db_type (str): 数据库类型, e.g., 'mysql', 'postgres'. Defaults to 'mysql'.
        """
        try:
            self.db_config = db_config
            logger.info("初始化 NL2SQL Agent, 数据库类型: %s", self.db_config["provider"])
            self.pool = self._get_database_pool()
            self.llm_config = llm_config
            self.schema = {}
            self._load_schema_from_db()
            self.client = None
            self._init_llm_client()
            self.prompt = textwrap.dedent(self._get_prompt_template())
            logger.info("NL2SQL Agent 初始化完成")
        except Exception as e:
            logger.error("初始化 NL2SQL Agent 失败: %s", e)
            raise e

    def _init_llm_client(self):
        """初始化OpenAI客户端"""
        logger.info("初始化 OpenAI 客户端，模型: %s", self.llm_config.get('model', 'unknown'))
        try:
            from openai import OpenAI
            self.client = OpenAI(
                api_key=self.llm_config['api_key'],
                base_url=self.llm_config.get('base_url', 'https://api.openai.com/v1'),
            )
            logger.debug("OpenAI 客户端初始化成功")
        except ImportError:
            logger.error("openai 库未安装")
            raise ImportError("请安装 openai: pip install openai")

    def _load_schema_from_db(self):
        """从数据库加载Schema
        """
        logger.info("开始从数据库 [%s] 加载 schema", self.db_config['provider'])
        conn = self.pool.connection()
        try:
            loader = self._get_schema_loader(conn)
            raw_schema = loader.load_full_schema()
            validated_schema = SchemaModel(**raw_schema)
            # 将验证后的Schema保存到self.schema
            self.schema = validated_schema.model_dump(by_alias=True)
        except Exception as e:
            logger.error("加载 Schema 失败: %s", str(e))
            raise e
        finally:
            conn.close()
    def _get_schema_loader(self, conn) -> BaseSchemaLoader:
        """根据数据库类型获取对应的 Schema Loader"""
        if self.db_config["provider"] == 'mysql':
            return MySQLSchemaLoader(conn)
        elif self.db_config["provider"] == 'sqlite':
            return SQLiteSchemaLoader(conn)
        else:
            raise ValueError(f"不支持的数据库类型: {self.db_config['provider']}")
    def _format_schema(self) -> str:
        """格式化Schema为文本"""
        lines = []
        for table_name, table_info in self.schema['tables'].items():
            lines.append(f"\n表名: {table_name} ({table_info['description']})")
            lines.append("列信息:")
            for col_name, col_info in table_info['columns'].items():
                pk = ' [主键]' if col_info['primary_key'] else ''
                lines.append(f"  - {col_name}: {col_info['type']}{pk} ({col_info['description']})")
        return '\n'.join(lines)

    def _get_prompt_template(self) -> str:
        """获取提示词模板
        """
        prompt_path = os.path.join(os.path.dirname(__file__),'prompts', 'mysql.txt')
        with open(prompt_path, 'r', encoding='utf-8') as f:
            return f.read()

    def _build_prompt(self, question: str) -> str:
        """构建Prompt"""
        schema_info = self._format_schema()
        try:
            return self.prompt.format(schema=schema_info, question=question)
        except KeyError as e:
            logger.error("Prompt 模板缺少变量: %s", e)
            raise

    def _extract_sql(self, response: str) -> Optional[str]:
        """从LLM响应提取SQL
        Args:
            response (str): LLM的原始响应
            
        Returns:
            Optional[str]: 合法的SQL语句，如果无法提取或非法则返回None
        """
        if not response:
            return None
            
        # 1. 预处理：去除首尾空白
        cleaned_response = response.strip()
        
        # 2. 快速失败：如果包含明确的错误提示，直接返回 None
        if "无法查询" in cleaned_response:
            return None

        # 3. 尝试提取 SQL
        # 查找 SELECT 关键字的位置 (忽略大小写)
        select_idx = cleaned_response.upper().find('SELECT')
        
        if select_idx == -1:
            return None
        
        # 从 SELECT 开始截取剩余部分
        potential_sql = cleaned_response[select_idx:]
        
        # 4. 确定结束位置
        # 优先寻找分号作为结束符
        semi_colon_idx = potential_sql.find(';')
        potential_sql = potential_sql[:semi_colon_idx]

        # 5. 清理和校验
        final_sql = potential_sql.strip()
        
        # 基本合法性校验：必须包含 SELECT 和 FROM
        sql_upper = final_sql.upper()
        if 'SELECT' not in sql_upper or 'FROM' not in sql_upper:
            return None
            
        # 长度校验：避免过短的无效字符串
        if len(final_sql) < 10:
            return None
            
        # 可选：去除末尾可能的多余标点或空格
        final_sql = final_sql.rstrip(';').strip()
        
        return final_sql

    def _call_llm(self, prompt: str) -> str:
        """调用LLM"""
        logger.debug("调用 LLM，prompt 长度: %d", len(prompt))
        start_time = time.time()
        try:
            response = self.client.chat.completions.create(
                model=self.llm_config['model'],
                messages=[{'role': 'user', 'content': prompt}],
                temperature = self.llm_config.get('temperature', 0.5),
                max_tokens = self.llm_config.get('max_tokens', 1024),
            )
            elapsed = time.time() - start_time
            logger.info("LLM 调用成功，耗时: %.2f秒", elapsed)
            return response.choices[0].message.content
        except Exception as e:
            logger.error("LLM 调用失败: %s", str(e))
            raise

    def _execute_sql(self, sql: str) -> Dict[str, Any]:
        """执行SQL"""
        logger.info("准备执行 SQL: %s", sql[:100] + '...' if len(sql) > 100 else sql)

        start_time = time.time()
        conn = self.pool.connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute(sql)
                columns = [desc[0] for desc in cursor.description] if cursor.description else []
                data = cursor.fetchall()
                return {
                    'success': True,
                    'data': data,
                    'columns': columns,
                    'row_count': len(data),
                    'time': round(time.time() - start_time, 2)
                }
        except Exception as e:
            logger.error("SQL 执行失败: %s", str(e))
            return {'success': False, 'error': str(e)}
        finally:
            conn.close()

    def query(self, question: str) -> Dict[str, Any]:
        """处理用户查询"""
        logger.info("收到查询请求: %s", question)
        try:
            prompt = self._build_prompt(question)
            logger.debug("构建 LLM 提示: %s", prompt)
            llm_response = self._call_llm(prompt)
            logger.debug("LLM 响应: %s", llm_response)
            sql = self._extract_sql(llm_response)
            
            if not sql:
                logger.warning("无法从 LLM 响应中提取 SQL")
                return {'success': False, 'error': '无法提取SQL', 'llm_response': llm_response}

            execution = self._execute_sql(sql)
            if not execution['success']:
                logger.error("SQL 执行失败: %s", execution['error'])
                return {'success': False, 'error': execution['error'], 'sql': sql}
            
            logger.info("查询成功: 返回 %d 条记录，耗时 %.2f秒", 
                       execution['row_count'], execution['time'])

            return {
                'success': True,
                'sql': sql,
                'results': execution['data'],
                'columns': execution['columns'],
                'row_count': execution['row_count'],
                'execution_time': execution['time']
            }

        except Exception as e:
            logger.exception("查询处理过程中发生异常: %s", str(e))
            return {'success': False, 'error': str(e)}

    def _get_database_pool(self):
        """获取相应服务商的数据库连接池
        """
        if self.db_config['provider'] == 'mysql':
            import pymysql
            return PooledDB(
                        creator=pymysql,
                        maxconnections=10,  # 最大连接数
                        mincached=2,        # 初始化时创建的空闲连接数
                        maxcached=5,        # 连接池中最多闲置的连接数
                        maxusage=100,  # 每个连接最多使用100次后自动重建，防止老化
                        ping=1,        # 在使用前检查连接是否存活 (0=不检查, 1=默认检查, 2=获取时检查, 7=总是检查)
                        host=self.db_config.get('host', 'localhost'),
                        port=self.db_config.get('port', 3306),
                        user=self.db_config['user'],
                        password=self.db_config['password'],
                        database=self.db_config['database'],
                        charset=self.db_config.get('charset', 'utf8mb4')
                        )
        elif self.db_config['provider'] == 'sqlite':
            import sqlite3
            return PooledDB(
                        creator=sqlite3,
                        maxconnections=10,  # 最大连接数
                        mincached=2,        # 初始化时创建的空闲连接数
                        maxcached=5,        # 连接池中最多闲置的连接数
                        maxusage=100,  # 每个连接最多使用100次后自动重建，防止老化
                        ping=1,        # 在使用前检查连接是否存活 (0=不检查, 1=默认检查, 2=获取时检查, 7=总是检查)
                        database = self.db_config['sqlite_db_path']
                        )
        else:
            raise ValueError("不支持的数据库服务提供商: %s", self.db_config['provider'])



