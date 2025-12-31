variable "subscription_id" {
  type     = string
  nullable = false
}

variable "name" {
  type     = string
  nullable = false
}

variable "environment" {
  type     = string
  nullable = false
}

variable "location" {
  type     = string
  nullable = false
}

variable "ml_engineers" {
  type        = set(string)
  description = "List of Object IDs for ML engineers (can be single users or group IDs) to add to the Azure AI hub and file share."
  default     = []
}

variable "ai_services_location" {
  type        = string
  description = "Location of the AI Services, where the GPT models are deployed."
  default     = "eastus2"
}

variable "ai_hub_name" {
  type        = string
  description = "Friendly name to apply to the Azure AI hub."
  default     = "AI Document Review"
}

variable "ai_project_name" {
  type        = string
  description = "Friendly name to apply to the Azure AI project."
  default     = "ADR"
}

variable "gpt_model_name" {
  type        = string
  description = "Model name of the GPT 4 model to deploy"
  default     = "gpt-4o"
}

variable "gpt_model_version" {
  type        = string
  description = "Model version of the GPT 4 model to deploy"
  default     = "2024-08-06"
}

variable "gpt_model_capacity" {
  type        = number
  description = "Scale capacity for model (default is 10)"
  default     = 450
}
