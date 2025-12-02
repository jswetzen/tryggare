export const manifest = (() => {
function __memo(fn) {
	let value;
	return () => value ??= (value = fn());
}

return {
	appDir: "_app",
	appPath: "_app",
	assets: new Set([]),
	mimeTypes: {},
	_: {
		client: {start:"_app/immutable/entry/start.CqmaQQ5H.js",app:"_app/immutable/entry/app.pqidW_38.js",imports:["_app/immutable/entry/start.CqmaQQ5H.js","_app/immutable/chunks/BmRUTw-1.js","_app/immutable/chunks/CMdyHIyL.js","_app/immutable/chunks/DIeogL5L.js","_app/immutable/chunks/Dt9VRRxM.js","_app/immutable/chunks/B9ZrYRGI.js","_app/immutable/chunks/LUIbBGDu.js","_app/immutable/entry/app.pqidW_38.js","_app/immutable/chunks/C1FmrZbK.js","_app/immutable/chunks/CMdyHIyL.js","_app/immutable/chunks/DIeogL5L.js","_app/immutable/chunks/DC07jX_I.js","_app/immutable/chunks/BtHQo87A.js","_app/immutable/chunks/CWj6FrbW.js","_app/immutable/chunks/LUIbBGDu.js","_app/immutable/chunks/DQ3q3nkm.js","_app/immutable/chunks/Dt9VRRxM.js","_app/immutable/chunks/iPCFofof.js"],stylesheets:[],fonts:[],uses_env_dynamic_public:false},
		nodes: [
			__memo(() => import('./nodes/0.js')),
			__memo(() => import('./nodes/1.js')),
			__memo(() => import('./nodes/2.js')),
			__memo(() => import('./nodes/3.js')),
			__memo(() => import('./nodes/4.js')),
			__memo(() => import('./nodes/5.js')),
			__memo(() => import('./nodes/6.js')),
			__memo(() => import('./nodes/7.js')),
			__memo(() => import('./nodes/8.js')),
			__memo(() => import('./nodes/9.js'))
		],
		remotes: {
			
		},
		routes: [
			{
				id: "/",
				pattern: /^\/$/,
				params: [],
				page: { layouts: [0,], errors: [1,], leaf: 2 },
				endpoint: null
			},
			{
				id: "/__fallback",
				pattern: /^\/__fallback\/?$/,
				params: [],
				page: { layouts: [0,], errors: [1,], leaf: 3 },
				endpoint: null
			},
			{
				id: "/checkin",
				pattern: /^\/checkin\/?$/,
				params: [],
				page: { layouts: [0,], errors: [1,], leaf: 4 },
				endpoint: null
			},
			{
				id: "/checkout",
				pattern: /^\/checkout\/?$/,
				params: [],
				page: { layouts: [0,], errors: [1,], leaf: 5 },
				endpoint: null
			},
			{
				id: "/debug-cookies",
				pattern: /^\/debug-cookies\/?$/,
				params: [],
				page: { layouts: [0,], errors: [1,], leaf: 6 },
				endpoint: null
			},
			{
				id: "/login",
				pattern: /^\/login\/?$/,
				params: [],
				page: { layouts: [0,], errors: [1,], leaf: 7 },
				endpoint: null
			},
			{
				id: "/logout",
				pattern: /^\/logout\/?$/,
				params: [],
				page: { layouts: [0,], errors: [1,], leaf: 8 },
				endpoint: null
			},
			{
				id: "/qr/[token]",
				pattern: /^\/qr\/([^/]+?)\/?$/,
				params: [{"name":"token","optional":false,"rest":false,"chained":false}],
				page: { layouts: [0,], errors: [1,], leaf: 9 },
				endpoint: null
			}
		],
		prerendered_routes: new Set([]),
		matchers: async () => {
			
			return {  };
		},
		server_assets: {}
	}
}
})();
