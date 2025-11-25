
// this file is generated — do not edit it


declare module "svelte/elements" {
	export interface HTMLAttributes<T> {
		'data-sveltekit-keepfocus'?: true | '' | 'off' | undefined | null;
		'data-sveltekit-noscroll'?: true | '' | 'off' | undefined | null;
		'data-sveltekit-preload-code'?:
			| true
			| ''
			| 'eager'
			| 'viewport'
			| 'hover'
			| 'tap'
			| 'off'
			| undefined
			| null;
		'data-sveltekit-preload-data'?: true | '' | 'hover' | 'tap' | 'off' | undefined | null;
		'data-sveltekit-reload'?: true | '' | 'off' | undefined | null;
		'data-sveltekit-replacestate'?: true | '' | 'off' | undefined | null;
	}
}

export {};


declare module "$app/types" {
	export interface AppTypes {
		RouteId(): "/" | "/checkin" | "/checkout" | "/debug-cookies" | "/login" | "/logout" | "/qr" | "/qr/[token]";
		RouteParams(): {
			"/qr/[token]": { token: string }
		};
		LayoutParams(): {
			"/": { token?: string };
			"/checkin": Record<string, never>;
			"/checkout": Record<string, never>;
			"/debug-cookies": Record<string, never>;
			"/login": Record<string, never>;
			"/logout": Record<string, never>;
			"/qr": { token?: string };
			"/qr/[token]": { token: string }
		};
		Pathname(): "/" | "/checkin" | "/checkin/" | "/checkout" | "/checkout/" | "/debug-cookies" | "/debug-cookies/" | "/login" | "/login/" | "/logout" | "/logout/" | "/qr" | "/qr/" | `/qr/${string}` & {} | `/qr/${string}/` & {};
		ResolvedPathname(): `${"" | `/${string}`}${ReturnType<AppTypes['Pathname']>}`;
		Asset(): string & {};
	}
}