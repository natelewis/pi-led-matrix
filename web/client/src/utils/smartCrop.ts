/**
 * Smart saliency-guided image cropping and exact-pixel matrix rendering engine.
 *
 * Computes an attention map combining:
 * - Edge gradient magnitude (high-detail subjects, text, edges)
 * - Color saturation & skin/warm subject prominence
 * - Gentle compositional bias (slightly favoring upper-center so portraits aren't decapitated)
 */

export type ImageFitMode = 'crop' | 'contain' | 'stretch';

export interface CropRect {
  x: number;
  y: number;
  width: number;
  height: number;
}

export interface SmartCropAnalysis {
  ratioMatch: 'exact' | 'wider' | 'taller';
  sourceAspect: number;
  targetAspect: number;
  /** Normalized focal point [0..1] representing the detected subject center. */
  focalX: number;
  focalY: number;
  /** Human-readable explanation of what smart crop noticed. */
  summary: string;
}

/**
 * Given source image dimensions, target matrix dimensions, a normalized focal
 * point [0..1], and zoom (>= 1), returns the exact source CropRect matching
 * targetAspect.
 */
export function computeCropRect(
  srcWidth: number,
  srcHeight: number,
  targetWidth: number,
  targetHeight: number,
  focalX: number,
  focalY: number,
  zoom = 1
): CropRect {
  const safeZoom = Math.max(1, Math.min(4, zoom));
  const srcAspect = srcWidth / Math.max(1, srcHeight);
  const targetAspect = targetWidth / Math.max(1, targetHeight);

  let baseW: number;
  let baseH: number;
  if (srcAspect > targetAspect) {
    // Source is wider than target -> height-bound
    baseH = srcHeight;
    baseW = baseH * targetAspect;
  } else {
    // Source is taller than target -> width-bound
    baseW = srcWidth;
    baseH = baseW / targetAspect;
  }

  const cropW = baseW / safeZoom;
  const cropH = baseH / safeZoom;

  const maxX = Math.max(0, srcWidth - cropW);
  const maxY = Math.max(0, srcHeight - cropH);

  const clampedFocalX = Math.max(0, Math.min(1, focalX));
  const clampedFocalY = Math.max(0, Math.min(1, focalY));

  const x = Math.max(0, Math.min(maxX, clampedFocalX * srcWidth - cropW / 2));
  const y = Math.max(0, Math.min(maxY, clampedFocalY * srcHeight - cropH / 2));

  return { x, y, width: cropW, height: cropH };
}

/**
 * Analyzes any CanvasImageSource (image or video frame) on a fast downsampled
 * canvas to find the highest-salience crop window for the target aspect ratio.
 */
export function analyzeSmartCropSource(
  source: CanvasImageSource,
  srcW: number,
  srcH: number,
  targetWidth: number,
  targetHeight: number,
  mediaNoun = 'Image'
): SmartCropAnalysis {
  const sourceAspect = srcW / Math.max(1, srcH);
  const targetAspect = targetWidth / Math.max(1, targetHeight);
  const ratioDiff = Math.abs(sourceAspect - targetAspect) / targetAspect;

  const ratioMatch: SmartCropAnalysis['ratioMatch'] =
    ratioDiff < 0.03 ? 'exact' : sourceAspect > targetAspect ? 'wider' : 'taller';

  if (ratioMatch === 'exact') {
    return {
      ratioMatch,
      sourceAspect,
      targetAspect,
      focalX: 0.5,
      focalY: 0.5,
      summary: 'Exact aspect ratio match — no cropping needed.',
    };
  }

  // Downsample for fast saliency scoring (<= 160px on long edge)
  const scale = Math.min(1, 160 / Math.max(srcW, srcH));
  const w = Math.max(16, Math.round(srcW * scale));
  const h = Math.max(16, Math.round(srcH * scale));

  const canvas = document.createElement('canvas');
  canvas.width = w;
  canvas.height = h;
  const ctx = canvas.getContext('2d', { willReadFrequently: true });
  if (!ctx) {
    return {
      ratioMatch,
      sourceAspect,
      targetAspect,
      focalX: 0.5,
      focalY: 0.45,
      summary: 'Centered crop applied.',
    };
  }

  ctx.drawImage(source, 0, 0, w, h);
  const { data } = ctx.getImageData(0, 0, w, h);

  // Build per-pixel luminance + salience map
  const lum = new Float32Array(w * h);
  const sat = new Float32Array(w * h);
  const skin = new Float32Array(w * h);

  for (let i = 0, p = 0; i < data.length; i += 4, p++) {
    const r = data[i] / 255;
    const g = data[i + 1] / 255;
    const b = data[i + 2] / 255;
    const a = data[i + 3] / 255;
    const maxC = Math.max(r, g, b);
    const minC = Math.min(r, g, b);

    lum[p] = (0.299 * r + 0.587 * g + 0.114 * b) * a;
    sat[p] = maxC > 0 ? ((maxC - minC) / maxC) * a : 0;

    // Gentle warm skin-tone heuristic to favor faces/people
    if (r > 0.35 && g > 0.18 && b > 0.1 && r > g && g > b && r - g > 0.05) {
      skin[p] = 0.6 * a;
    }
  }

  // Build 2D summed-area table (integral image) of attention weights for O(1) window scoring
  const stride = w + 1;
  const integral = new Float64Array((w + 1) * (h + 1));

  for (let y = 0; y < h; y++) {
    let rowSum = 0;
    for (let x = 0; x < w; x++) {
      const idx = y * w + x;
      const gx =
        x > 0 && x < w - 1 ? Math.abs(lum[idx + 1] - lum[idx - 1]) : 0;
      const gy =
        y > 0 && y < h - 1 ? Math.abs(lum[idx + w] - lum[idx - w]) : 0;
      const edge = Math.min(1, (gx + gy) * 2.2);

      // Slight composition weight: gently prefer rule-of-thirds / upper-center
      const nx = x / Math.max(1, w - 1);
      const ny = y / Math.max(1, h - 1);
      const centerDist = Math.hypot(nx - 0.5, (ny - 0.42) * 1.1);
      const compositionBias = Math.max(0.25, 1 - centerDist * 0.75);

      const attention =
        (edge * 0.6 + sat[idx] * 0.25 + skin[idx] * 0.35 + 0.05) * compositionBias;

      rowSum += attention;
      integral[(y + 1) * stride + (x + 1)] = integral[y * stride + (x + 1)] + rowSum;
    }
  }

  const windowScore = (x0: number, y0: number, x1: number, y1: number) =>
    integral[y1 * stride + x1] -
    integral[y0 * stride + x1] -
    integral[y1 * stride + x0] +
    integral[y0 * stride + x0];

  // Evaluate candidate windows matching targetAspect across the downsampled frame
  const cropW =
    w / h > targetAspect ? Math.max(1, Math.round(h * targetAspect)) : w;
  const cropH =
    w / h > targetAspect ? h : Math.max(1, Math.round(w / targetAspect));

  const maxX = Math.max(0, w - cropW);
  const maxY = Math.max(0, h - cropH);
  const stepX = Math.max(1, Math.floor(maxX / 36));
  const stepY = Math.max(1, Math.floor(maxY / 36));

  let bestScore = -1;
  let bestX = Math.floor(maxX / 2);
  let bestY = Math.floor(maxY / 2);

  for (let y = 0; y <= maxY; y += stepY) {
    for (let x = 0; x <= maxX; x += stepX) {
      const score = windowScore(x, y, x + cropW, y + cropH);
      if (score > bestScore) {
        bestScore = score;
        bestX = x;
        bestY = y;
      }
    }
  }

  const focalX = (bestX + cropW / 2) / w;
  const focalY = (bestY + cropH / 2) / h;

  let regionHint = 'center';
  if (ratioMatch === 'taller') {
    regionHint = focalY < 0.4 ? 'upper subject' : focalY > 0.6 ? 'lower subject' : 'vertical center';
  } else {
    regionHint = focalX < 0.4 ? 'left subject' : focalX > 0.6 ? 'right subject' : 'horizontal center';
  }

  return {
    ratioMatch,
    sourceAspect,
    targetAspect,
    focalX,
    focalY,
    summary: `${mediaNoun} is ${ratioMatch} than ${targetWidth}×${targetHeight} — auto-framed on ${regionHint}. Drag to fine-tune.`,
  };
}

export function analyzeSmartCrop(
  image: HTMLImageElement,
  targetWidth: number,
  targetHeight: number
): SmartCropAnalysis {
  return analyzeSmartCropSource(
    image,
    image.naturalWidth,
    image.naturalHeight,
    targetWidth,
    targetHeight,
    'Image'
  );
}

/**
 * Renders any CanvasImageSource (image or video frame) onto a targetWidth x
 * targetHeight canvas using the chosen fit mode, focal point, and zoom.
 */
export function renderMatrixSource(
  source: CanvasImageSource,
  srcW: number,
  srcH: number,
  targetWidth: number,
  targetHeight: number,
  options: {
    fitMode: ImageFitMode;
    focalX: number;
    focalY: number;
    zoom: number;
  },
  reuseCanvas?: HTMLCanvasElement
): { canvas: HTMLCanvasElement; rgbaBytes: Uint8ClampedArray } {
  const canvas = reuseCanvas ?? document.createElement('canvas');
  if (canvas.width !== targetWidth) canvas.width = targetWidth;
  if (canvas.height !== targetHeight) canvas.height = targetHeight;

  const ctx = canvas.getContext('2d', { willReadFrequently: true });
  if (!ctx) {
    throw new Error('Canvas 2D context unavailable.');
  }

  ctx.fillStyle = '#000000';
  ctx.fillRect(0, 0, targetWidth, targetHeight);
  ctx.imageSmoothingEnabled = true;
  ctx.imageSmoothingQuality = 'high';

  if (options.fitMode === 'stretch') {
    ctx.drawImage(source, 0, 0, srcW, srcH, 0, 0, targetWidth, targetHeight);
  } else if (options.fitMode === 'contain') {
    const scale = Math.min(targetWidth / srcW, targetHeight / srcH);
    const drawW = Math.max(1, Math.round(srcW * scale));
    const drawH = Math.max(1, Math.round(srcH * scale));
    const offsetX = Math.floor((targetWidth - drawW) / 2);
    const offsetY = Math.floor((targetHeight - drawH) / 2);
    ctx.drawImage(source, 0, 0, srcW, srcH, offsetX, offsetY, drawW, drawH);
  } else {
    const rect = computeCropRect(
      srcW,
      srcH,
      targetWidth,
      targetHeight,
      options.focalX,
      options.focalY,
      options.zoom
    );
    ctx.drawImage(
      source,
      rect.x,
      rect.y,
      rect.width,
      rect.height,
      0,
      0,
      targetWidth,
      targetHeight
    );
  }

  const imageData = ctx.getImageData(0, 0, targetWidth, targetHeight);
  for (let i = 3; i < imageData.data.length; i += 4) {
    imageData.data[i] = 255;
  }

  return { canvas, rgbaBytes: imageData.data };
}

export function renderMatrixImage(
  image: HTMLImageElement,
  targetWidth: number,
  targetHeight: number,
  options: {
    fitMode: ImageFitMode;
    focalX: number;
    focalY: number;
    zoom: number;
  }
): { canvas: HTMLCanvasElement; rgbaBytes: Uint8ClampedArray } {
  return renderMatrixSource(
    image,
    image.naturalWidth,
    image.naturalHeight,
    targetWidth,
    targetHeight,
    options
  );
}

let cachedMaskKey = '';
let cachedMaskCanvas: HTMLCanvasElement | null = null;
let scratchSrcCanvas: HTMLCanvasElement | null = null;

function getDotMaskCanvas(
  targetWidth: number,
  targetHeight: number,
  cell: number
): HTMLCanvasElement {
  const key = `${targetWidth}x${targetHeight}@${cell}`;
  if (cachedMaskCanvas && cachedMaskKey === key) {
    return cachedMaskCanvas;
  }

  // Create a single cell dot pattern and tile it across the full mask canvas
  const tile = document.createElement('canvas');
  tile.width = cell;
  tile.height = cell;
  const tileCtx = tile.getContext('2d');
  if (tileCtx) {
    tileCtx.fillStyle = '#ffffff';
    tileCtx.beginPath();
    tileCtx.arc(cell / 2, cell / 2, cell * 0.42, 0, Math.PI * 2);
    tileCtx.fill();
  }

  const mask = document.createElement('canvas');
  mask.width = targetWidth * cell;
  mask.height = targetHeight * cell;
  const mctx = mask.getContext('2d');
  if (mctx) {
    const pattern = mctx.createPattern(tile, 'repeat');
    if (pattern) {
      mctx.fillStyle = pattern;
      mctx.fillRect(0, 0, mask.width, mask.height);
    }
  }

  cachedMaskKey = key;
  cachedMaskCanvas = mask;
  return mask;
}

/**
 * Draws a matrix RGBA buffer onto a display preview canvas using GPU-accelerated
 * scaling and a cached dot-mask pattern (fast enough for 60 FPS video previews).
 */
export function paintLedPreviewCanvas(
  canvas: HTMLCanvasElement,
  rgbaBytes: Uint8ClampedArray,
  targetWidth: number,
  targetHeight: number,
  ledDots: boolean
): void {
  const cell = Math.max(
    2,
    Math.min(8, Math.floor(320 / Math.max(targetWidth, targetHeight)))
  );
  const nextW = targetWidth * cell;
  const nextH = targetHeight * cell;
  if (canvas.width !== nextW) canvas.width = nextW;
  if (canvas.height !== nextH) canvas.height = nextH;

  if (!scratchSrcCanvas) {
    scratchSrcCanvas = document.createElement('canvas');
  }
  if (scratchSrcCanvas.width !== targetWidth) scratchSrcCanvas.width = targetWidth;
  if (scratchSrcCanvas.height !== targetHeight) scratchSrcCanvas.height = targetHeight;

  const sctx = scratchSrcCanvas.getContext('2d');
  const ctx = canvas.getContext('2d');
  if (!sctx || !ctx) return;

  const imgData = sctx.createImageData(targetWidth, targetHeight);
  imgData.data.set(rgbaBytes);
  sctx.putImageData(imgData, 0, 0);

  ctx.globalCompositeOperation = 'source-over';
  ctx.clearRect(0, 0, nextW, nextH);
  ctx.imageSmoothingEnabled = false;
  ctx.drawImage(scratchSrcCanvas, 0, 0, nextW, nextH);

  if (ledDots && cell >= 3) {
    const mask = getDotMaskCanvas(targetWidth, targetHeight, cell);
    ctx.globalCompositeOperation = 'destination-in';
    ctx.drawImage(mask, 0, 0);
    ctx.globalCompositeOperation = 'destination-over';
    ctx.fillStyle = '#000000';
    ctx.fillRect(0, 0, nextW, nextH);
    ctx.globalCompositeOperation = 'source-over';
  }
}

export function uint8ToBase64(bytes: Uint8ClampedArray): string {
  const chunkSize = 0x8000;
  const parts: string[] = [];
  for (let i = 0; i < bytes.length; i += chunkSize) {
    const slice = bytes.subarray(i, i + chunkSize);
    parts.push(String.fromCharCode(...slice));
  }
  return btoa(parts.join(''));
}
