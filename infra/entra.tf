
resource "azuread_service_principal" "msgraph" {
  client_id    = data.azuread_application_published_app_ids.well_known.result.MicrosoftGraph
  use_existing = true
}

resource "azuread_service_principal" "storage" {
  client_id    = data.azuread_application_published_app_ids.well_known.result.AzureStorage
  use_existing = true
}

resource "random_uuid" "api_app_api_scope_id" {}

resource "azuread_application" "api_app" {
  display_name     = local.resource_name.aad_api_app
  owners           = [data.azurerm_client_config.current.object_id]
  identifier_uris  = ["api://adr-api-${var.name}-${var.environment}"]
  sign_in_audience = "AzureADMyOrg"

  required_resource_access {
    resource_app_id = data.azuread_application_published_app_ids.well_known.result.MicrosoftGraph

    resource_access {
      id   = azuread_service_principal.msgraph.oauth2_permission_scope_ids["User.Read"]
      type = "Scope"
    }
  }

  api {
    oauth2_permission_scope {
      admin_consent_description  = "Allow the application to access data on behalf of the signed-in user."
      admin_consent_display_name = "Access Data"
      enabled                    = true
      id                         = random_uuid.api_app_api_scope_id.result
      type                       = "User"
      user_consent_description   = "Allow the application to access data on your behalf."
      user_consent_display_name  = "Access Data"
      value                      = "user_impersonation"
    }
    known_client_applications      = [azuread_application.client_app.client_id]
    requested_access_token_version = 2
  }

  web {
    implicit_grant {
      access_token_issuance_enabled = true
      id_token_issuance_enabled     = true
    }
  }

  single_page_application {
    redirect_uris = [
      "http://localhost:8000/",
      "http://localhost:8000/oauth2-redirect",
      "https://${local.resource_name.web_app}.azurewebsites.net/api",
      "https://${local.resource_name.web_app}.azurewebsites.net/api/oauth2-redirect",
    ]
  }
}

resource "azuread_application" "client_app" {
  display_name     = local.resource_name.aad_client_app
  owners           = [data.azurerm_client_config.current.object_id]
  identifier_uris  = ["api://adr-client-${var.name}-${var.environment}"]
  sign_in_audience = "AzureADMyOrg"

  web {
    implicit_grant {
      access_token_issuance_enabled = true
      id_token_issuance_enabled     = true
    }
  }

  single_page_application {
    redirect_uris = [
      "http://localhost:5173/",
      "https://${local.resource_name.web_app}.azurewebsites.net/"
    ]
  }

  # https://registry.terraform.io/providers/hashicorp/azuread/latest/docs/resources/application_api_access
  # prevent constant changes
  lifecycle {
    ignore_changes = [
      required_resource_access
    ]
  }
}

# Connection from Client -> API App
resource "azuread_application_api_access" "api_connection" {
  application_id = azuread_application.client_app.id
  api_client_id  = azuread_application.api_app.client_id

  scope_ids = [
    azuread_application.api_app.oauth2_permission_scope_ids["user_impersonation"]
  ]
}

# MS Graph API Permissions
resource "azuread_application_api_access" "graph_connection" {
  application_id = azuread_application.client_app.id
  api_client_id  = data.azuread_application_published_app_ids.well_known.result.MicrosoftGraph

  scope_ids = [
    azuread_service_principal.msgraph.oauth2_permission_scope_ids["User.Read"],
    azuread_service_principal.msgraph.oauth2_permission_scope_ids["profile"],
    azuread_service_principal.msgraph.oauth2_permission_scope_ids["openid"],
    azuread_service_principal.msgraph.oauth2_permission_scope_ids["offline_access"]
  ]
}

# Storage user_impersonation
resource "azuread_application_api_access" "storage_user_impersonation" {
  application_id = azuread_application.client_app.id
  api_client_id  = data.azuread_application_published_app_ids.well_known.result.AzureStorage

  scope_ids = [
    azuread_service_principal.storage.oauth2_permission_scope_ids["user_impersonation"]
  ]
}

resource "azuread_service_principal" "api_app" {
  client_id = azuread_application.api_app.client_id
}

resource "azuread_service_principal" "client_app" {
  client_id = azuread_application.client_app.client_id
}
