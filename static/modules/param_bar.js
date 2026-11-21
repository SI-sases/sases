// 参数胶囊栏（v0.37.0）
// 用法：initParamBar() 初始化；getParamMaxSteps() 读取当前值

const STORAGE_KEY = 'sases_max_steps';
const DEFAULT_STEPS = 8;
const MODE_KEY = 'sases_agent_mode';
const MODE_PRESETS = [
  { value: 'auto', label: '⚡ 自动' },
  { value: 'fast', label: '⚡ 快速' },
  { value: 'strict', label: '🎯 严格' },
];
let _mode = null;

const PRESETS = [
  { value: 5, label: '5步', desc: '快速任务' },
  { value: 8, label: '8步', desc: '默认' },
  { value: 15, label: '15步', desc: '复杂任务' },
  { value: -1, label: '不限', desc: '谨慎使用' },
];

let _currentValue = null;

function _read() {
  const raw = localStorage.getItem(STORAGE_KEY);
  if (raw === null) return DEFAULT_STEPS;
  const v = parseInt(raw, 10);
  if (isNaN(v)) return DEFAULT_STEPS;
  return v;
}

function _write(v) {
  localStorage.setItem(STORAGE_KEY, String(v));
  _currentValue = v;
}

function _labelOf(v) {
  if (v === -1) return '不限';
  return v + '步';
}

function _updatePill() {
  const pill = document.getElementById('param-rounds');
  if (!pill) return;
  const v = getParamMaxSteps();
  pill.textContent = '⚙️ ' + _labelOf(v);
  pill.classList.remove('param-modified', 'param-unlimited');
  if (v === -1) {
    pill.classList.add('param-unlimited');
  } else if (v !== DEFAULT_STEPS) {
    pill.classList.add('param-modified');
  }
}

function _ensureMenu() {
  let menu = document.getElementById('param-menu');
  if (menu) return menu;
  menu = document.createElement('div');
  menu.id = 'param-menu';
  menu.className = 'param-menu';
  document.body.appendChild(menu);
  return menu;
}

function _renderMenu(menu, onPick) {
  menu.innerHTML = '';
  PRESETS.forEach(p => {
    const item = document.createElement('div');
    item.className = 'param-menu-item' + (p.value === _currentValue ? ' active' : '');
    item.innerHTML = p.label + '<span class="param-desc">' + p.desc + '</span>';
    item.onclick = () => {
      onPick(p.value);
      _hideMenu();
    };
    menu.appendChild(item);
  });
}

function _showMenu(anchorEl) {
  const menu = _ensureMenu();
  _renderMenu(menu, (v) => {
    _write(v);
    _updatePill();
  });
  const rect = anchorEl.getBoundingClientRect();
  menu.style.left = rect.left + 'px';
  menu.style.bottom = (window.innerHeight - rect.top + 6) + 'px';
  menu.classList.add('show');
}

function _hideMenu() {
  const menu = document.getElementById('param-menu');
  if (menu) menu.classList.remove('show');
}

export function initParamBar() {
  _currentValue = _read();
  _mode = _readMode();
  const pill = document.getElementById('param-rounds');
  if (!pill) return;
  _updatePill();
  _updateModePill();
  const modePill = document.getElementById('mode-pill');
  if (modePill && !modePill._sasesModeBound) {
    modePill._sasesModeBound = true;
    modePill.onclick = (e) => {
      e.stopPropagation();
      const idx = MODE_PRESETS.findIndex(p => p.value === getAgentMode());
      const next = MODE_PRESETS[(idx + 1) % MODE_PRESETS.length];
      localStorage.setItem(MODE_KEY, next.value);
      _mode = next.value;
      _updateModePill();
    };
  }
  if (!pill._sasesParamBound) {
    pill._sasesParamBound = true;
    pill.onclick = (e) => {
      e.stopPropagation();
      const menu = document.getElementById('param-menu');
      if (menu && menu.classList.contains('show')) {
        _hideMenu();
      } else {
        _showMenu(pill);
      }
    };
  }
  if (!window._sasesParamGlobalBound) {
    window._sasesParamGlobalBound = true;
    document.addEventListener('click', () => _hideMenu());
  }
}

export function getParamMaxSteps() {
  if (_currentValue === null) _currentValue = _read();
  return _currentValue;
}

function _readMode() {
  const raw = localStorage.getItem(MODE_KEY);
  if (raw === 'fast' || raw === 'strict' || raw === 'auto') return raw;
  return 'auto';
}

function _updateModePill() {
  const el = document.getElementById('mode-pill');
  if (!el) return;
  const v = getAgentMode();
  const p = MODE_PRESETS.find(x => x.value === v) || MODE_PRESETS[0];
  el.textContent = p.label;
  el.classList.toggle('param-modified', v !== 'auto');
}

export function getAgentMode() {
  if (_mode === null) _mode = _readMode();
  return _mode;
}

export function setParamMaxSteps(v) {
  _write(v);
  _updatePill();
}

// 挂到 window 供 chat.js 非模块化调用
if (typeof window !== 'undefined') {
  window.sasesParamBar = { initParamBar, getParamMaxSteps, setParamMaxSteps };
}