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
		client: {start:"_app/immutable/entry/start.CukmqLAI.js",app:"_app/immutable/entry/app.D22Ig4bH.js",imports:["_app/immutable/entry/start.CukmqLAI.js","_app/immutable/chunks/J08drevD.js","_app/immutable/chunks/CNMrB2ks.js","_app/immutable/chunks/B7s-rZmo.js","_app/immutable/chunks/Ba3sptyn.js","_app/immutable/chunks/CfLHk2GV.js","_app/immutable/entry/app.D22Ig4bH.js","_app/immutable/chunks/jKjWACjA.js","_app/immutable/chunks/CNMrB2ks.js","_app/immutable/chunks/BrR-DdPc.js","_app/immutable/chunks/CfLHk2GV.js","_app/immutable/chunks/BaRHjNmB.js","_app/immutable/chunks/B7s-rZmo.js","_app/immutable/chunks/CuE6rR82.js"],stylesheets:[],fonts:[],uses_env_dynamic_public:false},
		nodes: [
			__memo(() => import('./nodes/0.js')),
			__memo(() => import('./nodes/1.js')),
			__memo(() => import('./nodes/2.js')),
			__memo(() => import('./nodes/3.js')),
			__memo(() => import('./nodes/4.js')),
			__memo(() => import('./nodes/5.js')),
			__memo(() => import('./nodes/6.js')),
			__memo(() => import('./nodes/7.js')),
			__memo(() => import('./nodes/8.js'))
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
				id: "/qr/[token]",
				pattern: /^\/qr\/([^/]+?)\/?$/,
				params: [{"name":"token","optional":false,"rest":false,"chained":false}],
				page: { layouts: [0,], errors: [1,], leaf: 8 },
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
