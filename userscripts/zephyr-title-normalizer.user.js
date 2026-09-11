// ==UserScript==
// @name         Zephyr Title Normalizer
// @namespace    https://bogwahn.com/zephyr
// @version      0.2.0
// @description  Rewrite document.title to Zephyr filename grammar for Video DownloadHelper.
// @match        *://newsensations.com/*
// @match        *://www.newsensations.com/*
// @grant        GM_getValue
// @grant        GM_setValue
// @grant        GM_registerMenuCommand
// ==/UserScript==

/**
 * Spike: extract page metadata → set document.title to locked grammar:
 *   {Actors}.{Studio}.{Title}.{Resolution}[.VR].{ext}
 *
 * Reuses Persepolis/BANG! normalize patterns (First.Last, .And., max 3 actors, dotted res).
 * Per-host selector map below; NS selectors aligned to stash CommunityScrapers NewSensationsMain
 * (+ NetworkSites fallbacks). See docs/zephyr/newsensations.md.
 *
 * Operator: point Video DownloadHelper at /Internal/Zetc/Download (docs/zephyr/download-helper.md).
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

  /**
   * New Sensations tour scene page (tour_ns / updates).
   * Primary XPath from stash NewSensationsMain.yml; CSS + alternate XPaths as fallbacks.
   * Studio is fixed (site does not expose a reliable studio link on scene pages).
   */
  const NEWSENSATIONS_HOST = {
    isVr: false,
    studioFixed: 'New Sensations',
    notes:
      'tour_ns scene pages: div.indScene h1 + span.tour_update_models a. ' +
      'Resolution often absent on tour HTML — inferred from download links or defaults to 4k.',
    selectors: [
      // Title (primary + layout variants across NS network tours)
      { name: 'title', xpath: "//div[@class='indScene']/h1", attr: 'text' },
      { name: 'title', xpath: "//div[@class='indScene']/h2", attr: 'text' },
      { name: 'title', css: 'div.indScene h1', attr: 'text' },
      { name: 'title', css: 'div.indScene h2', attr: 'text' },
      { name: 'title', xpath: "//div[@class='update_title']", attr: 'text' },
      { name: 'title', css: 'div.update_title', attr: 'text' },
      { name: 'title', xpath: "//span[@class='title_bar_hilite']", attr: 'text' },

      // Actors (max 3 applied later); multi
      {
        name: 'actors',
        xpath: "//div[@class='sceneTextLink']/p/span[@class='tour_update_models']/a",
        attr: 'text',
        multi: true
      },
      {
        name: 'actors',
        xpath: "//span[@class='tour_update_models']/a",
        attr: 'text',
        multi: true
      },
      { name: 'actors', css: 'div.sceneTextLink span.tour_update_models a', attr: 'text', multi: true },
      { name: 'actors', css: 'span.tour_update_models a', attr: 'text', multi: true },
      { name: 'actors', xpath: "//span[@class='update_models']/a", attr: 'text', multi: true },
      { name: 'actors', css: 'span.update_models a', attr: 'text', multi: true },

      // Studio: fixed string (also applied via studioFixed if selectors miss)
      { name: 'studio', fixed: 'New Sensations' },

      // Resolution when a quality control exists (member / download UI — often missing on tour)
      { name: 'resolution', css: '.download_quality .active, .quality-picker .on, .quality.active', attr: 'text' },
      {
        name: 'resolution',
        xpath: "//a[contains(@href,'.mp4') or contains(@href,'.mkv')][contains(.,'4k') or contains(.,'4K') or contains(.,'1080') or contains(.,'720')]",
        attr: 'text'
      },
      {
        name: 'downloadUrl',
        css: 'a[href*=".mp4"], a[href*=".mkv"], a[href*=".webm"]',
        attr: 'href'
      }
    ]
  };

  // Per-host config map. Only newsensations.com is filled; other hosts = empty scaffolding.
  const DEFAULT_SITE_CONFIG = {
    'newsensations.com': NEWSENSATIONS_HOST,
    'www.newsensations.com': NEWSENSATIONS_HOST
    // Future hosts (empty scaffolding — do not invent selectors yet):
    // 'bang.com': { isVr: false, selectors: [] },
    // 'www.bang.com': { isVr: false, selectors: [] },
  };

  function getFilenameConfig() {
    const saved = GM_getValue('filenameConfig', null);
    if (!saved) return DEFAULT_FILENAME_CONFIG;
    return {
      global: Object.assign({}, DEFAULT_FILENAME_CONFIG.global, saved.global || {}),
      perHost: Object.assign({}, DEFAULT_FILENAME_CONFIG.perHost, saved.perHost || {})
    };
  }
  function setFilenameConfig(cfg) {
    GM_setValue('filenameConfig', cfg);
  }
  function getSiteConfig() {
    const saved = GM_getValue('siteConfig', null);
    if (!saved) return DEFAULT_SITE_CONFIG;
    // Built-in hosts win unless the operator overwrote that host key.
    return Object.assign({}, DEFAULT_SITE_CONFIG, saved);
  }
  function setSiteConfig(cfg) {
    GM_setValue('siteConfig', cfg);
  }
  function getSiteConfigForHost(host) {
    const all = getSiteConfig();
    if (all[host]) return all[host];
    if (host.startsWith('www.') && all[host.slice(4)]) return all[host.slice(4)];
    if (!host.startsWith('www.') && all['www.' + host]) return all['www.' + host];
    return null;
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
    // Dedupe while preserving order (CSS+XPath fallbacks may double-hit)
    const seen = Object.create(null);
    norm = norm.filter((n) => {
      if (seen[n]) return false;
      seen[n] = true;
      return true;
    });
    if (norm.length > MAX_ACTORS) {
      console.warn('Zephyr: truncating actors to', MAX_ACTORS, norm);
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

  function detectVr(cfg) {
    if (cfg && cfg.isVr === true) return true;
    if (cfg && cfg.isVr === false) return false;
    const href = (window.location.href || '').toLowerCase();
    if (href.includes('/vr/')) return true;
    const badges = cfg && Array.isArray(cfg.vrSignals) ? cfg.vrSignals : ['180°', 'SBS', 'MKX200'];
    const bodyText = (document.body && document.body.innerText) || '';
    for (const b of badges) {
      if (bodyText.indexOf(b) !== -1) return true;
    }
    if (/\bVR\b/.test(bodyText) && /virtual\s*reality/i.test(bodyText)) return true;
    return false;
  }

  function getNodeValue(node, attr) {
    if (!node) return null;
    if (attr === 'text') {
      const t = (node.textContent || '').trim().replace(/\s+/g, ' ');
      return t || null;
    }
    const val = node.getAttribute(attr);
    return val ? val.trim() : null;
  }

  function evalXPathNodes(xpath) {
    const out = [];
    try {
      const snap = document.evaluate(
        xpath,
        document,
        null,
        XPathResult.ORDERED_NODE_SNAPSHOT_TYPE,
        null
      );
      for (let i = 0; i < snap.snapshotLength; i++) {
        out.push(snap.snapshotItem(i));
      }
    } catch (e) {
      console.warn('Zephyr: bad xpath', xpath, e);
    }
    return out;
  }

  function collectSelectorValues(sel) {
    if (sel.fixed != null && String(sel.fixed).length) {
      return [String(sel.fixed)];
    }
    const attr = sel.attr || 'text';
    let nodes = [];
    if (sel.xpath) nodes = evalXPathNodes(sel.xpath);
    else if (sel.css) nodes = Array.from(document.querySelectorAll(sel.css));
    return nodes.map((n) => getNodeValue(n, attr)).filter(Boolean);
  }

  function inferResolutionFromPage() {
    const haystacks = [];
    document.querySelectorAll('a[href], option, button, [data-quality], .download_quality, .quality').forEach((el) => {
      haystacks.push(el.getAttribute('href') || '');
      haystacks.push(el.textContent || '');
      haystacks.push(el.getAttribute('data-quality') || '');
    });
    // Prefer higher resolutions when multiple appear
    const order = ['4k', '2160', '2k', '1440', '1080', '720', '540', '480'];
    const joined = haystacks.join(' ').toLowerCase();
    for (const token of order) {
      if (joined.includes(token)) return normalizeResolution(token);
    }
    return null;
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
      const { name, multi = false } = sel;
      if (!name) continue;
      const values = collectSelectorValues(sel);
      if (!values.length) continue;

      if (multi || name === 'actors') {
        if (name === 'actors') result.actors.push(...values);
        continue;
      }

      const value = values[0];
      if (name === 'studio' && !result.studio) result.studio = value;
      else if (name === 'title' && !result.title) result.title = value;
      else if (name === 'resolution' && !result.resolution) result.resolution = value;
      else if ((name === 'downloadUrl' || name === 'url') && !result.url) result.url = value;
    }

    if (!result.studio && cfg.studioFixed) {
      result.studio = cfg.studioFixed;
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
        if (!result.resolution) {
          result.resolution = normalizeResolution(result.url) || normalizeResolution(path);
        }
      } catch (e) {
        /* ignore */
      }
    }

    if (!result.resolution) {
      result.resolution = inferResolutionFromPage();
    }

    result.isVr = detectVr(cfg);
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
      console.warn(
        'Zephyr: incomplete metadata; leaving document.title alone.',
        { actors: meta.actors, studio: meta.studio, title: meta.title }
      );
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
    const current = all[host] || getSiteConfigForHost(host) || { isVr: false, selectors: [] };
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
    // Late-hydrated tour markup (actors/title injected after first paint)
    const bodyObs = new MutationObserver(function () {
      scheduleApply();
    });
    if (document.body) {
      bodyObs.observe(document.body, { childList: true, subtree: true });
    }
    setInterval(resistOverwrite, 2000);
  }
})();
