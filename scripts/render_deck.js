// Runs inside the page render_deck.py builds; `KIT` holds its settings. The URL's hash picks
// the mode: #check measures every slide into a report element, #slide=<id> shows one
// slide for a screenshot, and #sheet lays every slide out as a contact sheet.
(() => {
  const TEXT = 'h1,h2,h3,p,li,th,td';
  const WIDTH = 1920;
  const HEIGHT = 1080;
  const SIDE = 64;
  const FOOTER_TOP = 952;
  const FOOTER_BOTTOM = 1016;
  const FOOTER_MAX_PX = 24;
  const MIN_PX = 24;
  const LARGE_PX = 44;
  const slides = [...document.querySelectorAll('#kit-slides > section')];
  const mode = location.hash.slice(1);

  if (mode.startsWith('slide=')) {
    const id = decodeURIComponent(mode.slice('slide='.length));
    for (const slide of slides) slide.style.display = slide.id === id ? '' : 'none';
    return;
  }
  if (mode === 'sheet') {
    buildSheet();
    return;
  }
  document.fonts.ready.then(() => {
    const report = slides.map(measure);
    const pre = document.createElement('pre');
    pre.id = 'kit-report';
    pre.textContent = JSON.stringify(report);
    document.body.append(pre);
  });

  function buildSheet() {
    const sheet = document.createElement('div');
    const cellWidth = WIDTH * KIT.scale;
    const cellHeight = HEIGHT * KIT.scale;
    sheet.style.cssText = `display:grid;grid-template-columns:repeat(4, ${cellWidth}px);gap:${KIT.gap}px;padding:${KIT.gap}px;font:20px/1.2 sans-serif;color:#fff`;
    for (const slide of slides) {
      const cell = document.createElement('div');
      const frame = document.createElement('div');
      frame.style.cssText = `width:${cellWidth}px;height:${cellHeight}px;overflow:hidden`;
      slide.style.transform = `scale(${KIT.scale})`;
      slide.style.transformOrigin = 'top left';
      frame.append(slide);
      const label = document.createElement('div');
      label.style.cssText = `height:${KIT.label}px;padding-top:8px`;
      label.textContent = KIT.labels[slide.id] || slide.id;
      cell.append(frame, label);
      sheet.append(cell);
    }
    document.body.replaceChildren(sheet);
  }

  function measure(slide) {
    const box = slide.getBoundingClientRect();
    const at = (rect) => ({
      left: rect.left - box.left,
      top: rect.top - box.top,
      right: rect.right - box.left,
      bottom: rect.bottom - box.top,
    });
    const problems = [];
    if (slide.scrollHeight > HEIGHT + 1 || slide.scrollWidth > WIDTH + 1) {
      problems.push(
        `content runs to ${slide.scrollWidth}x${slide.scrollHeight}, past the 1920x1080 slide; split it`,
      );
    }
    const leaves = [...slide.querySelectorAll(TEXT)].filter(
      (element) =>
        !element.closest('aside') && !element.querySelector(TEXT) && element.textContent.trim(),
    );
    const lines = [];
    const outside = [];
    for (const element of leaves) {
      const style = getComputedStyle(element);
      const px = parseFloat(style.fontSize);
      const snippet = `\`${element.textContent.trim().slice(0, 40)}\``;
      if (element.scrollWidth > element.clientWidth + 2) {
        problems.push(`${snippet} is wider than its box; widen it or shorten the longest word`);
      }
      if (element.style.height && element.scrollHeight > element.clientHeight + 2) {
        problems.push(`${snippet} is taller than its fixed height; drop the height`);
      }
      if (px < MIN_PX) problems.push(`${snippet} is ${px}px; nothing under ${MIN_PX}px`);
      const rects = textRects(element).map(at);
      const isFooter = px <= FOOTER_MAX_PX && style.position === 'absolute';
      const lowest = isFooter ? FOOTER_BOTTOM : FOOTER_TOP;
      if (rects.some((r) => r.left < SIDE - 1 || r.right > WIDTH - SIDE + 1 || r.top < SIDE - 1 || r.bottom > lowest + 1)) {
        outside.push(snippet);
      }
      for (const rect of rects) lines.push({ element, rect, snippet });
      const ratio = contrast(element, slide);
      const minimum = px >= LARGE_PX ? 3 : 4.5;
      if (ratio !== null && ratio < minimum) {
        problems.push(`${snippet} has contrast ${ratio.toFixed(1)}:1 (min ${minimum}:1)`);
      }
    }
    if (outside.length) {
      const more = outside.length > 3 ? ` and ${outside.length - 3} more` : '';
      problems.push(`${outside.slice(0, 3).join(', ')}${more} sit outside the margins or in the footer band`);
    }
    problems.push(...overlaps(lines));
    const heading = slide.querySelector('h1, h2');
    const headingLines = heading ? textRects(heading).map(at) : [];
    const headingRect = headingLines.length
      ? {
          left: Math.min(...headingLines.map((r) => r.left)),
          top: Math.min(...headingLines.map((r) => r.top)),
          bottom: Math.max(...headingLines.map((r) => r.bottom)),
        }
      : null;
    const titleLines = new Set(headingLines.map((r) => Math.round(r.top))).size;
    const maxLines = heading && heading.tagName === 'H1' ? 3 : 2;
    if (titleLines > maxLines) {
      problems.push(`title wraps to ${titleLines} lines (max ${maxLines}); shorten it`);
    }
    return {
      id: slide.id,
      titleTop: headingRect ? headingRect.top : null,
      titleLeft: headingRect ? headingRect.left : null,
      titleBottom: headingRect ? headingRect.bottom : null,
      titleLines,
      bodyBottom: flowBottom(slide, at),
      bodyTop: flowTop(slide, heading, at),
      problems: [...new Set(problems)],
    };
  }

  function textRects(element) {
    const range = document.createRange();
    range.selectNodeContents(element);
    return [...range.getClientRects()].filter((rect) => rect.width > 1 && rect.height > 1);
  }

  function overlaps(lines) {
    const found = [];
    for (let i = 0; i < lines.length; i++) {
      for (let j = i + 1; j < lines.length; j++) {
        const [a, b] = [lines[i], lines[j]];
        if (a.element === b.element || a.element.contains(b.element) || b.element.contains(a.element)) continue;
        const width = Math.min(a.rect.right, b.rect.right) - Math.max(a.rect.left, b.rect.left);
        const height = Math.min(a.rect.bottom, b.rect.bottom) - Math.max(a.rect.top, b.rect.top);
        if (width > 2 && height > 2) found.push(`${a.snippet} overlaps ${b.snippet}`);
      }
    }
    return found;
  }

  function contrast(element, slide) {
    const foreground = rgba(getComputedStyle(element).color);
    const background = backdrop(element, slide);
    if (!foreground || !background || isOverMedia(element, slide)) return null;
    return ratio(blend(foreground, background), background);
  }

  function backdrop(element, slide) {
    for (let node = element; node; node = node.parentElement) {
      const style = getComputedStyle(node);
      if (style.backgroundImage !== 'none') return null;
      const colour = rgba(style.backgroundColor);
      if (colour && colour[3] > 0) return colour[3] < 1 ? null : colour;
      if (node === slide) return null;
    }
    return null;
  }

  function isOverMedia(element, slide) {
    const rect = element.getBoundingClientRect();
    return [...slide.querySelectorAll('img, svg, x-shape')].some((media) => {
      const isBelow = media.compareDocumentPosition(element) & Node.DOCUMENT_POSITION_FOLLOWING;
      const other = media.getBoundingClientRect();
      const meets = other.left < rect.right && other.right > rect.left && other.top < rect.bottom && other.bottom > rect.top;
      return isBelow && meets && !media.contains(element);
    });
  }

  function flowBottom(slide, at) {
    let bottom = 0;
    for (const element of slide.querySelectorAll('*')) {
      if (element.closest('aside') || isPinned(element, slide)) continue;
      if (element.matches(`${TEXT}, img, svg, table, x-shape`) || hasPaint(element)) {
        bottom = Math.max(bottom, at(element.getBoundingClientRect()).bottom);
      }
    }
    return bottom;
  }

  function flowTop(slide, heading, at) {
    const next = [...slide.children].find(
      (child) => child !== heading && child.tagName !== 'ASIDE' && !isPinned(child, slide),
    );
    return next ? firstPaint(next, at) : null;
  }

  function firstPaint(element, at) {
    const painted = [element, ...element.querySelectorAll('*')].filter(
      (node) => node.matches(`${TEXT}, img, svg, table, x-shape`) || hasPaint(node),
    );
    return painted.length ? Math.min(...painted.map((node) => at(node.getBoundingClientRect()).top)) : null;
  }

  function isPinned(element, slide) {
    for (let node = element; node && node !== slide; node = node.parentElement) {
      if (getComputedStyle(node).position === 'absolute') return true;
    }
    return false;
  }

  function hasPaint(element) {
    const style = getComputedStyle(element);
    const colour = rgba(style.backgroundColor);
    return (colour && colour[3] > 0) || style.borderTopStyle !== 'none';
  }

  function rgba(value) {
    const parts = value.match(/[\d.]+/g);
    if (!parts || parts.length < 3) return null;
    const [r, g, b, a] = parts.map(Number);
    return [r, g, b, a === undefined ? 1 : a];
  }

  function blend(top, bottom) {
    return [0, 1, 2].map((i) => top[i] * top[3] + bottom[i] * (1 - top[3])).concat(1);
  }

  function luminance(colour) {
    const linear = colour.slice(0, 3).map((channel) => {
      const value = channel / 255;
      return value <= 0.04045 ? value / 12.92 : ((value + 0.055) / 1.055) ** 2.4;
    });
    return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2];
  }

  function ratio(first, second) {
    const [lighter, darker] = [luminance(first), luminance(second)].sort((x, y) => y - x);
    return (lighter + 0.05) / (darker + 0.05);
  }
})();
