

export const index = 0;
let component_cache;
export const component = async () => component_cache ??= (await import('../entries/pages/_layout.svelte.js')).default;
export const universal = {
  "ssr": false,
  "prerender": false,
  "load": null
};
export const universal_id = "src/routes/+layout.ts";
export const imports = ["_app/immutable/nodes/0.CGQGM0Ye.js","_app/immutable/chunks/BlmT29IN.js","_app/immutable/chunks/BmRUTw-1.js","_app/immutable/chunks/CMdyHIyL.js","_app/immutable/chunks/DIeogL5L.js","_app/immutable/chunks/Dt9VRRxM.js","_app/immutable/chunks/B9ZrYRGI.js","_app/immutable/chunks/LUIbBGDu.js","_app/immutable/chunks/CWj6FrbW.js","_app/immutable/chunks/BtHQo87A.js","_app/immutable/chunks/DQ3q3nkm.js","_app/immutable/chunks/C1FmrZbK.js","_app/immutable/chunks/DkGn2Mjj.js","_app/immutable/chunks/DC07jX_I.js","_app/immutable/chunks/BiYAUeOk.js","_app/immutable/chunks/iPCFofof.js","_app/immutable/chunks/D1sZ1ziQ.js","_app/immutable/chunks/69_IOA4Y.js","_app/immutable/chunks/DIFkoK8U.js","_app/immutable/chunks/1CqQ3_fd.js"];
export const stylesheets = ["_app/immutable/assets/0.Cha86fW9.css"];
export const fonts = [];
