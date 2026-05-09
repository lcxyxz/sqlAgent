# src/schema_loader.py
import pymysql
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

class PostgresSchemaLoader(BaseSchemaLoader):
    def load_tables(self) -> Dict[str, Any]:
        cursor = self.conn.cursor()
        try:
            cursor.execute("""
                SELECT tablename, obj_description((schemaname || '.' || tablename)::regclass, 'pg_class') as comment
                FROM pg_tables
                WHERE schemaname = 'public'
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
    
    # ... 实现 load_columns 和 load_relationships ...