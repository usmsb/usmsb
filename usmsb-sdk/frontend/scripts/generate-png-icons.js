/**
 * USMSB SDK Icon Generator
 * Generates PNG and ICO icons from SVG sources using sharp
 *
 * Usage:
 *   npm install sharp --save-dev
 *   node scripts/generate-icons.js
 */

import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';
import sharp from 'sharp';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

async function generateIcons() {

  const publicDir = path.join(__dirname, '..', 'public');

  // SVG content for favicon (simplified 32x32)
  const faviconSvg = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32" width="32" height="32">
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

  // Full logo SVG (512x512)
  const logoSvg = fs.readFileSync(path.join(publicDir, 'logo.svg'), 'utf8');

  console.log('Generating icons...');

  try {
    // Generate favicon.ico (16x16 and 32x32 multi-resolution)
    const png16 = await sharp(Buffer.from(faviconSvg))
      .resize(16, 16)
      .png()
      .toBuffer();

    const png32 = await sharp(Buffer.from(faviconSvg))
      .resize(32, 32)
      .png()
      .toBuffer();

    // Create ICO file (simplified - just use PNG data)
    // ICO header
    const icoHeader = Buffer.alloc(6);
    icoHeader.writeUInt16LE(0, 0);      // Reserved
    icoHeader.writeUInt16LE(1, 2);      // Type: 1 = ICO
    icoHeader.writeUInt16LE(2, 4);      // Number of images: 2

    // ICO directory entries
    const entry1 = Buffer.alloc(16);
    entry1.writeUInt8(16, 0);           // Width
    entry1.writeUInt8(16, 1);           // Height
    entry1.writeUInt8(0, 2);            // Color palette
    entry1.writeUInt8(0, 3);            // Reserved
    entry1.writeUInt16LE(1, 4);         // Color planes
    entry1.writeUInt16LE(32, 6);        // Bits per pixel
    entry1.writeUInt32LE(png16.length, 8);  // Size
    entry1.writeUInt32LE(22 + 32, 12);  // Offset (header + 2 entries)

    const entry2 = Buffer.alloc(16);
    entry2.writeUInt8(32, 0);           // Width
    entry2.writeUInt8(32, 1);           // Height
    entry2.writeUInt8(0, 2);
    entry2.writeUInt8(0, 3);
    entry2.writeUInt16LE(1, 4);
    entry2.writeUInt16LE(32, 6);
    entry2.writeUInt32LE(png32.length, 8);
    entry2.writeUInt32LE(22 + 32 + png16.length, 12);  // Offset

    const icoData = Buffer.concat([icoHeader, entry1, entry2, png16, png32]);
    fs.writeFileSync(path.join(publicDir, 'favicon.ico'), icoData);
    console.log('  Created: favicon.ico');

    // Generate logo192.png
    await sharp(Buffer.from(logoSvg))
      .resize(192, 192)
      .png()
      .toFile(path.join(publicDir, 'logo192.png'));
    console.log('  Created: logo192.png');

    // Generate logo512.png
    await sharp(Buffer.from(logoSvg))
      .resize(512, 512)
      .png()
      .toFile(path.join(publicDir, 'logo512.png'));
    console.log('  Created: logo512.png');

    // Generate apple-touch-icon.png (180x180)
    const appleTouchSvg = fs.readFileSync(path.join(publicDir, 'apple-touch-icon.svg'), 'utf8');
    await sharp(Buffer.from(appleTouchSvg))
      .resize(180, 180)
      .png()
      .toFile(path.join(publicDir, 'apple-touch-icon.png'));
    console.log('  Created: apple-touch-icon.png');

    console.log('\nAll icons generated successfully!');
  } catch (err) {
    console.error('Error generating icons:', err);
    process.exit(1);
  }
}

generateIcons().catch(console.error);
