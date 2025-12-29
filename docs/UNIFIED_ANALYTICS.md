# Unified Google Analytics Setup

**GA4 Property ID**: `G-3RYSL77PJF`

This document describes the unified analytics setup for all Finsoeasy properties.

---

## Sites Using This Property

| Site | Domain | Status |
|------|--------|--------|
| R&D Alpha Research | research.finsoeasy.com | ✅ Active |
| Main Finsoeasy | finsoeasy.com | ⏳ Pending deployment |

---

## GA4 Tracking Code for finsoeasy.com

Add this snippet to the `<head>` section of finsoeasy.com:

```html
<!-- Google Analytics - Unified Finsoeasy Property -->
<script async src="https://www.googletagmanager.com/gtag/js?id=G-3RYSL77PJF"></script>
<script>
  window.dataLayer = window.dataLayer || [];
  function gtag(){dataLayer.push(arguments);}
  gtag('js', new Date());
  gtag('config', 'G-3RYSL77PJF', {
    'cookie_domain': '.finsoeasy.com',
    'cookie_flags': 'SameSite=None;Secure'
  });
</script>
```

---

## How It Works

1. **Single GA4 Property**: Both sites report to `G-3RYSL77PJF`
2. **Automatic Hostname Tracking**: GA4 automatically records the hostname for each pageview
3. **Cross-domain Tracking**: The `cookie_domain: '.finsoeasy.com'` setting enables shared cookies across subdomains

---

## Viewing Data in GA4

### Filter by Site

In GA4, you can filter reports by hostname:

1. Go to **Reports** → **Engagement** → **Pages and screens**
2. Add a **Comparison** or **Filter**
3. Filter by `Hostname` equals:
   - `research.finsoeasy.com` - Research platform
   - `finsoeasy.com` - Main site

### Create Segments

For recurring analysis, create segments:

1. Go to **Explore** → **Segments**
2. Create segment with condition: `Hostname exactly matches research.finsoeasy.com`
3. Name it "Research Platform"
4. Repeat for "Main Site"

---

## Implementation Status

- [x] Research platform (research.finsoeasy.com) - Already tracking
- [x] Main site (finsoeasy.com) - **DEPLOYED Dec 29, 2025**

---

## Deployment Instructions for finsoeasy.com

1. SSH into Sydney server:
   ```bash
   ssh -i ~/.ssh/finsoeasy-key.pem ubuntu@13.210.239.75
   ```

2. Locate the main HTML template (likely in `/var/www/` or similar)

3. Add the GA4 snippet to the `<head>` section

4. Restart the web server if needed:
   ```bash
   sudo systemctl restart nginx
   ```

---

*Last updated: December 29, 2025*

