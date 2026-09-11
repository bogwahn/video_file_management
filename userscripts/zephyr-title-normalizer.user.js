// ==UserScript==
// @name         Zephyr Title Normalizer
// @namespace    https://bogwahn.com/zephyr
// @version      0.1.0
// @description  Rewrite document.title to Zephyr filename grammar for Video DownloadHelper.
// @match        *://*/*
// @grant        GM_getValue
// @grant        GM_setValue
// @grant        GM_registerMenuCommand
// ==/UserScript==

/**
 * Spike skeleton: extract page metadata → set document.title to locked grammar:
 *   {Actors}.{Studio}.{Title}.{Resolution}[.VR].{ext}
 * Reuses BANG! / Persepolis normalization patterns; retargeted from helper enqueue to title rewrite.
 *
 * Operator: point Video DownloadHelper at /Internal/Zetc/Download (see docs/zephyr/download-helper.md).
 * TamperMonkey cannot mkdir the hot folder — FileWatcher ensures it exists.
 */

(function () {
  'use strict';

  const HARD_CAP = 150;
  const MAX_ACTORS = 3;

  // Dotted resolution form (locked): ….Title.4k.mp4  (not Title4k)
  const DEFAULT_FILENAME_CONFIG = {
    global: {
      mode: 'default',
      template: '{actors}.{studio}.{title}.{resolution}{vr}.{ext}',
      maxLength: 150
    },
    perHost: {}
  };

  // Seed BANG!-style host selectors (CSS; migrate from userscripts/BANG!Xpath.xpath as needed).
  const DEFAULT_SITE_CONFIG = {
    // Example placeholder — replace selectors per MVP host:
    // 'www.example.com': {
    //   isVr: false,
    //   selectors: [
    //     { name: 'actors', css: '.cast a', attr: 'text', multi: true },
    //     { name: 'studio', css: '.studio a', attr: 'text' },
    //     { name: 'title', css: 'h1', attr: 'text' },
    //     { name: 'resolution', css: '.quality .active', attr: 'text' }
    //   ]
    // }
  };

  function getFilenameConfig() {
    return GM_getValue('filenameConfig', DEFAULT_FILENAME_CONFIG);
  }
  function setFilenameConfig(cfg) {
    GM_setValue('filenameConfig', cfg);
  }
  function getSiteConfig() {
    return GM_getValue('siteConfig', DEFAULT_SITE_CONFIG);
  }
  function setSiteConfig(cfg) {
    GM_setValue('siteConfig', cfg);
  }
  function getSiteConfigForHost(host) {
    return getSiteConfig()[host] || null;
  }

  function toTitleCaseWords(raw) {
    return raw
      .toLowerCase()
      .split(/\s+/)
      .filter(Boolean)
      .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
      .join(' ');
  }

  function stripIllegal(raw) {
    return String(raw || '').replace(/[\/:*"<>|]/g, '');
  }

  function normalizeActorName(raw) {
    if (!raw) return null;
    const titled = toTitleCaseWords(stripIllegal(raw).trim().replace(/\s+/g, ' '));
    return titled.replace(/\s+/g, '.');
  }

  function buildActorBlock(actorNames) {
    if (!actorNames || !actorNames.length) return null;
    let norm = actorNames.map(normalizeActorName).filter(Boolean);
    if (norm.length > MAX_ACTORS) {
      console.warn('Zephyr: truncating actors to', MAX_ACTORS);
      norm = norm.slice(0, MAX_ACTORS);
    }
    if (!norm.length) return null;
    return norm.length === 1 ? norm[0] : norm.join('.And.');
  }

  function normalizeStudio(raw) {
    if (!raw) return null;
    const titled = toTitleCaseWords(stripIllegal(raw).trim().replace(/\s+/g, ' '));
    // Prefer dotted words (locked plan) over space-stripped CamelCase.
    return titled.replace(/\s+/g, '.');
  }

  function normalizeTitle(raw) {
    if (!raw) return null;
    const titled = toTitleCaseWords(stripIllegal(raw).trim().replace(/\s+/g, ' '));
    return titled.replace(/\s+/g, '.');
  }

  function normalizeResolution(raw) {
    if (!raw) return null;
    const t = String(raw).toLowerCase();
    if (t.includes('480')) return '480p';
    if (t.includes('540')) return '540p';
    if (t.includes('720')) return '720p';
    if (t.includes('1080')) return '1080p';
    if (t.includes('4k') || t.includes('2160')) return '4k';
    if (t.includes('2k') || t.includes('1440')) return '2k';
    return null;
  }

  function detectVr(cfg, meta) {
    if (cfg && cfg.isVr === true) return true;
    const href = (window.location.href || '').toLowerCase();
    if (href.includes('/vr/')) return true;
    const badges = cfg && Array.isArray(cfg.vrSignals) ? cfg.vrSignals : ['VR', '180°', 'SBS', 'MKX200'];
    const bodyText = (document.body && document.body.innerText) || '';
    for (const b of badges) {
      if (bodyText.indexOf(b) !== -1 && (b !== 'VR' || /\bVR\b/.test(bodyText))) {
        // light heuristic; host isVr flag is preferred
      }
    }
    if (cfg && cfg.isVr) return !!cfg.isVr;
    return false;
  }

  function getNodeValue(node, attr) {
    if (!node) return null;
    if (attr === 'text') {
      const t = (node.textContent || '').trim();
      return t || null;
    }
    const val = node.getAttribute(attr);
    return val ? val.trim() : null;
  }

  function extractMetaForCurrentHost() {
    const host = window.location.host;
    const cfg = getSiteConfigForHost(host);
    const result = {
      host,
      pageUrl: window.location.href,
      url: null,
      actors: [],
      studio: null,
      title: null,
      resolution: null,
      extension: 'mp4',
      isVr: false
    };

    if (!cfg || !Array.isArray(cfg.selectors)) {
      return result;
    }

    for (const sel of cfg.selectors.slice(0, 20)) {
      const { name, css, attr = 'text', multi = false } = sel;
      if (!name || !css) continue;
      if (multi) {
        const values = Array.from(document.querySelectorAll(css))
          .map((n) => getNodeValue(n, attr))
          .filter(Boolean);
        if (name === 'actors') result.actors.push(...values);
      } else {
        const node = document.querySelector(css);
        const value = getNodeValue(node, attr);
        if (!value) continue;
        if (name === 'actors') result.actors.push(value);
        else if (name === 'studio' && !result.studio) result.studio = value;
        else if (name === 'title' && !result.title) result.title = value;
        else if (name === 'resolution' && !result.resolution) result.resolution = value;
        else if ((name === 'downloadUrl' || name === 'url') && !result.url) result.url = value;
      }
    }

    if (!result.url) {
      const a = document.querySelector('a[href*=".mp4"], a[href*=".mkv"], a[href*=".webm"]');
      if (a && a.href) result.url = a.href;
    }
    if (result.url) {
      try {
        const path = new URL(result.url, window.location.href).pathname || '';
        const ext = path.split('.').pop();
        if (ext && ext.length <= 5) result.extension = ext.toLowerCase();
      } catch (e) {
        /* ignore */
      }
    }

    result.isVr = detectVr(cfg, result);
    return result;
  }

  function buildZephyrFilename(meta) {
    const actorBlock = buildActorBlock(meta.actors);
    const studioBlock = normalizeStudio(meta.studio);
    const titleBlock = normalizeTitle(meta.title);
    const resToken = normalizeResolution(meta.resolution) || '4k';
    const ext = (meta.extension || 'mp4').toLowerCase().replace(/^\./, '');

    if (!actorBlock || !studioBlock || !titleBlock) {
      return null; // incomplete — do not claim standardized
    }

    const vr = meta.isVr ? '.VR' : '';
    let name = [actorBlock, studioBlock, titleBlock, resToken].join('.') + vr + '.' + ext;
    name = name.replace(/\.+/g, '.');
    return enforceMaxLength(name, HARD_CAP);
  }

  function enforceMaxLength(filename, maxLen) {
    if (!filename || filename.length <= maxLen) return filename;
    const m = filename.match(/^(.*?)(\.(?:VR\.)?[^.]+)$/i);
    let base = filename;
    let ext = '';
    if (m) {
      // Prefer truncating title: drop tokens before resolution
      base = m[1];
      ext = m[2];
    }
    const parts = base.split('.');
    while ((parts.join('.') + ext).length > maxLen && parts.length > 4) {
      // drop from title region (near end, before resolution)
      parts.splice(parts.length - 2, 1);
    }
    let out = parts.join('.') + ext;
    if (out.length > maxLen) out = out.slice(0, maxLen);
    return out;
  }

  let lastApplied = null;
  let applyTimer = null;

  function applyTitle() {
    const meta = extractMetaForCurrentHost();
    const name = buildZephyrFilename(meta);
    if (!name) {
      console.warn('Zephyr: incomplete metadata; leaving document.title alone (or set NEEDS-META via menu).');
      return null;
    }
    if (document.title !== name) {
      document.title = name;
      lastApplied = name;
      console.log('Zephyr title set:', name);
    }
    return name;
  }

  function resistOverwrite() {
    if (!lastApplied) return;
    if (document.title !== lastApplied) {
      document.title = lastApplied;
    }
  }

  function scheduleApply() {
    if (applyTimer) clearTimeout(applyTimer);
    applyTimer = setTimeout(function () {
      applyTitle();
    }, 250);
  }

  GM_registerMenuCommand('Zephyr: Apply title now', function () {
    const name = applyTitle();
    window.alert(name ? 'Title set to:\n' + name : 'Incomplete metadata — configure site selectors.');
  });

  GM_registerMenuCommand('Zephyr: Preview filename', function () {
    const meta = extractMetaForCurrentHost();
    const name = buildZephyrFilename(meta);
    window.alert(
      'Preview:\n' +
        (name || '(incomplete)') +
        '\n\nActors: ' +
        JSON.stringify(meta.actors) +
        '\nStudio: ' +
        meta.studio +
        '\nTitle: ' +
        meta.title +
        '\nRes: ' +
        meta.resolution +
        '\nVR: ' +
        meta.isVr +
        '\nPage: ' +
        meta.pageUrl
    );
  });

  GM_registerMenuCommand('Zephyr: Edit site selectors (JSON for this host)', function () {
    const host = window.location.host;
    const all = getSiteConfig();
    const current = all[host] || { isVr: false, selectors: [] };
    const updated = window.prompt('Edit selector config for ' + host, JSON.stringify(current, null, 2));
    if (!updated) return;
    try {
      const parsed = JSON.parse(updated);
      if (!Array.isArray(parsed.selectors) || parsed.selectors.length > 20) {
        window.alert('selectors must be an array with at most 20 entries');
        return;
      }
      all[host] = parsed;
      setSiteConfig(all);
      scheduleApply();
      window.alert('Saved selectors for ' + host);
    } catch (e) {
      window.alert('JSON error: ' + e);
    }
  });

  GM_registerMenuCommand('Zephyr: Edit filename config JSON', function () {
    const cfg = getFilenameConfig();
    const updated = window.prompt('Edit filename config', JSON.stringify(cfg, null, 2));
    if (!updated) return;
    try {
      setFilenameConfig(JSON.parse(updated));
      window.alert('Filename config saved');
    } catch (e) {
      window.alert('JSON error: ' + e);
    }
  });

  // Auto-apply when a host config exists; resist site JS overwriting title.
  if (getSiteConfigForHost(window.location.host)) {
    scheduleApply();
    const obs = new MutationObserver(function () {
      resistOverwrite();
    });
    const titleEl = document.querySelector('title');
    if (titleEl) obs.observe(titleEl, { childList: true, characterData: true, subtree: true });
    setInterval(resistOverwrite, 2000);
  }
})();
