# Client App Vars
output "vite_tenant_id" {
  value = data.azurerm_client_config.current.tenant_id
}

output "vite_client_id" {
  value = azuread_application.client_app.client_id
}

output "vite_api_scope" {
  value = "${tolist(azuread_application.api_app.identifier_uris)[0]}/user_impersonation"
}

output "vite_storage_account" {
  value = azurerm_storage_account.main.primary_blob_endpoint
}

output "vite_storage_document_container" {
  value = azurerm_storage_container.documents.name
}

# API App Vars
output "webapp_name" {
  value = azurerm_linux_web_app.main.name
}

output "webapp_url" {
  value = azurerm_linux_web_app.main.default_hostname
}

output "aad_client_id" {
  value = azuread_application.api_app.client_id
}

output "aad_tenant_id" {
  value = data.azurerm_client_config.current.tenant_id
}

output "cosmos_url" {
  value = azurerm_cosmosdb_account.main.endpoint
}

output "database_name" {
  value = azurerm_cosmosdb_sql_database.state.name
}

output "subscription_id" {
  value = data.azurerm_subscription.primary.subscription_id
}

output "resource_group" {
  value = azurerm_resource_group.main.name
}

output "ai_hub_project_name" {
  value = azapi_resource.ai_project.name
}

output "ai_hub_region" {
  value = azapi_resource.ai_hub.location
}

output "aml_endpoint_name" {
  value = azapi_resource.ai_online_endpoint.name
}

output "document_intelligence_endpoint" {
  value = "https://ais${var.name}${var.environment}.cognitiveservices.azure.com"
}

output "azure_openai_endpoint" {
  value = "https://ais${var.name}${var.environment}.openai.azure.com"
}

output "storage_url_prefix" {
  value = "${azurerm_storage_account.main.primary_blob_endpoint}/${azurerm_storage_container.documents.name}"
}

output "appinsights_instrumentation_key" {
  value     = azurerm_application_insights.main.instrumentation_key
  sensitive = true
}

# Flow vars
output "identity_client_id" {
  value = azurerm_user_assigned_identity.ai_compute.client_id
}
output "identity_resource_id" {
  value = azurerm_user_assigned_identity.ai_compute.id
}
