# src/schema_loader.py
import sqlite3
from typing import Dict, Any, List
from logging import getLogger

logger = getLogger(__name__)

class BaseSchemaLoader:
    """Schema 加载器基类"""
    def __init__(self, connection):
        self.conn = connection

    def load_tables(self) -> Dict[str, Any]:
        raise NotImplementedError

    def load_columns(self, tables: Dict[str, Any]) -> Dict[str, Any]:
        raise NotImplementedError

    def load_relationships(self) -> List[Dict[str, str]]:
        raise NotImplementedError

    def load_full_schema(self) -> Dict[str, Any]:
        """加载完整 Schema"""
        tables = self.load_tables()
        tables = self.load_columns(tables)
        relationships = self.load_relationships()
        return {
            'tables': tables,
            'relationships': relationships
        }

class MySQLSchemaLoader(BaseSchemaLoader):
    """MySQL Schema 加载器"""
    def load_tables(self) -> Dict[str, Any]:
        cursor = self.conn.cursor()
        try:
            cursor.execute("""
                SELECT TABLE_NAME, TABLE_COMMENT
                FROM INFORMATION_SCHEMA.TABLES
                WHERE TABLE_SCHEMA = DATABASE() AND TABLE_TYPE = 'BASE TABLE'
            """)
            tables = {}
            for table_name, comment in cursor.fetchall():
                tables[table_name] = {
                    'columns': {},
                    'description': comment or table_name
                }
            return tables
        finally:
            cursor.close()

    def load_columns(self, tables: Dict[str, Any]) -> Dict[str, Any]:
        cursor = self.conn.cursor()
        try:
            cursor.execute("""
                SELECT TABLE_NAME, COLUMN_NAME, DATA_TYPE, IS_NULLABLE, COLUMN_KEY, COLUMN_COMMENT
                FROM INFORMATION_SCHEMA.COLUMNS
                WHERE TABLE_SCHEMA = DATABASE()
                ORDER BY TABLE_NAME, ORDINAL_POSITION
            """)
            for table_name, col_name, data_type, nullable, col_key, comment in cursor.fetchall():
                if table_name in tables:
                    tables[table_name]['columns'][col_name] = {
                        'type': data_type.upper(),
                        'nullable': nullable == 'YES',
                        'primary_key': col_key == 'PRI',
                        'description': comment or col_name
                    }
            return tables
        finally:
            cursor.close()

    def load_relationships(self) -> List[Dict[str, str]]:
        cursor = self.conn.cursor()
        try:
            cursor.execute("""
                SELECT TABLE_NAME, COLUMN_NAME, REFERENCED_TABLE_NAME, REFERENCED_COLUMN_NAME
                FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE
                WHERE TABLE_SCHEMA = DATABASE() AND REFERENCED_TABLE_NAME IS NOT NULL
            """)
            relationships = []
            for table_name, col_name, ref_table, ref_col in cursor.fetchall():
                relationships.append({
                    'from': f"{table_name}.{col_name}",
                    'to': f"{ref_table}.{ref_col}"
                })
            return relationships
        finally:
            cursor.close()

class SQLiteSchemaLoader(BaseSchemaLoader):
    """SQLite Schema 加载器"""

    def load_tables(self) -> Dict[str, Any]:
        """加载所有表的基本信息"""
        cursor = self.conn.cursor()
        try:
            # 从 sqlite_master 获取所有用户表
            cursor.execute("""
                SELECT name 
                FROM sqlite_master 
                WHERE type='table' AND name NOT LIKE 'sqlite_%'
                ORDER BY name
            """)
            tables = {}
            for (table_name,) in cursor.fetchall():
                # SQLite 原生不支持表注释，使用表名作为描述
                tables[table_name] = {
                    'columns': {},
                    'description': table_name
                }
            logger.info("已加载 %d 个表", len(tables))
            return tables
        except Exception as e:
            logger.error("加载表信息失败: %s", str(e))
            raise
        finally:
            cursor.close()

    def load_columns(self, tables: Dict[str, Any]) -> Dict[str, Any]:
        """加载每个表的列信息"""
        cursor = self.conn.cursor()
        try:
            for table_name in tables.keys():
                # 使用 PRAGMA table_info 获取列信息
                cursor.execute(f"PRAGMA table_info('{table_name}')")
                columns_info = cursor.fetchall()
                
                for col in columns_info:
                    # PRAGMA table_info 返回: (cid, name, type, notnull, dflt_value, pk)
                    cid, col_name, data_type, not_null, default_value, is_pk = col
                    
                    tables[table_name]['columns'][col_name] = {
                        'type': data_type.upper() if data_type else 'TEXT',
                        'nullable': not bool(not_null),
                        'primary_key': bool(is_pk),
                        'description': col_name,
                        'default': default_value
                    }
            
            logger.info("已加载所有表的列信息")
            return tables
        except Exception as e:
            logger.error("加载列信息失败: %s", str(e))
            raise
        finally:
            cursor.close()

    def load_relationships(self) -> List[Dict[str, str]]:
        """加载外键关系"""
        cursor = self.conn.cursor()
        try:
            relationships = []
            
            # 遍历所有表，获取外键信息
            cursor.execute("""
                SELECT name 
                FROM sqlite_master 
                WHERE type='table' AND name NOT LIKE 'sqlite_%'
            """)
            tables = [row[0] for row in cursor.fetchall()]
            
            for table_name in tables:
                # 使用 PRAGMA foreign_key_list 获取外键
                cursor.execute(f"PRAGMA foreign_key_list('{table_name}')")
                fk_info = cursor.fetchall()
                
                for fk in fk_info:
                    # PRAGMA foreign_key_list 返回:
                    # (id, seq, table, from, to, on_update, on_delete, match)
                    fk_id, seq, ref_table, from_col, to_col, on_update, on_delete, match = fk
                    
                    relationships.append({
                        'from': f"{table_name}.{from_col}",
                        'to': f"{ref_table}.{to_col}"
                    })
            
            logger.info("已加载 %d 个外键关系", len(relationships))
            return relationships
        except Exception as e:
            logger.error("加载外键关系失败: %s", str(e))
            raise
        finally:
            cursor.close()


class PostgresSchemaLoader(BaseSchemaLoader):
    """PostgreSQL Schema 加载器"""
    pass



