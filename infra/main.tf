

module "lambda" {
  source = "./lambda_data"
  service_lambda = var.service_lambda
  output_folder = var.output_folder
  # type_folder = var.type_folder
  # output_zip_layer = var.output_zip_layer
}

