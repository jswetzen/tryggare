import { apiClient } from './client';
import type { DiscoverPrefixesResponse, EventImportConfig, ImportRun } from './types';

export const importApi = {
  discoverPrefixes: (jsonData: unknown): Promise<DiscoverPrefixesResponse> =>
    apiClient.post('/imports/discover-prefixes/', { json_data: jsonData }),

  getConfig: (eventId: string): Promise<EventImportConfig> =>
    apiClient.get(`/imports/events/${eventId}/config/`),

  runImport: (
    eventId: string,
    jsonData: unknown,
    fieldMappings: Record<string, string>,
    sourceFileName: string
  ): Promise<ImportRun> =>
    apiClient.post(`/imports/events/${eventId}/run/`, {
      json_data: jsonData,
      field_mappings: fieldMappings,
      source_file_name: sourceFileName,
    }),

  getHistory: (eventId: string): Promise<ImportRun[]> =>
    apiClient.get(`/imports/events/${eventId}/history/`),
};
