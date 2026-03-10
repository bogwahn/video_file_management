// ==UserScript==
// @name         Persepolis Download Helper
// @namespace    https://bogwahn.com/
// @version      0.1.0
// @description  Build structured filenames from page metadata and send downloads to a local Persepolis helper.
// @match        *://*/*
// @grant        GM_getValue
// @grant        GM_setValue
// @grant        GM_registerMenuCommand
// @grant        GM_xmlhttpRequest
// ==/UserScript==

(function () {
  'use strict';

  // ---------------------------------------------------------------------------
  // Constants
  // ---------------------------------------------------------------------------

  const HARD_CAP = 150;
  const HELPER_ENDPOINT = 'http://127.0.0.1:8765/enqueue';

  // ---------------------------------------------------------------------------
  // Default Configs (can be overridden via GM_* JSON editors)
  // ---------------------------------------------------------------------------

  const DEFAULT_FILENAME_CONFIG = {
    global: {
      mode: 'default', // 'default' | 'template' | 'customFn'
      template: '{actors}.{studio}.{title}{resolution}.{ext}',
      customFn: '',
      maxLength: 150
    },
    perHost: {
      // 'www.example.com': {
      //   mode: 'template',
      //   template: '{actors}.{studio}.{title}{resolution}.{ext}',
      //   customFn: '',
      //   maxLength: 140
      // }
    }
  };

  const DEFAULT_RUNTIME_CONFIG = {
    globalMode: 'prompt-with-default', // 'auto' | 'prompt' | 'prompt-with-default'
    perHostMode: {
      // 'www.example.com': 'auto'
    }
  };

  const DEFAULT_SITE_CONFIG = {
    // 'www.example.com': {
    //   selectors: [
    //     { name: 'actors',     css: '.cast .actor',         attr: 'text',   multi: true },
    //     { name: 'studio',     css: '.studio a',            attr: 'text' },
    //     { name: 'title',      css: 'h1.video-title',       attr: 'text' },
    //     { name: 'resolution', css: '.quality-picker .on',  attr: 'text' },
    //     { name: 'downloadUrl',css: 'a.download-btn',       attr: 'href' }
    //   ]
    // }
  };

  // ---------------------------------------------------------------------------
  // Config Accessors
  // ---------------------------------------------------------------------------

  function getFilenameConfig() {
    return GM_getValue('filenameConfig', DEFAULT_FILENAME_CONFIG);
  }

  function setFilenameConfig(cfg) {
    GM_setValue('filenameConfig', cfg);
  }

  function getRuntimeConfig() {
    return GM_getValue('runtimeConfig', DEFAULT_RUNTIME_CONFIG);
  }

  function setRuntimeConfig(cfg) {
    GM_setValue('runtimeConfig', cfg);
  }

  function getSiteConfig() {
    return GM_getValue('siteConfig', DEFAULT_SITE_CONFIG);
  }

  function setSiteConfig(cfg) {
    GM_setValue('siteConfig', cfg);
  }

  function getSiteConfigForHost(host) {
    const all = getSiteConfig();
    return all[host] || null;
  }

  // ---------------------------------------------------------------------------
  // Normalization Helpers (Title Case, dot-joining, resolution)
  // ---------------------------------------------------------------------------

  function toTitleCaseWords(raw) {
    return raw
      .toLowerCase()
      .split(/\s+/)
      .filter(Boolean)
      .map(w => w.charAt(0).toUpperCase() + w.slice(1))
      .join(' ');
  }

  function normalizeActorName(raw) {
    if (!raw) return null;
    const cleaned = raw
      .trim()
      .replace(/\s+/g, ' ')
      .replace(/[\/:*"<>|]/g, '');
    const titled = toTitleCaseWords(cleaned);
    return titled.replace(/\s+/g, '.');
  }

  function buildActorBlock(actorNames) {
    if (!actorNames || !actorNames.length) return null;
    const norm = actorNames.map(normalizeActorName).filter(Boolean);
    if (!norm.length) return null;
    if (norm.length === 1) return norm[0];
    return norm.join('.And.');
  }

  function normalizeStudio(raw) {
    if (!raw) return null;
    const cleaned = raw
      .trim()
      .replace(/\s+/g, ' ')
      .replace(/[\/:*"<>|]/g, '');
    const titled = toTitleCaseWords(cleaned);
    return titled.replace(/\s+/g, '');
  }

  function normalizeTitle(raw) {
    if (!raw) return null;
    const cleaned = raw
      .trim()
      .replace(/[\/:*"<>|]/g, '');
    const titled = toTitleCaseWords(cleaned);
    return titled.replace(/\s+/g, '.');
  }

  function normalizeResolution(raw) {
    if (!raw) return null;
    const t = raw.toLowerCase();
    if (t.includes('480')) return '480p';
    if (t.includes('540')) return '540p';
    if (t.includes('720')) return '720p';
    if (t.includes('1080')) return '1080p';
    if (t.includes('4k')) return '4k';
    if (t.includes('2k')) return '2k';
    return null;
  }

  // ---------------------------------------------------------------------------
  // Selector Evaluation / Meta Extraction
  // ---------------------------------------------------------------------------

  function getNodeValue(node, attr) {
    if (!node) return null;
    if (attr === 'text') {
      const t = node.textContent || '';
      const trimmed = t.trim();
      return trimmed || null;
    }
    const val = node.getAttribute(attr);
    return val ? val.trim() : null;
  }

  function extractMetaForCurrentHost() {
    const host = window.location.host;
    const cfg = getSiteConfigForHost(host);
    const result = {
      host,
      url: null,
      actors: [],
      studio: null,
      title: null,
      resolution: null,
      extension: null
    };

    if (!cfg || !Array.isArray(cfg.selectors)) {
      return result;
    }

    const selectors = cfg.selectors.slice(0, 20); // enforce 20 max per host

    for (const sel of selectors) {
      const { name, css, attr = 'text', multi = false } = sel;
      if (!name || !css) continue;

      if (multi) {
        const nodes = Array.from(document.querySelectorAll(css));
        const values = nodes.map(n => getNodeValue(n, attr)).filter(Boolean);
        if (!values.length) continue;

        if (name === 'actors') {
          result.actors.push(...values);
        } else {
          if (!Array.isArray(result[name])) {
            result[name] = [];
          }
          result[name].push(...values);
        }
      } else {
        const node = document.querySelector(css);
        if (!node) continue;
        const value = getNodeValue(node, attr);
        if (!value) continue;

        if (name === 'actors') {
          result.actors.push(value);
        } else if (name === 'studio') {
          if (!result.studio) result.studio = value;
        } else if (name === 'title') {
          if (!result.title) result.title = value;
        } else if (name === 'resolution') {
          if (!result.resolution) result.resolution = value;
        } else if (name === 'downloadUrl' || name === 'url') {
          if (!result.url) result.url = value;
        } else {
          result[name] = value;
        }
      }
    }

    // Fallback: try a generic media link if no explicit URL selector
    if (!result.url) {
      const a = document.querySelector('a[href*=".mp4"], a[href*=".mkv"], a[href*=".webm"]');
      if (a && a.href) result.url = a.href;
    }

    // Derive extension from URL
    if (result.url) {
      try {
        const u = new URL(result.url, window.location.href);
        const path = u.pathname || '';
        const ext = path.split('.').pop();
        if (ext && ext.length <= 5) {
          result.extension = ext.toLowerCase();
        }
      } catch (e) {
        console.warn('Failed to parse URL for extension:', e);
      }
    }

    return result;
  }

  // ---------------------------------------------------------------------------
  // Filename Config & Override Logic
  // ---------------------------------------------------------------------------

  function getUserOverrideForHost(host) {
    const cfg = getFilenameConfig();
    if (cfg.perHost && cfg.perHost[host]) return cfg.perHost[host];
    return cfg.global || null;
  }

  function getRuntimeModeForHost(host) {
    const cfg = getRuntimeConfig();
    if (cfg.perHostMode && cfg.perHostMode[host]) {
      return cfg.perHostMode[host];
    }
    return cfg.globalMode || 'auto';
  }

  function getMaxLengthForHost(host) {
    const cfg = getFilenameConfig();
    let requested =
      (cfg.perHost && cfg.perHost[host] && cfg.perHost[host].maxLength) ??
      (cfg.global && cfg.global.maxLength) ??
      HARD_CAP;

    if (!Number.isFinite(requested) || requested <= 0) {
      requested = HARD_CAP;
    }
    return Math.min(requested, HARD_CAP);
  }

  function buildDefaultFilename(meta) {
    const actorBlock  = buildActorBlock(meta.actors);
    const studioBlock = normalizeStudio(meta.studio);
    const titleBlock  = normalizeTitle(meta.title);
    const resToken    = normalizeResolution(meta.resolution);

    const titleWithRes = titleBlock
      ? titleBlock + (resToken || '')
      : (resToken || '');

    const parts = [];
    if (actorBlock)  parts.push(actorBlock);
    if (studioBlock) parts.push(studioBlock);
    if (titleWithRes) parts.push(titleWithRes);

    const base = parts.join('.');
    const ext  = (meta.extension || 'mp4').toLowerCase().replace(/^\./, '');
    return `${base}.${ext}`;
  }

  function buildNormalizedBlocks(meta) {
    return {
      actorsBlock: buildActorBlock(meta.actors),
      studioBlock: normalizeStudio(meta.studio),
      titleBlock:  normalizeTitle(meta.title),
      resToken:    normalizeResolution(meta.resolution),
      ext:         (meta.extension || 'mp4').toLowerCase().replace(/^\./, '')
    };
  }

  function applyTemplate(template, meta) {
    const norm = buildNormalizedBlocks(meta);
    const ctx = {
      actors:     norm.actorsBlock || '',
      studio:     norm.studioBlock || '',
      title:      norm.titleBlock || '',
      resolution: norm.resToken || '',
      ext:        norm.ext
    };

    let out = template;
    for (const [key, value] of Object.entries(ctx)) {
      const token = '{' + key + '}';
      // simple replace-all
      while (out.includes(token)) {
        out = out.replace(token, value);
      }
    }

    // fix repeated dots
    out = out.replace(/\.+/g, '.');

    // ensure extension at end
    if (!out.toLowerCase().endsWith('.' + ctx.ext)) {
      if (!out.endsWith('.')) out += '.';
      out += ctx.ext;
    }

    return out;
  }

  function runCustomFn(fnBody, meta) {
    try {
      const fn = new Function('meta', fnBody);
      const result = fn(meta);
      if (typeof result === 'string' && result.trim()) {
        return result.trim();
      }
    } catch (e) {
      console.error('Custom filename function error:', e);
    }
    return buildDefaultFilename(meta);
  }

  function getFilename(meta) {
    const host = meta.host;
    const override = getUserOverrideForHost(host);
    if (!override || !override.mode || override.mode === 'default') {
      return buildDefaultFilename(meta);
    }
    if (override.mode === 'template') {
      const tpl = override.template || DEFAULT_FILENAME_CONFIG.global.template;
      return applyTemplate(tpl, meta);
    }
    if (override.mode === 'customFn') {
      return runCustomFn(override.customFn || '', meta);
    }
    return buildDefaultFilename(meta);
  }

  function enforceMaxLength(filename, maxLen) {
    if (!filename || filename.length <= maxLen) return filename;

    const m = filename.match(/^(.*?)(\.[^.]*)$/);
    let base, ext;
    if (m) {
      base = m[1];
      ext  = m[2];
    } else {
      base = filename;
      ext  = '';
    }

    if (ext.length >= maxLen) {
      return filename.slice(0, maxLen);
    }

    const allowedBaseLen = maxLen - ext.length;
    if (base.length <= allowedBaseLen) {
      return base + ext;
    }

    let truncatedBase = base.slice(0, allowedBaseLen);
    const lastDot = truncatedBase.lastIndexOf('.');
    if (lastDot > allowedBaseLen * 0.4) {
      truncatedBase = truncatedBase.slice(0, lastDot);
    }

    return truncatedBase + ext;
  }

  function promptForFilename(defaultName, meta) {
    const msg = 'Persepolis filename for:\n' +
      (meta.url || '') +
      '\n\nEdit or replace:';
    return window.prompt(msg, defaultName);
  }

  async function getFinalFilename(meta, options) {
    const opts = options || {};
    const forcePrompt = !!opts.forcePrompt;

    const autoName = getFilename(meta);
    const mode = getRuntimeModeForHost(meta.host);
    const maxLen = getMaxLengthForHost(meta.host);

    let candidate = autoName;

    const shouldPrompt =
      forcePrompt ||
      mode === 'prompt' ||
      mode === 'prompt-with-default';

    if (shouldPrompt) {
      const suggested = (mode === 'prompt-with-default') ? autoName : '';
      const userValue = promptForFilename(suggested, meta);
      if (userValue && userValue.trim()) {
        candidate = userValue.trim();
      }
    }

    return enforceMaxLength(candidate, maxLen);
  }

  // ---------------------------------------------------------------------------
  // Local Helper Communication
  // ---------------------------------------------------------------------------

  function sendToHelper(payload) {
    GM_xmlhttpRequest({
      method: 'POST',
      url: HELPER_ENDPOINT,
      headers: { 'Content-Type': 'application/json' },
      data: JSON.stringify(payload),
      onload: function (res) {
        if (res.status !== 200 && res.status !== 201) {
          console.error('Helper responded with error:', res.status, res.responseText);
        }
      },
      onerror: function (err) {
        console.error('Failed to reach helper:', err);
      }
    });
  }

  async function enqueueFromPage(options) {
    const opts = options || {};
    const forcePrompt = !!opts.forcePrompt;

    const meta = extractMetaForCurrentHost();
    if (!meta.url) {
      console.warn('Persepolis userscript: No download URL found on this page.');
      return;
    }

    const filename = await getFinalFilename(meta, { forcePrompt });
    const payload = {
      url: meta.url,
      filename,
      host: meta.host
    };

    console.log('Persepolis enqueue payload:', payload);
    sendToHelper(payload);
  }

  // ---------------------------------------------------------------------------
  // Menu Commands / Entry Points
  // ---------------------------------------------------------------------------

  GM_registerMenuCommand('Persepolis: Enqueue (auto/config)', function () {
    enqueueFromPage({ forcePrompt: false });
  });

  GM_registerMenuCommand('Persepolis: Enqueue (force prompt)', function () {
    enqueueFromPage({ forcePrompt: true });
  });

  GM_registerMenuCommand('Persepolis: Edit site selectors (JSON for this host)', function () {
    const host = window.location.host;
    const all = getSiteConfig();
    const current = all[host] || { selectors: [] };
    const pretty = JSON.stringify(current, null, 2);
    const updated = window.prompt('Edit selector config for host: ' + host, pretty);
    if (!updated) return;
    try {
      const parsed = JSON.parse(updated);
      if (!Array.isArray(parsed.selectors) || parsed.selectors.length > 20) {
        window.alert('Invalid config: selectors must be an array with at most 20 entries.');
        return;
      }
      all[host] = parsed;
      setSiteConfig(all);
      window.alert('Selector config saved for ' + host);
    } catch (e) {
      window.alert('Error parsing JSON: ' + e);
    }
  });

  GM_registerMenuCommand('Persepolis: Edit filename config (global + perHost JSON)', function () {
    const cfg = getFilenameConfig();
    const pretty = JSON.stringify(cfg, null, 2);
    const updated = window.prompt('Edit filename config (global + perHost)', pretty);
    if (!updated) return;
    try {
      const parsed = JSON.parse(updated);
      setFilenameConfig(parsed);
      window.alert('Filename config saved.');
    } catch (e) {
      window.alert('Error parsing JSON: ' + e);
    }
  });

  GM_registerMenuCommand('Persepolis: Edit runtime config (JSON)', function () {
    const cfg = getRuntimeConfig();
    const pretty = JSON.stringify(cfg, null, 2);
    const updated = window.prompt('Edit runtime config (modes)', pretty);
    if (!updated) return;
    try {
      const parsed = JSON.parse(updated);
      setRuntimeConfig(parsed);
      window.alert('Runtime config saved.');
    } catch (e) {
      window.alert('Error parsing JSON: ' + e);
    }
  });

  // ---------------------------------------------------------------------------
  // (Optional) Future: Shift+click interception can be added here
  // ---------------------------------------------------------------------------

})();
