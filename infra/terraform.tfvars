service_lambda = [ {
    "lambda_function_name" = "redshift_lambda",
    "lambda_role_arn" = "arn:aws:iam::015319782619:role/github-assume-role",
    "lambda_handler" = "code-create-tables.main",
    "lambda_runtime" = "python3.11",
    "lambda_memory_size" = 256,
    "lambda_timeout" = 300,
    "architectures" = "x86_64",
    "use_vpc" = true,
    "security_group_ids" = "sg-0ceed711bd13edba1",
    "REGION" = "us-east-1",
    "BUCKET_NAME" = "claro-cenam",
    "REDSHIFT_DB" = "kopiclouddb",
    "REDSHIFT_USER" = "kopiadmin",
    "REDSHIFT_PASSWORD" = "M3ss1G0at10",
    "REDSHIFT_HOST" = "kopicloud-workgroup.015319782619.us-east-1.redshift-serverless.amazonaws.com",
    "REDSHIFT_PORT" = "5439",
    "WORKGROUP_NAME" = "kopicloud-workgroup"
} ]

output_folder = "../code/lambda-code-redshift-db.zip"
# source_file = "../code/code-create-tables.py"
# type_folder = "zip"

# output_zip_layer = "../code/zip/lambda-layer-redshift.zip"
# path_folder_layer = "../code/layer/"


aws_region = "us-east-1"