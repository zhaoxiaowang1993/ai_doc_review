data "azurerm_subscription" "primary" {}

data "azurerm_client_config" "current" {}

data "azurerm_cosmosdb_sql_role_definition" "data_contributor" {
  resource_group_name = azurerm_resource_group.main.name
  account_name        = azurerm_cosmosdb_account.main.name
  # Cosmos Data Contributor built-in role ID
  role_definition_id = "00000000-0000-0000-0000-000000000002"
}

data "azapi_resource_list" "ai_services" {
  type      = "Microsoft.CognitiveServices/deletedAccounts@2024-10-01"
  parent_id = data.azurerm_subscription.primary.id
}

data "azuread_application_published_app_ids" "well_known" {}
