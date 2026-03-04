import { apiClient } from './client';
import type {
  DiscoverPrefixesResponse,
  EventImportConfig,
  ImportProvider,
  ImportProviderWrite,
  ImportRun,
} from './types';

export const importApi = {
  discoverPrefixes: (jsonString: string): Promise<DiscoverPrefixesResponse> =>
    apiClient.post('/imports/discover-prefixes/', { json_string: jsonString }),

  getConfig: (eventId: string): Promise<EventImportConfig> =>
    apiClient.get(`/imports/events/${eventId}/config/`),

  runImport: (
    eventId: string,
    jsonString: string,
    fieldMappings: Record<string, string>,
    sourceFileName: string
  ): Promise<ImportRun> =>
    apiClient.post(`/imports/events/${eventId}/run/`, {
      json_string: jsonString,
      field_mappings: fieldMappings,
      source_file_name: sourceFileName,
    }),

  // Run without json_string — server-side auto-fetch from linked provider
  runImportAutoFetch: (
    eventId: string,
    fieldMappings: Record<string, string>
  ): Promise<ImportRun> =>
    apiClient.post(`/imports/events/${eventId}/run/`, {
      field_mappings: fieldMappings,
    }),

  getHistory: (eventId: string): Promise<ImportRun[]> =>
    apiClient.get(`/imports/events/${eventId}/history/`),

  // Provider CRUD
  listProviders: (): Promise<ImportProvider[]> =>
    apiClient.get('/imports/providers/'),

  createProvider: (data: ImportProviderWrite): Promise<ImportProvider> =>
    apiClient.post('/imports/providers/', data),

  updateProvider: (id: string, data: ImportProviderWrite): Promise<ImportProvider> =>
    apiClient.put(`/imports/providers/${id}/`, data),

  deleteProvider: (id: string): Promise<void> =>
    apiClient.delete(`/imports/providers/${id}/`),

  getProvider: (id: string): Promise<ImportProvider> =>
    apiClient.get(`/imports/providers/${id}/`),

  setConfigProvider: (eventId: string, providerId: string | null): Promise<EventImportConfig> =>
    apiClient.patch(`/imports/events/${eventId}/config/provider/`, { provider_id: providerId }),

  // Discover prefixes via provider live-fetch (for first-time mapping)
  discoverPrefixesFromProvider: (eventId: string): Promise<DiscoverPrefixesResponse> =>
    apiClient.post(`/imports/events/${eventId}/discover-prefixes/`),
};
