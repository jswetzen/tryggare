import React, { useState, useEffect, useRef } from 'react';
import { Html5Qrcode } from 'html5-qrcode';
import { Camera, X, AlertCircle } from 'lucide-react';

export default function QRScanner() {
  const [scanning, setScanning] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [permissionDenied, setPermissionDenied] = useState(false);
  const scannerRef = useRef(null);

  const startScanner = async () => {
    setError(null);
    setPermissionDenied(false);
    
    try {
      // Initialize scanner if not already created
      if (!scannerRef.current) {
        scannerRef.current = new Html5Qrcode('qr-reader');
      }

      // Start scanning
      await scannerRef.current.start(
        { facingMode: 'environment' }, // Use back camera on mobile
        {
          fps: 10,
          qrbox: { width: 250, height: 250 },
          aspectRatio: 1.0
        },
        (decodedText) => {
          // Success callback - QR code detected
          setResult(decodedText);
          setScanning(false);
          
          // Stop the scanner
          if (scannerRef.current && scannerRef.current.isScanning) {
            scannerRef.current.stop().catch(console.error);
          }
        },
        (errorMessage) => {
          // This fires continuously while scanning, so we ignore it
          // Only actual errors are caught in the catch block
        }
      );
      
      setScanning(true);
    } catch (err) {
      console.error('Scanner error:', err);
      
      // Check if it's a permission error
      if (err.name === 'NotAllowedError' || 
          err.name === 'PermissionDeniedError' ||
          err.message?.includes('Permission denied')) {
        setPermissionDenied(true);
        setError('Camera access was denied. Please allow camera access to scan QR codes.');
      } else if (err.name === 'NotFoundError') {
        setError('No camera found on this device.');
      } else {
        setError('Failed to start camera. Please try again.');
      }
    }
  };

  useEffect(() => {
    startScanner();

    // Cleanup on unmount
    return () => {
      if (scannerRef.current) {
        scannerRef.current.stop().catch(console.error);
        scannerRef.current.clear().catch(console.error);
      }
    };
  }, []);

  const handleRetry = () => {
    startScanner();
  };

  const handleCloseResult = () => {
    setResult(null);
    startScanner();
  };

  return (
    <div className="min-h-screen bg-gray-900 flex items-center justify-center p-4">
      <div className="w-full max-w-md">
        <div className="bg-gray-800 rounded-lg shadow-xl overflow-hidden">
          {/* Header */}
          <div className="bg-gray-700 p-4 flex items-center gap-3">
            <Camera className="w-6 h-6 text-blue-400" />
            <h1 className="text-xl font-semibold text-white">QR Code Scanner</h1>
          </div>

          {/* Scanner Area */}
          <div className="relative bg-black">
            {!error && (
              <div 
                id="qr-reader" 
                className="w-full"
                style={{ minHeight: '300px' }}
              />
            )}

            {/* Error State */}
            {error && (
              <div className="p-8 text-center min-h-[300px] flex flex-col items-center justify-center">
                <AlertCircle className="w-16 h-16 text-red-400 mb-4" />
                <p className="text-red-300 mb-6">{error}</p>
                {permissionDenied && (
                  <button
                    onClick={handleRetry}
                    className="bg-blue-600 hover:bg-blue-700 text-white px-6 py-3 rounded-lg font-medium transition-colors"
                  >
                    Request Camera Access
                  </button>
                )}
              </div>
            )}

            {/* Scanning Status */}
            {scanning && !error && (
              <div className="absolute bottom-4 left-0 right-0 text-center">
                <div className="inline-block bg-black bg-opacity-70 text-white px-4 py-2 rounded-full text-sm">
                  Position QR code within the box
                </div>
              </div>
            )}
          </div>

          {/* Instructions */}
          {!error && (
            <div className="bg-gray-700 p-4">
              <p className="text-gray-300 text-sm text-center">
                Point your camera at a QR code to scan it
              </p>
            </div>
          )}
        </div>
      </div>

      {/* Result Popup */}
      {result && (
        <div className="fixed inset-0 bg-black bg-opacity-75 flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-lg shadow-2xl max-w-md w-full p-6 relative animate-in fade-in zoom-in duration-200">
            <button
              onClick={handleCloseResult}
              className="absolute top-4 right-4 text-gray-400 hover:text-gray-600 transition-colors"
            >
              <X className="w-6 h-6" />
            </button>

            <h2 className="text-2xl font-bold text-gray-800 mb-4">QR Code Detected!</h2>
            
            <div className="bg-gray-100 p-4 rounded-lg mb-6 break-all">
              <p className="text-gray-800 font-mono text-sm">{result}</p>
            </div>

            {/* Check if it's a URL */}
            {result.startsWith('http://') || result.startsWith('https://') ? (
              <a
                href={result}
                target="_blank"
                rel="noopener noreferrer"
                className="block w-full bg-blue-600 hover:bg-blue-700 text-white text-center px-6 py-3 rounded-lg font-medium transition-colors mb-3"
              >
                Open Link
              </a>
            ) : null}

            <button
              onClick={handleCloseResult}
              className="w-full bg-gray-200 hover:bg-gray-300 text-gray-800 px-6 py-3 rounded-lg font-medium transition-colors"
            >
              Scan Another
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
