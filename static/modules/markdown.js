// static/modules/markdown.js
// 轻量 Markdown 渲染：先转义，再生成固定标签。
// 支持标题、段落、粗体、斜体、行内代码、代码块、列表、引用、分割线、链接。
import { t } from './i18n.js';

function esc(s) {
  return String(s == null ? '' : s)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

function inline(text) {
  let s = text;
  s = s.replace(/`([^`\n]+)`/g, '<code class="inline-code">$1</code>');
  s = s.replace(/\*\*([^*\n]+)\*\*/g, '<strong>$1</strong>');
  s = s.replace(/(^|[^*])\*([^*\n]+)\*/g, '$1<em>$2</em>');
  s = s.replace(/\[([^\]]+)\]\((https?:\/\/[^\s)]+)\)/g,
    '<a href="$2" target="_blank" rel="noopener noreferrer">$1</a>');
  return s;
}

export function renderMarkdown(text) {
  let src = String(text == null ? '' : text);
  const blocks = [];

  src = src.replace(/```([A-Za-z0-9_+-]*)\n([\s\S]*?)```/g, function (m, lang, code) {
    const i = blocks.length;
    blocks.push({ lang: lang || 'text', code: code.replace(/\n$/, '') });
    return '\u0000CODE' + i + '\u0000';
  });

  const html = esc(src);
  const out = [];
  let para = [];

  function flush() {
    if (!para.length) return;
    out.push('<p class="md-p">' + para.join('<br>') + '</p>');
    para = [];
  }

  for (const line of html.split('\n')) {
    const trimmed = line.trim();
    if (!trimmed) {
      flush();
      continue;
    }
    if (/^\u0000CODE\d+\u0000$/.test(trimmed)) {
      flush();
      out.push(trimmed);
      continue;
    }
    if (/^### (.+)$/.test(trimmed)) {
      flush();
      out.push('<div class="md-h3">' + inline(trimmed.slice(4)) + '</div>');
      continue;
    }
    if (/^## (.+)$/.test(trimmed)) {
      flush();
      out.push('<div class="md-h2">' + inline(trimmed.slice(3)) + '</div>');
      continue;
    }
    if (/^# (.+)$/.test(trimmed)) {
      flush();
      out.push('<div class="md-h1">' + inline(trimmed.slice(2)) + '</div>');
      continue;
    }
    if (/^&gt; (.+)$/.test(trimmed)) {
      flush();
      out.push('<blockquote class="md-quote">' + inline(trimmed.slice(5)) + '</blockquote>');
      continue;
    }
    if (/^(?:-{3,}|\*{3,}|_{3,})$/.test(trimmed)) {
      flush();
      out.push('<hr class="md-hr">');
      continue;
    }
    if (/^(?:- |\* )(.+)$/.test(trimmed)) {
      flush();
      out.push('<div class="md-li">• ' + inline(trimmed.slice(2)) + '</div>');
      continue;
    }
    if (/^\d+\. (.+)$/.test(trimmed)) {
      flush();
      const m = trimmed.match(/^(\d+)\. (.+)$/);
      out.push('<div class="md-li">' + m[1] + '. ' + inline(m[2]) + '</div>');
      continue;
    }
    para.push(inline(trimmed));
  }
  flush();

  let result = out.join('\n');
  result = result.replace(/\u0000CODE(\d+)\u0000/g, function (m, idx) {
    const b = blocks[Number(idx)];
    if (!b) return '';
    const lang = esc(b.lang);
    return '<div class="code-block"><div class="code-head"><span class="code-lang">' + lang +
      '</span><button class="code-copy" type="button">' + t('md_copy') + '</button></div>' +
      '<pre><code>' + esc(b.code) + '</code></pre></div>';
  });
  return result;
}

if (typeof document !== 'undefined' && !window.__sasesMdCopyBound) {
  window.__sasesMdCopyBound = true;
  document.addEventListener('click', function (e) {
    const btn = e.target && e.target.closest ? e.target.closest('.code-copy') : null;
    if (!btn) return;
    const block = btn.closest('.code-block');
    const code = block ? block.querySelector('code') : null;
    const text = code ? code.textContent : '';
    try {
      if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(text);
      } else {
        const ta = document.createElement('textarea');
        ta.value = text;
        document.body.appendChild(ta);
        ta.select();
        document.execCommand('copy');
        ta.remove();
      }
      btn.textContent = t('md_copied');
      setTimeout(function () { btn.textContent = t('md_copy'); }, 1200);
    } catch (err) {
      console.warn('[markdown] copy failed', err);
    }
  });
}
