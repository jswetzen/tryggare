

export const index = 0;
let component_cache;
export const component = async () => component_cache ??= (await import('../entries/pages/_layout.svelte.js')).default;
export const imports = ["_app/immutable/nodes/0.B6oUifS0.js","_app/immutable/chunks/B2QSKqcC.js","_app/immutable/chunks/Cmf9IRo1.js"];
export const stylesheets = ["_app/immutable/assets/0.BJpPh3MV.css"];
export const fonts = [];
