## Variables

variable "service_lambda" {
  description = "list of paramerters for lambda function"
  type        = list(map(string))
  default = []
}

variable "output_folder" {
  type = string
}

# variable "source_file" {
#   type = string
# }

# variable "type_folder" {
#   type = string
# }

# variable "output_zip_layer" {
#   type = string
# }
