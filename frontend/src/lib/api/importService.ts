import { apiClient } from './client';
import type {
  DiscoverPrefixesResponse,
  ImportSource,
  ImportSourceWrite,
  ImportRun,
} from './types';

export const importApi = {
  discoverPrefixes: (jsonString: string): Promise<DiscoverPrefixesResponse> =>
    apiClient.post('/imports/discover-prefixes/', { json_string: jsonString }),

  // Source CRUD
  listSources: (): Promise<ImportSource[]> =>
    apiClient.get('/imports/sources/'),

  createSource: (data: ImportSourceWrite): Promise<ImportSource> =>
    apiClient.post('/imports/sources/', data),

  updateSource: (id: string, data: ImportSourceWrite): Promise<ImportSource> =>
    apiClient.put(`/imports/sources/${id}/`, data),

  deleteSource: (id: string): Promise<void> =>
    apiClient.delete(`/imports/sources/${id}/`),

  getSource: (id: string): Promise<ImportSource> =>
    apiClient.get(`/imports/sources/${id}/`),

  // Run import from a source (manual upload)
  runImport: (
    sourceId: string,
    jsonString: string,
    fieldMappings: Record<string, string>,
    sourceFileName: string
  ): Promise<ImportRun> =>
    apiClient.post(`/imports/sources/${sourceId}/run/`, {
      json_string: jsonString,
      field_mappings: fieldMappings,
      source_file_name: sourceFileName,
    }),

  // Run without json_string — server-side auto-fetch from linked provider
  runImportAutoFetch: (
    sourceId: string,
    fieldMappings: Record<string, string>
  ): Promise<ImportRun> =>
    apiClient.post(`/imports/sources/${sourceId}/run/`, {
      field_mappings: fieldMappings,
    }),

  getHistory: (sourceId: string): Promise<ImportRun[]> =>
    apiClient.get(`/imports/sources/${sourceId}/history/`),

  // Discover prefixes via source live-fetch (for first-time mapping)
  discoverPrefixesFromSource: (sourceId: string): Promise<DiscoverPrefixesResponse> =>
    apiClient.post(`/imports/sources/${sourceId}/discover-prefixes/`),
};
