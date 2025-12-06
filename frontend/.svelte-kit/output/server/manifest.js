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
		client: {start:"_app/immutable/entry/start.D3o_YclF.js",app:"_app/immutable/entry/app.9kjT0wki.js",imports:["_app/immutable/entry/start.D3o_YclF.js","_app/immutable/chunks/DQ_BFNpF.js","_app/immutable/chunks/pxs1u2Lk.js","_app/immutable/chunks/DIeogL5L.js","_app/immutable/chunks/DE_lwqnV.js","_app/immutable/chunks/CAO759vl.js","_app/immutable/chunks/B4SCbM-L.js","_app/immutable/entry/app.9kjT0wki.js","_app/immutable/chunks/C1FmrZbK.js","_app/immutable/chunks/pxs1u2Lk.js","_app/immutable/chunks/DIeogL5L.js","_app/immutable/chunks/Cr9hUHC2.js","_app/immutable/chunks/DOBAaUNM.js","_app/immutable/chunks/CWj6FrbW.js","_app/immutable/chunks/B4SCbM-L.js","_app/immutable/chunks/BmWNL-SK.js","_app/immutable/chunks/DE_lwqnV.js","_app/immutable/chunks/D9fO5uqx.js","_app/immutable/chunks/Dn4RsGBP.js"],stylesheets:[],fonts:[],uses_env_dynamic_public:false},
		nodes: [
			__memo(() => import('./nodes/0.js')),
			__memo(() => import('./nodes/1.js')),
			__memo(() => import('./nodes/2.js')),
			__memo(() => import('./nodes/4.js')),
			__memo(() => import('./nodes/5.js')),
			__memo(() => import('./nodes/6.js')),
			__memo(() => import('./nodes/7.js')),
			__memo(() => import('./nodes/8.js')),
			__memo(() => import('./nodes/9.js')),
			__memo(() => import('./nodes/10.js'))
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
				id: "/checkin",
				pattern: /^\/checkin\/?$/,
				params: [],
				page: { layouts: [0,], errors: [1,], leaf: 3 },
				endpoint: null
			},
			{
				id: "/checkout",
				pattern: /^\/checkout\/?$/,
				params: [],
				page: { layouts: [0,], errors: [1,], leaf: 4 },
				endpoint: null
			},
			{
				id: "/debug-cookies",
				pattern: /^\/debug-cookies\/?$/,
				params: [],
				page: { layouts: [0,], errors: [1,], leaf: 5 },
				endpoint: null
			},
			{
				id: "/login",
				pattern: /^\/login\/?$/,
				params: [],
				page: { layouts: [0,], errors: [1,], leaf: 6 },
				endpoint: null
			},
			{
				id: "/logout",
				pattern: /^\/logout\/?$/,
				params: [],
				page: { layouts: [0,], errors: [1,], leaf: 7 },
				endpoint: null
			},
			{
				id: "/print-queue",
				pattern: /^\/print-queue\/?$/,
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
		prerendered_routes: new Set(["/__fallback","/__fallback/__data.json","/favicon.png"]),
		matchers: async () => {
			
			return {  };
		},
		server_assets: {}
	}
}
})();
