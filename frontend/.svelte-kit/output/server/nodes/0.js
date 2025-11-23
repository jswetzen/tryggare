

export const index = 0;
let component_cache;
export const component = async () => component_cache ??= (await import('../entries/pages/_layout.svelte.js')).default;
export const imports = ["_app/immutable/nodes/0.th7AglwJ.js","_app/immutable/chunks/CWs93j59.js","_app/immutable/chunks/BPV49JXs.js","_app/immutable/chunks/SLwYZtPo.js"];
export const stylesheets = ["_app/immutable/assets/0.BJpPh3MV.css"];
export const fonts = [];
