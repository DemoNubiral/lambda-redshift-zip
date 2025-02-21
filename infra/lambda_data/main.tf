
data "aws_caller_identity" "current" {}
## 
locals {
  unique_id = substr(md5("lambda-redhshift-${data.aws_caller_identity.current.account_id}"), 0, 8)
}

## Crear la función Lambda
resource "aws_lambda_function" "lambda_function" {
  for_each = {for lambda in var.service_lambda : lambda.lambda_function_name => lambda}
  function_name = each.value.lambda_function_name
  role          = aws_iam_role.lambda_execution_role.arn
  handler       = each.value.lambda_handler
  runtime       = each.value.lambda_runtime
  memory_size   = each.value.lambda_memory_size
  timeout       = each.value.lambda_timeout 
  architectures = [each.value.architectures]

  # Usar el archivo ZIP generado dentro de S3
  filename      = var.output_folder
  dynamic "vpc_config" {
    for_each = each.value.use_vpc ? [1] : []
    content {
      subnet_ids         = ["subnet-014ad9617871f211a",
                    "subnet-0d6ffcd4014593b3d",
                    "subnet-0a8f76b3bd83d543d",
                    "subnet-004c47931f19176d5",
                    "subnet-04945d72e1d6eb168",
                    "subnet-0fcd712221e4a986a",
                    "subnet-0f8160e82a9fed6af",
                    "subnet-0ff6020b3414b37f7"]
      security_group_ids = [each.value.security_group_ids]
    }
  }

  environment {
    variables = {
      REGION              = each.value.REGION
      BUCKET_NAME         = each.value.BUCKET_NAME
      REDSHIFT_DB         = each.value.REDSHIFT_DB
      REDSHIFT_USER       = each.value.REDSHIFT_USER
      REDSHIFT_PASSWORD   = each.value.REDSHIFT_PASSWORD
      REDSHIFT_HOST       = each.value.REDSHIFT_HOST
      REDSHIFT_PORT       = each.value.REDSHIFT_PORT
      WORKGROUP_NAME      = each.value.WORKGROUP_NAME
    }
  }

  depends_on = [
    aws_iam_role_policy.lambda_policy
  ]

  tags = {
    Name      = "${each.value.lambda_function_name}-redshift-${local.unique_id}"
  }


}

## Role y Política de permisos para Lambda
resource "aws_iam_role" "lambda_execution_role" {
  ##name = replace("${var.Environment}-lambda-execution-role", "/[^a-zA-Z0-9+=,.@_-]/", "-")
  name = "lambda-execution-role-redshift-${local.unique_id}"

  assume_role_policy = jsonencode({
    Version = "2012-10-17",
    Statement = [{
      Action = "sts:AssumeRole",
      Effect = "Allow",
      Principal = {
        Service = "lambda.amazonaws.com"
      }
    }]
  })
}


resource "aws_iam_role_policy" "lambda_policy" {
  name   = "lambda-policy-redshift-${local.unique_id}"
  role   = aws_iam_role.lambda_execution_role.id

  policy = jsonencode({
    Version: "2012-10-17",
    Statement: [
      {
        Action: "*",
        Effect: "Allow",
        Resource: "*"
      }
      ,{
        Sid: "LambdaLogging",
        Action: [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ],
        Effect: "Allow",
        Resource: "arn:aws:logs:*:*:*"
      },

      {
        Sid: "Invokelambda",
        Action: [
          "lambda:InvokeFunction"
        ],
        Effect: "Allow",
        Resource: "arn:aws:lambda:*:*:function:*"
      },
      {
        Sid: "AssignNetwork",
        Action: [
          "ec2:CreateNetworkInterface",
          "ec2:DescribeNetworkInterfaces",
          "ec2:DeleteNetworkInterface",
          "ec2:AssignPrivateIpAddresses",
          "ec2:UnassignPrivateIpAddresses"
        ],
        Effect: "Allow",
        Resource: "*"
      }
    ]
  })
}



