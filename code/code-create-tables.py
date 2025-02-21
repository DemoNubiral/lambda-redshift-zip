import boto3
import os
import datetime
import psycopg2
import json
import re
import sys
import logging


client = boto3.client('redshift-data', region_name='us-east-1')
client_s3 = boto3.client('s3')
path_file_process = "redshift-table-process/"
path = os.getcwd()
key_file = "create-table-redshift-log.txt"

"""Logger start"""
logger = logging.getLogger()
logger.setLevel(logging.INFO)
"""Logger end"""


def write_log(file, text, bucket_name):
    try:
        try:
            response = client_s3.get_object(Bucket=bucket_name, Key=file)
            existing_content = response['Body'].read().decode('utf-8')
        except client_s3.exceptions.NoSuchKey:
            existing_content = ""
        
        # Agregar el nuevo log con la fecha y hora
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        new_content = f"{existing_content} \n {timestamp} - {text}\n"
        
        # Subir el archivo actualizado a client_s3
        client_s3.put_object(Bucket=bucket_name, Key=file, Body=new_content)
    except Exception as e:
        print(f"Ocurrió un error: {e}")



def execute_query( query, database, workgroup, bucket_name, key_file, user):
    try:
        write_log(key_file, "execute_query", bucket_name)
        logger.info("execute_query")
        response = client.execute_statement(
            DbUser=user,
            Database=database,
            Sql=query,
            WorkgroupName=workgroup
        )
        logger.info(f"response: {response}, se ejecuta la query de creacion de tabla.")
        write_log(key_file, f"response: {response}, se ejecuta la query de creacion de tabla.", bucket_name)
        return response
    except Exception as e:
        logger.error(f"Ocurrió un error: {e} + {query} + {response}")
        write_log(key_file, f"Ocurrió un error: {e}", bucket_name)
        return {"statusCode": 500, "error": str(e)}


def create_table( table_creation_query, workgroup_name, dbname, bucket_name, key_file, user):
    try:
        write_log(key_file, "create_table", bucket_name)
        logger.info("create_table")
        response = execute_query(table_creation_query, dbname, workgroup_name, bucket_name, key_file, user)
        if response["ResponseMetadata"]["HTTPStatusCode"] == 200:
            logger.info("Se crea la tabla satisfactoriamente")
            write_log(key_file, f"response: {response}, se crea la tabla satisfactoriamente", bucket_name)
            return response
        else: 
            logger.error(f"Falla en la creacion de la tabla: {response}")
            write_log(key_file, f"response: {response}, falla en la creacion de la tabla", bucket_name)
            return {"statusCode": response['statusCode'], "error": str(response)}
    except Exception as e:
        write_log(key_file, f"Ocurrió un error: {e}", bucket_name)
        logger.error(f"Ocurrió un error: {e} + {response}")
        return {"statusCode": 500, "error": str(e)}



def load_table( create_table_redshift, connection, bucket_name, key_file):
    try:
        write_log(key_file, "load_table", bucket_name)        
        logger.info("load_table")
        connection_cursor =connection.cursor()
        copy_sql = f"""
            {create_table_redshift}
        """
        logger.info(f"copy_sql: {copy_sql}")
        write_log(key_file, f"copy_sql: {copy_sql}", bucket_name)
        connection_cursor.execute(copy_sql)
        connection.commit()
        connection_cursor.close()
        connection.close()
        logger.info(f"Carga de tabla exitosa: {copy_sql}")
        write_log(key_file, "Carga de tabla exitosa", bucket_name)
    except Exception as e:
        logger.error(f"Ocurrió un error: {e} + {copy_sql}")
        write_log(key_file, f"Ocurrió un error: {e}", bucket_name)
        print(f"Ocurrió un error: {e}")


def parse_env_file( file_path, connection, workgroup_name, dbname, bucket_name, key_file, user):
    write_log(key_file, "parse_env_file", bucket_name)
    logger.info("parse_env_file")
    for files in file_path:
        data = {}
        current_key = None
        
        with open("redshift-table-process/"+files, 'r', encoding='utf-8') as file:
            for line in file:
                line = line.strip()
                
                if line.startswith('#'):
                    current_key = line[1:]  # Remove '#' from the key
                    data[current_key] = ""
                elif current_key:
                    data[current_key] += line + " "  # Concatenate instead of adding newlines
        
        # Post-process to clean up values
        for key in data:
            data[key] = data[key].replace('"', '').replace("'", '').strip()  # Remove all escaped quotes

        # Extract table name
        table_name_match = re.search(r'name_table=(\w+)', data.get("create_table", ""))
        table_name = table_name_match.group(1) if table_name_match else "unknown_table"
        
        # Extract columns as a structured list
        match = re.search(r'columns=\[(.*?)\]', data.get("create_table", ""))
        columns = []
        if match:
            columns_raw = match.group(1)
            for col in columns_raw.split("},"):
                col = col.replace("{", "").replace("}", "").strip()
                col_data = dict(item.split(": ") for item in col.split(", "))
                columns.append(col_data)

        extract_schema =  re.search(r'schema=(\w+)', data.get("create_table", ""))
        extract_schema_name = extract_schema.group(1) if table_name_match else "unknown_table"    
        
        # Generate CREATE TABLE statement
        create_table_stmt = f"CREATE TABLE IF NOT EXISTS {extract_schema_name}.{table_name} (\n"
        for col in columns:
            col_name = col.get("name_column")
            col_type = col.get("type_column")
            create_table_stmt += f"    {col_name} {col_type},\n"
        create_table_stmt = create_table_stmt.rstrip(",\n") + "\n)"

        load_table_start = data.get("load_table_start", "").strip()
        load_table_stmt = f"{load_table_start}"

        create_schema = data.get("create_schema", "").strip()
        create_schema_name = f"{create_schema}"
        
        if create_schema_name:
            logger.info("Se encontró la sentencia para crear el esquema")
            write_log(key_file, "Se encontró la sentencia para crear el esquema", bucket_name)
            logger.info(f"create_schema: {create_schema_name}")
            write_log(key_file, f"create_schema: {create_schema_name}", bucket_name)
            response = execute_query(create_schema_name, dbname, workgroup_name, bucket_name, key_file, user)
            if response["ResponseMetadata"]["HTTPStatusCode"] != 200:
                logger.error("No se pudo crear el esquema")
                sys.exit("No se pudo crear el esquema")
            else:
                logger.info("Se creó el esquema satisfactoriamente")
                write_log(key_file, "Se creó el esquema satisfactoriamente", bucket_name)
        else:   
            logger.warning("No se encontró la sentencia para crear el esquema")
            write_log(key_file, "No se encontró la sentencia para crear el esquema", bucket_name)

        if create_table_stmt:
            write_log(key_file, "Se encontró la sentencia para crear la tabla", bucket_name)
            logger.info("Se encontró la sentencia para crear la tabla")
            write_log(key_file, f"create_table_stmt: {create_table_stmt}", bucket_name)
            logger.info(f"create_table_stmt: {create_table_stmt}")
            response = create_table(create_table_stmt, workgroup_name, dbname, bucket_name, key_file, user)
            if response["ResponseMetadata"]["HTTPStatusCode"] != 200:
                logger.error("No se pudo crear la tabla")
                sys.exit("No se pudo crear la tabla")
        else:
            logger.warning("No se encontró la sentencia para crear la tabla")
            write_log(key_file, "No se encontró la sentencia para crear la tabla", bucket_name)
        
        
        if load_table_stmt:
            logger.info("Se encontró la sentencia para cargar la tabla")
            write_log(key_file, "Se encontró la sentencia para cargar la tabla", bucket_name)
            logger.info(f"load_table_stmt: {load_table_stmt}")
            write_log(key_file, f"load_table_stmt: {load_table_stmt}", bucket_name)
            load_table(load_table_stmt, connection, bucket_name, key_file)
        else:
            logger.warning("No se encontró la sentencia para cargar la tabla")
            write_log(key_file, "No se encontró la sentencia para cargar la tabla", bucket_name)   



def main(event, context):
    try:
        print("********************************")
        print("se inicia proceso de creación de tablas en redshift")
        print("********************************")
        logger.info("Inicio del proceso de creación de tablas en redshift")
        bucket_name=os.getenv('BUCKET_NAME')
        dbname=os.getenv('REDSHIFT_DB')
        user=os.getenv('REDSHIFT_USER')
        password=os.getenv('REDSHIFT_PASSWORD')
        host=os.getenv('REDSHIFT_HOST')
        port=os.getenv('REDSHIFT_PORT')
        workgroup_name=os.getenv('WORKGROUP_NAME')
        logger.info("Variables de entorno cargadas correctamente")

        write_log(key_file, "Inicio del proceso de creación de tablas en redshift", bucket_name)
        logger.info("Conexión a la base de datos")
        
        connection = psycopg2.connect(
            dbname=dbname,
            user=user,
            password=password,
            host=host,
            port=port
        )

    except Exception as e:
        write_log(key_file, f"Ocurrió un error: {e}", bucket_name)
        logger.error(f"Ocurrió un error: {e}")
        sys.exit("No se pudo establecer conexión con la base de datos")
    else:
        write_log(key_file, "Conexión establecida con la base de datos", bucket_name)
        logger.info("Conexión establecida con la base de datos")

    try:
        files = os.listdir(path_file_process)
        if files:
            logger.info("Se encontraron archivos en el directorio")
            write_log(key_file, f"Se encontraron archivos en el directorio", bucket_name)
            parse_env_file(files, connection, workgroup_name, dbname, bucket_name, key_file, user)  
        else:
            logger.warning("No hay archivos en el directorio")
            write_log(key_file, "No hay archivos en el directorio", bucket_name)
            sys.exit("No hay archivos en el directorio")
            print("********************************")
            print("No hay archivos en el directorio")
            print("********************************")
    except Exception as e:
        write_log(key_file, f"Ocurrió un error: {e}", bucket_name)
        logger.error(f"Ocurrió un error: {e}")
        sys.exit("Ocurrió un error")
    




   