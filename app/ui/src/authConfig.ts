import { InteractionType, RedirectRequest, type Configuration } from '@azure/msal-browser'

export const msalConfig: Configuration = {
  auth: {
    clientId: import.meta.env.VITE_CLIENT_ID!,
    authority: `https://login.microsoftonline.com/${import.meta.env.VITE_TENANT_ID!}`,
    redirectUri: '/',
    postLogoutRedirectUri: '/logged-out'
  },
  cache: {
    cacheLocation: 'localStorage',
    storeAuthStateInCookie: false
  }
}

// add scopes here to get consent on initial login - referenced in <MsalAuthenticationTemplate> - App.tsx
export const loginRequest: RedirectRequest = {
  scopes: ['user.read', 'openid', 'profile', 'https://storage.azure.com/user_impersonation']
}

export const interactionType = InteractionType.Redirect

export const accessTokenRequest = {
  scopes: [import.meta.env.VITE_API_SCOPE!]
}
