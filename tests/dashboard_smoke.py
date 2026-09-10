import os
from playwright.sync_api import sync_playwright

BASE=os.environ.get('SMOKE_BASE_URL','http://127.0.0.1:4173/Aegis-Nexus').rstrip('/')

def dismiss_startup_modal(page):
    modal = page.locator('#gp-how-to-read')
    if modal.count() and modal.is_visible():
        close_candidates = [
            '#gp-how-to-read button[aria-label*="close" i]',
            '#gp-how-to-read button[data-close]',
            '#gp-how-to-read .gp-modal-close',
            '#gp-how-to-read button'
        ]
        closed = False
        for selector in close_candidates:
            candidate = page.locator(selector).first
            if candidate.count() and candidate.is_visible():
                candidate.click(force=True)
                closed = True
                break
        if not closed:
            page.keyboard.press('Escape')
        page.wait_for_timeout(150)
    assert not modal.is_visible(), 'startup how-to-read modal remained open'

def smoke(page, name):
    page_errors = []
    page.on('pageerror', lambda exc: page_errors.append(str(exc)))
    page.goto(BASE + '/index.html', wait_until='domcontentloaded', timeout=30000)
    page.locator('#mapContainer').wait_for(timeout=30000)
    dismiss_startup_modal(page)

    page.locator('#gpMapLayers').wait_for(timeout=30000)
    page.locator('#gpMapLayers').click()
    assert page.locator('#gpMapLayerPanel').evaluate("el => el.classList.contains('open')")
    assert page.locator('.gp-map-layers-backdrop').count() > 0
    page.keyboard.press('Escape')
    assert not page.locator('#gpMapLayerPanel').evaluate("el => el.classList.contains('open')")
    assert page.locator('.gp-map-layers-backdrop').count() == 0

    page.locator('#gpMapSearch').fill('Ukraine')
    page.locator('#gpMapReset').click()
    page.wait_for_function("() => parseInt(document.querySelector('#gpMapCount').textContent.replace(/,/g,''),10) > 0")
    count_text = page.locator('#gpMapCount').inner_text()
    assert 'signals' in count_text.lower(), f'unexpected map count: {count_text}'
    assert int(count_text.split()[0].replace(',', '')) > 0, f'map has no signals: {count_text}'

    page.evaluate("window.dispatchEvent(new CustomEvent('gp:test-open-map-detail'))")
    page.locator('#mapSidePanel').wait_for(timeout=10000, state='visible')
    page.locator('#gpMapClose').wait_for(timeout=10000, state='visible')
    page.locator('#gpMapClose').click()
    page.locator('#mapSidePanel').wait_for(timeout=10000, state='hidden')

    page.locator('#gpBrainSearch').fill('China')
    node = page.locator('[data-brain-node]').first
    node.wait_for(state='visible')
    node.click()
    page.locator('#brainClearSelection').wait_for(state='visible')
    assert page.locator('#brainBody a[href^="http"]').count() > 0
    page.locator('#brainClearSelection').click()
    page.locator('#gpBrainClear').click()

    frame_el=page.locator('iframe.gp-intelweb-frame')
    frame_el.scroll_into_view_if_needed()
    frame=page.frame_locator('iframe.gp-intelweb-frame')
    toggle=frame.locator('#control-toggle')
    toggle.wait_for(timeout=30000, state='visible')
    controls=frame.locator('#controls')
    controls.wait_for(timeout=30000, state='visible')

    toggle.click()
    controls.wait_for(timeout=5000, state='visible')
    assert controls.evaluate("el => el.classList.contains('collapsed')")
    toggle.click()
    assert not controls.evaluate("el => el.classList.contains('collapsed')")
    frame.locator('#clear').wait_for(timeout=5000, state='visible')
    frame.locator('#clear').click()
    frame.locator('#reset').wait_for(timeout=5000, state='visible')
    frame.locator('#reset').click()
    assert not page_errors, f'page errors: {page_errors}'
    print(f'SMOKE PASS {name}: startup modal, map layers/search/reset, signal detail/close, Brain search/evidence/close, lazy Intelligence Web, filter toggle/clear/reset controls')

with sync_playwright() as p:
    browser=p.chromium.launch(headless=True, **({'channel':os.environ['SMOKE_BROWSER_CHANNEL']} if os.environ.get('SMOKE_BROWSER_CHANNEL') else {}))
    desktop=browser.new_page(viewport={'width':1440,'height':900}, reduced_motion='reduce')
    smoke(desktop,'desktop')
    mobile=browser.new_page(viewport={'width':390,'height':844}, reduced_motion='reduce')
    smoke(mobile,'mobile')
    browser.close()
