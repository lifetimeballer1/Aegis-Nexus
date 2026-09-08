"""Real WebGL rendering and boot-failure checks for the Intelligence Web."""
import json
import os
from pathlib import Path

from playwright.sync_api import sync_playwright

BASE = os.environ.get('SMOKE_BASE_URL', 'http://127.0.0.1:4173')
OUTPUT = Path(os.environ.get('SMOKE_OUTPUT_DIR', 'artifacts/intelligence-web'))


def verify_render(page, name):
    errors, failed, responses = [], [], {}
    page.on('pageerror', lambda error: errors.append(str(error)))
    page.on('requestfailed', lambda request: failed.append(request.url))
    page.on('response', lambda response: responses.update({response.url.split('?')[0]: response.status}))
    page.goto(BASE + '/intelligence-web.html', wait_until='networkidle')
    page.wait_for_function('''() => {
        const g = window.__gpGraph;
        return g && g.graphData().nodes.length && g.graphData().links.length
            && g.renderer().info.render.calls > 0;
    }''')
    # The former guard falsely reported failure at 15 seconds.
    page.wait_for_timeout(16000)
    assert page.locator('#loading').is_hidden()
    state = page.evaluate('''() => {
        const g = window.__gpGraph, data = g.graphData(), renderer = g.renderer();
        const gl = renderer.getContext();
        let meshes = 0;
        g.scene().traverse(object => { if (object.isMesh && object.visible) meshes++; });
        return {nodes: data.nodes.length, links: data.links.length, meshes,
            calls: renderer.info.render.calls, triangles: renderer.info.render.triangles,
            width: gl.drawingBufferWidth, height: gl.drawingBufferHeight,
            contextLost: gl.isContextLost(), webglError: gl.getError(),
            finitePositions: data.nodes.every(n => [n.x,n.y,n.z].every(Number.isFinite))};
    }''')
    assert responses[BASE + '/data/intelligence_graph.json'] == 200
    assert state['nodes'] > 0 and state['links'] > 0 and state['meshes'] > 0
    assert state['calls'] > 0 and state['triangles'] > 0
    assert state['width'] > 0 and state['height'] > 0
    assert state['finitePositions'] and not state['contextLost'] and state['webglError'] == 0
    assert not errors, errors
    assert not failed, failed
    page.locator('#control-toggle').click()
    assert page.locator('#controls').evaluate("el => el.classList.contains('collapsed')")
    page.locator('#labels-toggle').evaluate('el => el.click()')
    page.screenshot(path=str(OUTPUT / (name + '.png')))
    print('RENDER PASS ' + name + ': ' + json.dumps(state), flush=True)
    page.locator('#control-toggle').click()
    verify_controls(page, name)
    assert not errors, errors


def verify_controls(page, name):
    graph = 'window.__gpGraph'
    original = page.evaluate(f'{graph}.graphData().nodes.length')
    page.locator('[data-kind="economic"]').click()
    assert page.locator('[data-kind="economic"]').get_attribute('aria-pressed') == 'true'
    assert page.locator('#node-select option').count() > 1
    page.locator('#reset').click()
    page.locator('#search').fill('China')
    assert page.locator('#node-select option').count() > 1
    page.locator('#node-select').select_option(index=1)
    page.locator('#details').wait_for(state='visible')
    assert page.locator('#detail .source-link[href^="http"]').count() > 0
    page.locator('#close').click()
    page.locator('#details').wait_for(state='hidden')
    page.locator('#control-toggle').click()
    page.locator('#search').fill('no-such-entity-xyz')
    assert page.evaluate(f'{graph}.graphData().nodes.length') == 0
    assert page.locator('#node-select').is_disabled()
    page.locator('#reset').click()
    assert page.evaluate(f'{graph}.graphData().nodes.length') == original
    page.locator('[data-period="24"]').click()
    assert page.locator('[data-period="24"]').get_attribute('aria-pressed') == 'true'
    assert page.evaluate('''() => {
        const g = window.__gpGraph.graphData(), now = Date.now();
        return g.links.every(e => e.evidence.length && e.evidence.every(v => {
            const t = Date.parse(v.time || v.published_at || v.published_date || '');
            return t <= now && t >= now - 86400000;
        }));
    }''')
    page.locator('#reset').click()
    page.locator('#flow').click()
    assert page.evaluate(f'{graph}.linkVisibility()') is False
    page.locator('#flow').click()
    assert page.evaluate(f'{graph}.linkVisibility()') is True
    page.locator('#refresh').click()
    page.wait_for_function(f'() => {graph}.graphData().nodes.length > 0')
    page.set_viewport_size({'width': 600, 'height': 700})
    page.wait_for_function(f'() => {graph}.width() === 600 && {graph}.height() === 700')
    print('CONTROLS PASS ' + name + ': category, search, evidence drawer/close, empty/reset, source-date filter, relationships, refresh, resize', flush=True)


def verify_failure(browser):
    page = browser.new_page()
    page.route('**/3d-force-graph.min.js', lambda route: route.abort())
    page.goto(BASE + '/intelligence-web.html', wait_until='networkidle')
    page.locator('#loading-retry').wait_for()
    # A successful fallback JSON request must not hide renderer failure.
    page.wait_for_timeout(3500)
    assert page.locator('#loading').is_visible()
    assert '3D graph library failed to load' in page.locator('#loading').inner_text()
    assert page.evaluate('typeof window.__gpGraph') == 'undefined'
    assert page.locator('#graph canvas').count() == 0
    print('FAILURE PASS: missing library remains visible with retry; no false ready state', flush=True)
    page.close()


if __name__ == '__main__':
    OUTPUT.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        options = {'headless': True}
        if os.environ.get('SMOKE_BROWSER_CHANNEL'):
            options['channel'] = os.environ['SMOKE_BROWSER_CHANNEL']
        browser = p.chromium.launch(**options)
        for name, width, height in [('desktop', 1440, 900), ('mobile', 390, 844)]:
            page = browser.new_page(viewport={'width': width, 'height': height})
            verify_render(page, name)
            page.close()
        verify_failure(browser)
        browser.close()
