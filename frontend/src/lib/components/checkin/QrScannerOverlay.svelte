<script lang="ts">
  import { onMount, onDestroy } from 'svelte';
  import { t } from 'svelte-i18n';

  interface Props {
    onScan: (code: string) => void;
    onClose: () => void;
  }

  let { onScan, onClose }: Props = $props();

  let videoEl = $state<HTMLVideoElement | null>(null);
  let canvasEl = $state<HTMLCanvasElement | null>(null);
  let stream = $state<MediaStream | null>(null);
  let cameraError = $state<'insecure' | 'denied' | 'unavailable' | null>(null);
  let scanning = $state(false);
  let rafId: number;

  onMount(async () => {
    // Camera API requires a secure context (HTTPS or localhost)
    if (!navigator.mediaDevices || !window.isSecureContext) {
      cameraError = 'insecure';
      return;
    }
    try {
      stream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: 'environment' }
      });
      if (videoEl) {
        videoEl.srcObject = stream;
        await videoEl.play();
        scanning = true;
        rafId = requestAnimationFrame(scanFrame);
      }
    } catch (err) {
      const name = (err as DOMException)?.name;
      if (name === 'NotAllowedError' || name === 'PermissionDeniedError') {
        cameraError = 'denied';
      } else {
        cameraError = 'unavailable';
      }
    }
  });

  onDestroy(() => {
    stopCamera();
  });

  function stopCamera() {
    scanning = false;
    if (rafId) cancelAnimationFrame(rafId);
    if (stream) {
      stream.getTracks().forEach((t) => t.stop());
      stream = null;
    }
  }

  async function scanFrame() {
    if (!scanning || !videoEl || !canvasEl) return;
    if (videoEl.readyState < videoEl.HAVE_ENOUGH_DATA) {
      rafId = requestAnimationFrame(scanFrame);
      return;
    }

    const w = videoEl.videoWidth;
    const h = videoEl.videoHeight;
    canvasEl.width = w;
    canvasEl.height = h;
    const ctx = canvasEl.getContext('2d');
    if (!ctx) return;

    ctx.drawImage(videoEl, 0, 0, w, h);
    const imageData = ctx.getImageData(0, 0, w, h);

    // Lazy-load jsQR
    const jsQR = (await import('jsqr')).default;
    const result = jsQR(imageData.data, w, h);
    if (result) {
      scanning = false;
      stopCamera();
      onScan(result.data);
      return;
    }

    rafId = requestAnimationFrame(scanFrame);
  }

  function handleClose() {
    stopCamera();
    onClose();
  }
</script>

<!-- Full-screen overlay -->
<div
  class="fixed inset-0 z-50 flex flex-col items-center justify-center bg-black/80"
  role="dialog"
  aria-modal="true"
  aria-label={$t('checkin.qrScanTitle')}
>
  <!-- Close button -->
  <button
    onclick={handleClose}
    class="absolute top-4 right-4 text-white bg-black/40 hover:bg-black/60 rounded-full w-10 h-10 flex items-center justify-center text-xl font-bold"
    aria-label={$t('checkin.qrClose')}
  >
    ×
  </button>

  <!-- Title -->
  <p class="text-white text-lg font-semibold mb-4">{$t('checkin.qrScanTitle')}</p>

  {#if cameraError}
    <!-- Error state -->
    <div class="bg-white rounded-xl p-6 mx-4 max-w-sm text-center">
      {#if cameraError === 'insecure'}
        <p class="text-slate-700">{$t('checkin.qrCameraInsecureContext')}</p>
      {:else if cameraError === 'denied'}
        <p class="text-slate-700">{$t('checkin.qrCameraPermissionDenied')}</p>
      {:else}
        <p class="text-slate-700">{$t('checkin.qrCameraUnavailable')}</p>
      {/if}
      <button
        onclick={handleClose}
        class="mt-4 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
      >
        {$t('checkin.qrClose')}
      </button>
    </div>
  {:else}
    <!-- Viewfinder -->
    <div class="relative">
      <!-- Video element -->
      <!-- svelte-ignore a11y_media_has_caption -->
      <video
        bind:this={videoEl}
        class="rounded-lg max-w-[min(90vw,400px)] max-h-[60vh] object-cover"
        playsinline
      ></video>

      <!-- Viewfinder border overlay -->
      <div
        class="absolute inset-0 rounded-lg pointer-events-none"
        style="box-shadow: 0 0 0 4px rgba(59,130,246,0.8), inset 0 0 0 2px rgba(59,130,246,0.4);"
      ></div>

      <!-- Corner marks -->
      <div class="absolute top-2 left-2 w-6 h-6 border-t-4 border-l-4 border-blue-400 rounded-tl"></div>
      <div class="absolute top-2 right-2 w-6 h-6 border-t-4 border-r-4 border-blue-400 rounded-tr"></div>
      <div class="absolute bottom-2 left-2 w-6 h-6 border-b-4 border-l-4 border-blue-400 rounded-bl"></div>
      <div class="absolute bottom-2 right-2 w-6 h-6 border-b-4 border-r-4 border-blue-400 rounded-br"></div>
    </div>
  {/if}

  <!-- Hidden canvas for decoding -->
  <canvas bind:this={canvasEl} class="hidden"></canvas>
</div>
