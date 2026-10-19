// ==UserScript==
// @name         Video Library Title Builder
// @namespace    local.video.library
// @version      1.0.0
// @description  Extracts site-specific video metadata and rewrites document.title before downloading.
// @match        *://*/*
// @run-at       document-idle
// @grant        none
// ==/UserScript==

(() => {
  "use strict";

  const VALID_RESOLUTIONS = new Set([
    "480p", "540p", "720p", "1080p",
    "2K", "3K", "4K", "5K", "6K", "7K", "8K"
  ]);

  /*
   * Add one rule for each supported site or page layout.
   *
   * A field may be:
   *   1. A CSS selector string
   *   2. An array of fallback CSS selectors
   *   3. A function that returns text or an array of presenter names
   *
   * Use more than one rule for a site when it has multiple page layouts.
   */
  const SITE_RULES = [
    {
      id: "example-university-videos",
      match: ({ hostname, pathname }) =>
        hostname === "video.example.edu" && pathname.startsWith("/watch/"),

      presenters: [
        ".presenter-name",
        ".speaker-name",
        '[itemprop="performer"] [itemprop="name"]'
      ],

      organization: [
        ".organization-name",
        ".studio-name",
        ".university-name",
        '[itemprop="publisher"] [itemprop="name"]'
      ],

      videoTitle: [
        ".video-title",
        "main h1",
        'meta[property="og:title"]'
      ],

      resolution: [
        ".video-resolution",
        '[data-resolution]'
      ]
    },

    /*
    {
      id: "another-site",
      match: ({ hostname, pathname }) =>
        hostname.endsWith("another-site.org") && pathname.includes("/videos/"),

      presenters: () =>
        [...document.querySelectorAll(".speaker-card .name")]
          .map(element => element.textContent),

      organization: ".institution",
      videoTitle: "h1.video-heading",

      // Use this only if the page itself exposes the selected resolution.
      resolution: () =>
        document.querySelector(".quality.selected")?.textContent || ""
    },
    */
  ];

  function normalizeWhitespace(value) {
    return String(value ?? "")
      .replace(/\u00a0/g, " ")
      .replace(/\s+/g, " ")
      .trim();
  }

  function elementValue(element) {
    if (!element) return "";

    const attributeNames = [
      "content",
      "datetime",
      "data-name",
      "data-title",
      "data-resolution",
      "title",
      "aria-label"
    ];

    for (const name of attributeNames) {
      const value = element.getAttribute?.(name);
      if (normalizeWhitespace(value)) return normalizeWhitespace(value);
    }

    return normalizeWhitespace(element.textContent);
  }

  function readAll(selector) {
    try {
      return [...document.querySelectorAll(selector)]
        .map(elementValue)
        .filter(Boolean);
    } catch (error) {
      console.warn("[Video Library] Invalid selector:", selector, error);
      return [];
    }
  }

  function readFirst(definition) {
    if (typeof definition === "function") {
      const result = definition();
      return Array.isArray(result)
        ? normalizeWhitespace(result.find(Boolean))
        : normalizeWhitespace(result);
    }

    const selectors = Array.isArray(definition) ? definition : [definition];

    for (const selector of selectors.filter(Boolean)) {
      const values = readAll(selector);
      if (values.length) return values[0];
    }

    return "";
  }

  function readPresenters(definition) {
    if (typeof definition === "function") {
      const result = definition();
      const values = Array.isArray(result) ? result : [result];
      return values.map(normalizeWhitespace).filter(Boolean).slice(0, 3);
    }

    const selectors = Array.isArray(definition) ? definition : [definition];

    for (const selector of selectors.filter(Boolean)) {
      const values = readAll(selector);
      if (values.length) return values.slice(0, 3);
    }

    return [];
  }

  function titleCase(value) {
    return normalizeWhitespace(value)
      .toLocaleLowerCase("en-US")
      .replace(/(^|[\s'’.-])([a-z])/g, (_, prefix, letter) =>
        prefix + letter.toLocaleUpperCase("en-US")
      );
  }

  function sanitizeSection(value) {
    return normalizeWhitespace(value)
      .replace(/[<>:"/\\|?*\u0000-\u001f]/g, " ")
      .replace(/[–—-]+/g, " ")
      .replace(/\.+/g, " ")
      .replace(/\s+/g, " ")
      .trim();
  }

  function formatPresenters(names) {
    return names
      .slice(0, 3)
      .map(name => titleCase(sanitizeSection(name)).replace(/\s+/g, "."))
      .filter(Boolean)
      .join(".And.");
  }

  function formatOrganization(value) {
    return titleCase(sanitizeSection(value)).replace(/\s+/g, "");
  }

  function formatVideoTitle(value) {
    return titleCase(sanitizeSection(value)).replace(/\s+/g, ".");
  }

  function normalizeResolution(value) {
    const text = normalizeWhitespace(value);
    const match = text.match(/(?:^|\b)(480p|540p|720p|1080p|[2-8]k)(?:\b|$)/i);
    if (!match) return "";

    const candidate = /p$/i.test(match[1])
      ? match[1].toLowerCase()
      : match[1].toUpperCase();

    return VALID_RESOLUTIONS.has(candidate) ? candidate : "";
  }

  function findResolutionOnPage() {
    const searchableText = [
      document.querySelector('meta[property="og:video:height"]')?.content,
      document.querySelector('meta[name="video:resolution"]')?.content,
      document.body?.innerText
    ].filter(Boolean).join(" ");

    const heightMatch = searchableText.match(/(?:^|\D)(480|540|720|1080)(?:\D|$)/);
    if (heightMatch) return `${heightMatch[1]}p`;

    return normalizeResolution(searchableText);
  }

  function findRule() {
    const context = {
      href: location.href,
      hostname: location.hostname,
      pathname: location.pathname,
      search: location.search
    };

    return SITE_RULES.find(rule => {
      try {
        return rule.match(context);
      } catch (error) {
        console.warn(`[Video Library] Rule match failed: ${rule.id}`, error);
        return false;
      }
    });
  }

  function buildDownloadTitle(rule) {
    const presenters = readPresenters(rule.presenters);
    const organization = readFirst(rule.organization);
    const videoTitle = readFirst(rule.videoTitle);
    const resolution =
      normalizeResolution(readFirst(rule.resolution)) || findResolutionOnPage();

    const formatted = {
      presenters: formatPresenters(presenters),
      organization: formatOrganization(organization),
      videoTitle: formatVideoTitle(videoTitle),
      resolution
    };

    const missing = Object.entries(formatted)
      .filter(([, value]) => !value)
      .map(([field]) => field);

    if (missing.length) {
      console.warn(`[Video Library] ${rule.id} missing: ${missing.join(", ")}`, {
        presenters,
        organization,
        videoTitle,
        resolution
      });
      return "";
    }

    return [
      formatted.presenters,
      formatted.organization,
      formatted.videoTitle,
      formatted.resolution
    ].join(".");
  }

  let originalTitle = document.title;
  let lastGeneratedTitle = "";
  let updateTimer;

  function updateTitle() {
    const rule = findRule();
    if (!rule) return;

    const generatedTitle = buildDownloadTitle(rule);
    if (!generatedTitle) return;

    if (document.title !== generatedTitle) {
      document.title = generatedTitle;
      lastGeneratedTitle = generatedTitle;
      console.info(`[Video Library] Title set by ${rule.id}:`, generatedTitle);
    }
  }

  function scheduleUpdate() {
    clearTimeout(updateTimer);
    updateTimer = setTimeout(updateTitle, 500);
  }

  updateTitle();

  // Supports delayed content and single-page applications.
  const observer = new MutationObserver(scheduleUpdate);
  observer.observe(document.documentElement, {
    childList: true,
    subtree: true
  });

  // Useful manual controls in the browser console.
  window.videoLibraryTitle = {
    update: updateTitle,
    restore() {
      document.title = originalTitle;
    },
    current() {
      return lastGeneratedTitle;
    }
  };
})();
