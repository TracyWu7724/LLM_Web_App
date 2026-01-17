"""Simple cache service stub - caching disabled"""

class CacheService:
    """Stub cache service that doesn't actually cache anything"""

    def get_query_result(self, query, limit=None):
        """Returns None - no cached result"""
        return None

    def set_query_result(self, query, result, limit=None, ttl=None):
        """No-op - doesn't cache"""
        pass

    def get_table_list(self, include_sql_server=False):
        """Returns None - no cached table list"""
        return None

    def set_table_list(self, tables, include_sql_server=False, ttl=None):
        """No-op - doesn't cache"""
        pass

    def get_table_schema(self, table_name):
        """Returns None - no cached schema"""
        return None

    def set_table_schema(self, table_name, schema, ttl=None):
        """No-op - doesn't cache"""
        pass

# Global cache instance
db_cache = CacheService()
