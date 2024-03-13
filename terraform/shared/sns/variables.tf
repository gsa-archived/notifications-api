variable "cf_org_name" {
  type        = string
  description = "cloud.gov organization name"
}

variable "cf_space_name" {
  type        = string
  description = "cloud.gov space name (staging or prod)"
}

variable "name" {
  type        = string
  description = "name of the service instance"
}

variable "aws_region" {
  type        = string
  description = "AWS region the SNS settings are set in"
}

variable "monthly_spend_limit" {
  type        = number
  description = "SMS budget limit in USD. Support request must be made before raising above 1"
}

variable "delete_recursive_allowed" {
  type        = bool
  default     = true
  description = "Flag for allowing resources to be recursively deleted - not recommended in production environments"
}

variable "allow_ssh" {
  type        = bool
  default     = true
  description = "Flag for allowing SSH access in a space - not recommended in production environments"
}
