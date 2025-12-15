
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
		RouteId(): "/" | "/__fallback" | "/checkin" | "/checkout-compare" | "/checkout" | "/debug-cookies" | "/login" | "/logout" | "/print-queue" | "/qr" | "/qr/[token]";
		RouteParams(): {
			"/qr/[token]": { token: string }
		};
		LayoutParams(): {
			"/": { token?: string };
			"/__fallback": Record<string, never>;
			"/checkin": Record<string, never>;
			"/checkout-compare": Record<string, never>;
			"/checkout": Record<string, never>;
			"/debug-cookies": Record<string, never>;
			"/login": Record<string, never>;
			"/logout": Record<string, never>;
			"/print-queue": Record<string, never>;
			"/qr": { token?: string };
			"/qr/[token]": { token: string }
		};
		Pathname(): "/" | "/__fallback" | "/__fallback/" | "/checkin" | "/checkin/" | "/checkout-compare" | "/checkout-compare/" | "/checkout" | "/checkout/" | "/debug-cookies" | "/debug-cookies/" | "/login" | "/login/" | "/logout" | "/logout/" | "/print-queue" | "/print-queue/" | "/qr" | "/qr/" | `/qr/${string}` & {} | `/qr/${string}/` & {};
		ResolvedPathname(): `${"" | `/${string}`}${ReturnType<AppTypes['Pathname']>}`;
		Asset(): string & {};
	}
}