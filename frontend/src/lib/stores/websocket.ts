/**
 * WebSocket store for real-time check-in/check-out updates
 * Uses Svelte writable stores for reactivity
 */

import { writable } from 'svelte/store';
import type { WebSocketMessage } from '$lib/api/types';

// WebSocket URL for browser connections (not server-side)
// Must use VITE_ prefix to be available in browser
const WS_BASE_URL = import.meta.env.VITE_PUBLIC_WS_BASE_URL || 'ws://localhost:8000';

interface WebSocketState {
  connected: boolean;
  connecting: boolean;
  error: string | null;
  lastMessage: WebSocketMessage | null;
}

class WebSocketStore {
  private socket: WebSocket | null = null;
  private reconnectTimeout: number | null = null;
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;
  private reconnectDelay = 3000;

  // State using Svelte writable store
  public state = writable<WebSocketState>({
    connected: false,
    connecting: false,
    error: null,
    lastMessage: null,
  });

  // Message handlers
  private messageHandlers: Set<(message: WebSocketMessage) => void> = new Set();

  /**
   * Connect to WebSocket
   */
  connect() {
    if (this.socket?.readyState === WebSocket.OPEN) {
      return;
    }

    this.state.update((s) => ({ ...s, connecting: true, error: null }));

    try {
      const url = `${WS_BASE_URL}/ws/checkins/`;
      this.socket = new WebSocket(url);

      this.socket.onopen = () => {
        console.log('WebSocket connected');
        this.state.update((s) => ({ ...s, connected: true, connecting: false }));
        this.reconnectAttempts = 0;
      };

      this.socket.onmessage = (event) => {
        try {
          const message: WebSocketMessage = JSON.parse(event.data);
          this.state.update((s) => ({ ...s, lastMessage: message }));

          // Notify all handlers
          this.messageHandlers.forEach((handler) => handler(message));
        } catch (error) {
          console.error('Failed to parse WebSocket message:', error);
        }
      };

      this.socket.onerror = (error) => {
        console.error('WebSocket error:', error);
        this.state.update((s) => ({ ...s, error: 'WebSocket connection error' }));
      };

      this.socket.onclose = () => {
        console.log('WebSocket disconnected');
        this.state.update((s) => ({ ...s, connected: false, connecting: false }));

        // Attempt to reconnect
        if (this.reconnectAttempts < this.maxReconnectAttempts) {
          this.reconnectTimeout = window.setTimeout(() => {
            this.reconnectAttempts++;
            console.log(
              `Reconnecting... (attempt ${this.reconnectAttempts}/${this.maxReconnectAttempts})`
            );
            this.connect();
          }, this.reconnectDelay);
        } else {
          this.state.update((s) => ({ ...s, error: 'Maximum reconnection attempts reached' }));
        }
      };
    } catch (error) {
      console.error('Failed to create WebSocket:', error);
      this.state.update((s) => ({ ...s, connecting: false, error: 'Failed to create WebSocket connection' }));
    }
  }

  /**
   * Disconnect from WebSocket
   */
  disconnect() {
    if (this.reconnectTimeout) {
      clearTimeout(this.reconnectTimeout);
      this.reconnectTimeout = null;
    }

    if (this.socket) {
      this.socket.close();
      this.socket = null;
    }

    this.state.update((s) => ({ ...s, connected: false, connecting: false }));
    this.reconnectAttempts = 0;
  }

  /**
   * Subscribe to messages
   */
  onMessage(handler: (message: WebSocketMessage) => void): () => void {
    this.messageHandlers.add(handler);

    // Return unsubscribe function
    return () => {
      this.messageHandlers.delete(handler);
    };
  }

  /**
   * Send a message (not currently used, but available for future features)
   */
  send(data: unknown) {
    if (this.socket?.readyState === WebSocket.OPEN) {
      this.socket.send(JSON.stringify(data));
    } else {
      console.warn('WebSocket is not connected');
    }
  }
}

// Export singleton instance
export const websocketStore = new WebSocketStore();
