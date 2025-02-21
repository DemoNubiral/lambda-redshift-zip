import os
import re

def parse_env_file():

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
        print(create_schema_name)



parse_env_file()