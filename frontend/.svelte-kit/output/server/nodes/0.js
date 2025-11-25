import * as server from '../entries/pages/_layout.server.ts.js';

export const index = 0;
let component_cache;
export const component = async () => component_cache ??= (await import('../entries/pages/_layout.svelte.js')).default;
export { server };
export const server_id = "src/routes/+layout.server.ts";
export const imports = ["_app/immutable/nodes/0.8f2pTsx-.js","_app/immutable/chunks/CWj6FrbW.js","_app/immutable/chunks/0C_mT4e3.js","_app/immutable/chunks/Dd6hwy8F.js","_app/immutable/chunks/HLA8ReXw.js"];
export const stylesheets = ["_app/immutable/assets/0.D_TFVojf.css"];
export const fonts = [];
