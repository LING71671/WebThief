# WebThief Advanced Guide

This guide covers advanced runtime-preservation features for JS-heavy sites.

## Overview

WebThief has two optional interception modules enabled by default:

- QR interception: capture QR lifecycle signals and inject QR bridge runtime.
- React/menu interception: preserve dynamic menus and convert part of JS visibility logic into CSS/runtime fallback.

## 5-Minute Quick Start

### 1) Clone a login page with QR behavior

```bash
webthief https://example.com/login --enable-qr-intercept -v
```

### 2) Clone a site with complex menu interactions

```bash
webthief https://example.com --enable-react-intercept -v
```

### 3) Max compatibility mode for dynamic pages

```bash
webthief https://example.com --single-page --keep-js --wait 5 -v
```

## Key Flags

- `--keep-js / --neutralize-js`:
- `--keep-js` (default): preserve page JS execution for interaction fidelity.
- `--neutralize-js`: disable runtime scripts in output for maximum static stability.
- `--enable-qr-intercept`: enable QR interception module.
- `--enable-react-intercept`: enable menu/component interception module.
- `--single-page`: best when you want homepage fidelity and external absolute jumps.
- `--crawl-site`: best when you need local multi-page navigation.
- `--wait N`: extra settle time after load; useful for delayed JS rendering.

## Recommended Workflows

### Dynamic homepage clone (recommended)

```bash
webthief https://target.site --single-page --keep-js --wait 5 -o ./clone_output -v
```

### Conservative static snapshot

```bash
webthief https://target.site --single-page --neutralize-js -o ./clone_output -v
```

## Verification Checklist

- Hero/banner autoplay and pagination work.
- Tab switch sections respond on click/hover.
- Hover fill/overlay transitions are visible.
- Lazy-loaded images appear after scroll.
- Network panel has no large batches of missing local assets.

## Troubleshooting

### Dynamic effects are missing

- Make sure output is generated with `--keep-js`.
- Increase `--wait` to `5` or `8` seconds.
- Open cloned pages through HTTP server, not `file://`.

Example:

```bash
cd clone_output
python -m http.server 8000
```

### Some decorative icons/backgrounds are missing

- Re-run with `-v` and inspect download failures.
- Confirm site uses same host paths; some third-party anti-hotlink scripts may block assets.

### Local runtime errors in console

- Try a baseline run to isolate runtime issues:

```bash
webthief https://target.site --single-page --neutralize-js -v
```

- Then compare with:

```bash
webthief https://target.site --single-page --keep-js -v
```

## Notes

- Absolute link fallback is intended for single-page homepage clones.
- Site-crawl mode rewrites same-host page links to local files.
- For legal/compliance boundaries, only clone sites you own or are authorized to test.
