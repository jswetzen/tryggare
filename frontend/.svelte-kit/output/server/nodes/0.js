import * as server from '../entries/pages/_layout.server.ts.js';

export const index = 0;
let component_cache;
export const component = async () => component_cache ??= (await import('../entries/pages/_layout.svelte.js')).default;
export { server };
export const server_id = "src/routes/+layout.server.ts";
export const imports = ["_app/immutable/nodes/0.BwkcDnFE.js","_app/immutable/chunks/ClEK_bS3.js","_app/immutable/chunks/CHAnh0Qe.js","_app/immutable/chunks/BahgTxaX.js","_app/immutable/chunks/DeQ8RDkx.js","_app/immutable/chunks/jKjWACjA.js","_app/immutable/chunks/CL-aOwLp.js","_app/immutable/chunks/Pupr50YX.js","_app/immutable/chunks/D7zBtH40.js","_app/immutable/chunks/oYpBe7jk.js","_app/immutable/chunks/Be6DjPqX.js","_app/immutable/chunks/DTYrHwOH.js","_app/immutable/chunks/oPsnH_Ep.js","_app/immutable/chunks/Dx9Yy79m.js"];
export const stylesheets = ["_app/immutable/assets/0.DJAJNnHR.css"];
export const fonts = [];
