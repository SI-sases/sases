import shutil
from datetime import datetime

HTML = "static/index.html"
JS = "static/modules/sidebar.js"

HTML_OLD = '''          <div class="side-menu-item" id="menu-mini-apps">
            <span class="menu-icon">🧩</span>
            <span>小程序</span>
            <span class="menu-arrow">›</span>
          </div>'''

HTML_NEW = HTML_OLD + '''
          <div class="side-menu-item" id="menu-external-api">
            <span class="menu-icon">🔌</span>
            <span>外部 API</span>
            <span class="menu-arrow">›</span>
          </div>'''

JS_OLD = """  if (menuMiniApps) {
    menuMiniApps.addEventListener('click', () => {
      closeSideDrawer();
      window.openSubpage(t('mini_apps'), `<div class="subpage-placeholder">${t('coming_soon')}</div>`);
    });
  }"""

JS_NEW = JS_OLD + """

  const menuExternalApi = document.getElementById('menu-external-api');
  if (menuExternalApi) {
    menuExternalApi.addEventListener('click', () => {
      closeSideDrawer();
      if (typeof window.__openExternalApiPage === 'function') {
        window.__openExternalApiPage();
      }
    });
  }"""

def patch(path, old, new, label):
    content = open(path, "r", encoding="utf-8").read()
    if "menu-external-api" in content and label == "sidebar.js":
        print(label + ": already exists, skip")
        return
    if 'id="menu-external-api"' in content and label == "index.html":
        print(label + ": already exists, skip")
        return
    if old not in content:
        print("ERROR: " + label + " anchor not found")
        return
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    shutil.copy2(path, path + ".bak_p2_6_" + ts)
    content = content.replace(old, new, 1)
    open(path, "w", encoding="utf-8").write(content)
    print(label + ": patched")

def main():
    patch(HTML, HTML_OLD, HTML_NEW, "index.html")
    patch(JS, JS_OLD, JS_NEW, "sidebar.js")

if __name__ == "__main__":
    main()