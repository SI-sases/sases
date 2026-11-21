// static/modules/markdown.js
// 轻量 Markdown 渲染：代码块/行内代码/粗体/标题/列表/链接。先转义，再生成固定标签。
function esc(s) {
  return String(s == null ? '' : s)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

export function renderMarkdown(text) {
  let src = String(text == null ? '' : text);
  const blocks = [];

  src = src.replace(/```([A-Za-z0-9_+-]*)\n([\s\S]*?)```/g, function (m, lang, code) {
    const i = blocks.length;
    blocks.push({ lang: lang || 'text', code: code.replace(/\n$/, '') });
    return '\u0000CODE' + i + '\u0000';
  });

  let html = esc(src);

  // 标题
  html = html.replace(/^### (.+)$/gm, '<div class="md-h3">$1</div>');
  html = html.replace(/^## (.+)$/gm, '<div class="md-h2">$1</div>');
  html = html.replace(/^# (.+)$/gm, '<div class="md-h1">$1</div>');

  // 列表
  html = html.replace(/^(?:- |\* )(.+)$/gm, '<div class="md-li">• $1</div>');
  html = html.replace(/^(\d+)\. (.+)$/gm, '<div class="md-li">$1. $2</div>');

  // 行内代码、粗体、斜体
  html = html.replace(/`([^`\n]+)`/g, '<code class="inline-code">$1</code>');
  html = html.replace(/\*\*([^*\n]+)\*\*/g, '<strong>$1</strong>');
  html = html.replace(/\*([^*\n]+)\*/g, '<em>$1</em>');

  // 链接（只允许 http/https）
  html = html.replace(/\[([^\]]+)\]\((https?:\/\/[^\s)]+)\)/g,
    '<a href="$2" target="_blank" rel="noopener noreferrer">$1</a>');

  // 代码块占位符
  html = html.replace(/\u0000CODE(\d+)\u0000/g, function (m, idx) {
    const b = blocks[Number(idx)];
    if (!b) return '';
    const lang = esc(b.lang);
    return '<div class="code-block"><div class="code-head"><span class="code-lang">' + lang +
      '</span><button class="code-copy" type="button">复制</button></div>' +
      '<pre><code>' + esc(b.code) + '</code></pre></div>';
  });

  return html;
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
      btn.textContent = '已复制';
      setTimeout(function () { btn.textContent = '复制'; }, 1200);
    } catch (err) {
      console.warn('[markdown] copy failed', err);
    }
  });
}
