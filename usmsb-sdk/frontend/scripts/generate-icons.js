/**
 * USMSB SDK Icon Generator
 * Generates PNG icons from SVG sources
 *
 * Run: node scripts/generate-icons.js
 */

const fs = require('fs');
const path = require('path');

// ICO file header generator (simplified - creates a valid ICO with PNG data)
function createIco(pngBuffer, width, height) {
  // ICO Header (6 bytes)
  const header = Buffer.alloc(6);
  header.writeUInt16LE(0, 0);      // Reserved
  header.writeUInt16LE(1, 2);      // Type: 1 = ICO
  header.writeUInt16LE(1, 4);      // Number of images

  // ICO Directory Entry (16 bytes)
  const entry = Buffer.alloc(16);
  entry.writeUInt8(width > 255 ? 0 : width, 0);    // Width
  entry.writeUInt8(height > 255 ? 0 : height, 1);  // Height
  entry.writeUInt8(0, 2);          // Color palette
  entry.writeUInt8(0, 3);          // Reserved
  entry.writeUInt16LE(1, 4);       // Color planes
  entry.writeUInt16LE(32, 6);      // Bits per pixel
  entry.writeUInt32LE(pngBuffer.length, 8);  // Size of image data
  entry.writeUInt32LE(22, 12);     // Offset to image data

  return Buffer.concat([header, entry, pngBuffer]);
}

// Create a simple PNG file manually (minimal 16x16, 32x32 icons)
function createSimplePng(size) {
  // This creates a minimal valid PNG with a solid color
  const { createCanvas } = require('canvas');
  const canvas = createCanvas(size, size);
  const ctx = canvas.getContext('2d');

  // Draw background
  ctx.fillStyle = '#0f0f23';
  ctx.beginPath();
  ctx.arc(size/2, size/2, size/2 - 1, 0, Math.PI * 2);
  ctx.fill();

  // Draw hexagon gradient
  const gradient = ctx.createLinearGradient(0, 0, size, size);
  gradient.addColorStop(0, '#6366f1');
  gradient.addColorStop(1, '#a855f7');

  ctx.fillStyle = gradient;
  const s = size / 2;
  const cx = size / 2;
  const cy = size / 2;

  ctx.beginPath();
  for (let i = 0; i < 6; i++) {
    const angle = (Math.PI / 3) * i - Math.PI / 2;
    const x = cx + s * 0.6 * Math.cos(angle);
    const y = cy + s * 0.6 * Math.sin(angle);
    if (i === 0) ctx.moveTo(x, y);
    else ctx.lineTo(x, y);
  }
  ctx.closePath();
  ctx.fill();

  // Draw center dot
  ctx.fillStyle = 'white';
  ctx.beginPath();
  ctx.arc(cx, cy, size * 0.1, 0, Math.PI * 2);
  ctx.fill();

  return canvas.toBuffer('image/png');
}

// Simple fallback: Create base64 encoded PNG data
function createFallbackPngDataUri(size) {
  // Return a data URI that can be embedded
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32" width="${size}" height="${size}">
    <defs>
      <linearGradient id="g" x1="0%" y1="0%" x2="100%" y2="100%">
        <stop offset="0%" style="stop-color:#6366f1"/>
        <stop offset="100%" style="stop-color:#a855f7"/>
      </linearGradient>
    </defs>
    <circle cx="16" cy="16" r="15" fill="#0f0f23"/>
    <polygon points="16,6 24,11 24,21 16,26 8,21 8,11" fill="url(#g)"/>
    <polygon points="16,9 21,12 21,20 16,23 11,20 11,12" fill="none" stroke="white" stroke-width="1" opacity="0.7"/>
    <circle cx="16" cy="16" r="2" fill="white" opacity="0.9"/>
  </svg>`;

  return svg;
}

// Main execution
const publicDir = path.join(__dirname, '..', 'public');

console.log('USMSB Icon Generator');
console.log('====================');

// Check if we have the canvas package
let hasCanvas = false;
try {
  require('canvas');
  hasCanvas = true;
} catch (e) {
  console.log('Note: canvas package not found. PNG generation requires manual conversion.');
  console.log('The SVG files can be converted using:');
  console.log('  - Online tools like cloudconvert.com');
  console.log('  - ImageMagick: convert -background none favicon.svg favicon.ico');
  console.log('  - Inkscape: inkscape favicon.svg --export-favicon=favicon.ico');
}

// Create manifest.json reference
console.log('\nSVG icons available:');
console.log('  - logo.svg (512x512 main logo)');
console.log('  - logo-dark.svg (512x512 dark version)');
console.log('  - favicon.svg (32x32 favicon)');
console.log('  - apple-touch-icon.svg (180x180)');

console.log('\nFor production, convert SVG to PNG/ICO using:');
console.log('  npm install -g sharp');
console.log('  Or use online conversion tools');

// Export function for programmatic use
module.exports = {
  createIco,
  createSimplePng: hasCanvas ? createSimplePng : null,
  createFallbackPngDataUri
};
