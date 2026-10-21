"use client";

import { useEffect, useRef, useState } from "react";
import { Icon } from "./icons";
import { Modal } from "./modal";

/** A live camera preview with a shutter. Laptops ignore <input capture>, so this
 * asks for the camera directly and hands back a JPEG file. */
export function CameraCapture({ onClose, onCapture }: { onClose: () => void; onCapture: (file: File) => void }) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const [error, setError] = useState(() => typeof navigator !== "undefined" && !navigator.mediaDevices?.getUserMedia
    ? "This browser has no camera access. Upload a photo instead." : "");
  const [ready, setReady] = useState(false);

  // Mounted only while open, so each opening starts fresh and closing releases the camera.
  useEffect(() => {
    let stream: MediaStream | null = null;
    let cancelled = false;
    navigator.mediaDevices?.getUserMedia({ video: { facingMode: "environment" }, audio: false })
      .then((media) => {
        if (cancelled) { media.getTracks().forEach((track) => track.stop()); return; }
        stream = media;
        if (videoRef.current) videoRef.current.srcObject = media;
      })
      .catch(() => setError("ARIA can't use your camera. Allow camera access in your browser, or upload a photo instead."));
    return () => { cancelled = true; stream?.getTracks().forEach((track) => track.stop()); };
  }, []);

  const snap = () => {
    const video = videoRef.current;
    if (!video?.videoWidth) return;
    const canvas = document.createElement("canvas");
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    canvas.getContext("2d")?.drawImage(video, 0, 0);
    canvas.toBlob((blob) => {
      if (!blob) return;
      const stamp = new Date().toISOString().slice(0, 16).replace(/[-:T]/g, "");
      onCapture(new File([blob], `Photo ${stamp}.jpg`, { type: "image/jpeg" }));
      onClose();
    }, "image/jpeg", 0.9);
  };

  return (
    <Modal open title="Take a photo" onClose={onClose}>
      <div className="modal camera-modal">
        <div className="section-head">
          <h3 style={{ margin: 0 }}>Take a photo</h3>
          <button className="btn btn-ghost" aria-label="Close camera" onClick={onClose}><Icon name="x" size={16} /></button>
        </div>
        {error
          ? <p role="alert" className="camera-error">{error}</p>
          : <video ref={videoRef} className="camera-view" autoPlay playsInline muted onLoadedData={() => setReady(true)} aria-label="Camera preview" />}
        <div className="dialog-actions">
          <button className="btn btn-secondary" onClick={onClose}>Cancel</button>
          {!error && <button className="btn btn-primary" disabled={!ready} onClick={snap}><Icon name="camera" size={16} /> Take photo</button>}
        </div>
      </div>
    </Modal>
  );
}
