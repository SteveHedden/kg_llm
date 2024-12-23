from databricks import sql
from config import DATABRICKS_SERVER_HOSTNAME, DATABRICKS_ACCESS_TOKEN

def query_databricks(query):
    connection = sql.connect(
        server_hostname=DATABRICKS_SERVER_HOSTNAME,
        http_path="/sql/1.0/warehouses/your-warehouse-id",
        access_token=DATABRICKS_ACCESS_TOKEN,
    )
    try:
        with connection.cursor() as cursor:
            cursor.execute(query)
            results = cursor.fetchall()
        return results
    finally:
        connection.close()
