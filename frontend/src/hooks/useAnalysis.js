/**
 * Internal trace:
 * - Wrong before: upload state and result state were scattered across pages with toast-driven errors and no reliable retry/reset flow.
 * - Fixed now: one hook owns idle/uploading/analysing/done/error states, upload progress, normalized API errors, and result persistence for routing.
 */

import { useMemo, useRef, useState } from 'react';
import client from '../api/client.js';

function buildErrorState(error) {
  if (error.isTimeout) {
    return {
      title: 'Analysis timed out',
      message: 'This file took too long to process. Try a smaller or shorter upload.',
      retryLabel: 'Try Again',
      code: error.code,
    };
  }

  if (error.isNetworkError) {
    return {
      title: 'Server unreachable',
      message: 'Check that the backend is running, then retry the upload.',
      retryLabel: 'Retry',
      code: error.code,
    };
  }

  if (error.status === 422 || error.status === 413) {
    return {
      title: 'Upload rejected',
      message: error.message,
      retryLabel: 'Choose Another File',
      code: error.code,
    };
  }

  return {
    title: 'Analysis failed - try again',
    message: error.message || 'Unexpected server error',
    retryLabel: 'Retry',
    code: error.code || 'REQUEST_FAILED',
  };
}

function detectFileType(file) {
  if (file.type.startsWith('image/')) return 'image';
  if (file.type.startsWith('video/')) return 'video';
  return 'audio';
}

export function useAnalysis() {
  const [status, setStatus] = useState('idle');
  const [progress, setProgress] = useState(0);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [asset, setAsset] = useState(null);
  const assetUrlRef = useRef(null);

  const reset = () => {
    if (assetUrlRef.current) {
      URL.revokeObjectURL(assetUrlRef.current);
      assetUrlRef.current = null;
    }
    setStatus('idle');
    setProgress(0);
    setResult(null);
    setError(null);
    setAsset(null);
  };

  const analyseFile = async (file, preview, mode = 'free') => {
    if (assetUrlRef.current) {
      URL.revokeObjectURL(assetUrlRef.current);
    }

    const previewUrl = URL.createObjectURL(file);
    assetUrlRef.current = previewUrl;
    setAsset({
      name: file.name,
      size: file.size,
      type: file.type,
      fileType: detectFileType(file),
      previewUrl,
      thumbnailUrl: preview?.thumbnailUrl || preview?.url || '',
      waveform: preview?.waveform || [],
    });
    setError(null);
    setResult(null);
    setProgress(0);
    setStatus('uploading');

    const formData = new FormData();
    formData.append('file', file);

    let intervalId = null;

    try {
      const endpoint = mode === 'paid' ? '/analyse/deep' : '/analyse';
      const response = await client.post(endpoint, formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
        onUploadProgress: (event) => {
          if (!event.total) return;
          const next = Math.round((event.loaded / event.total) * 92);
          setProgress((current) => Math.max(current, next));
          if (next >= 92) {
            setStatus('analysing');
            if (!intervalId) {
              intervalId = window.setInterval(() => {
                setProgress((current) => {
                  const next = current < 99 ? current + 1 : current;
                  if (mode === 'paid') {
                    if (next >= 94 && next < 96) setStatus('waking');
                    if (next >= 96 && next < 98) setStatus('deep_scanning');
                    if (next >= 98 && next < 99) setStatus('saving_paid');
                    if (next >= 99) setStatus('standby');
                  }
                  return next;
                });
              }, 400);
            }
          }
        },
      });

      if (intervalId) window.clearInterval(intervalId);
      setProgress(100);
      setResult(response.data);
      setStatus('done');
      return response.data;
    } catch (thrown) {
      if (intervalId) window.clearInterval(intervalId);
      setStatus('error');
      setProgress(0);
      const nextError = buildErrorState(thrown);
      setError(nextError);
      throw nextError;
    }
  };

  return useMemo(
    () => ({ status, progress, result, error, asset, analyseFile, reset }),
    [asset, error, progress, result, status],
  );
}
