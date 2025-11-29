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
		client: {start:"_app/immutable/entry/start.muNzoEOq.js",app:"_app/immutable/entry/app.BVOhBJfc.js",imports:["_app/immutable/entry/start.muNzoEOq.js","_app/immutable/chunks/CgIQ9ZAD.js","_app/immutable/chunks/BNFVY8TM.js","_app/immutable/chunks/DIeogL5L.js","_app/immutable/chunks/DqQmuhIe.js","_app/immutable/chunks/BXecR4_q.js","_app/immutable/chunks/DF1AgNLx.js","_app/immutable/entry/app.BVOhBJfc.js","_app/immutable/chunks/jKjWACjA.js","_app/immutable/chunks/BNFVY8TM.js","_app/immutable/chunks/DIeogL5L.js","_app/immutable/chunks/DgW1FCZf.js","_app/immutable/chunks/CWj6FrbW.js","_app/immutable/chunks/DF1AgNLx.js","_app/immutable/chunks/CrQ9bFLf.js","_app/immutable/chunks/DqQmuhIe.js","_app/immutable/chunks/C6yParRf.js"],stylesheets:[],fonts:[],uses_env_dynamic_public:false},
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
