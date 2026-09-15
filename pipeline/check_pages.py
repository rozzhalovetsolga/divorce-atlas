"""Render the exported pages: social preview image, phone screenshot, console errors. Needs `pip install playwright`."""
import os

from playwright.sync_api import sync_playwright

HERE = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.dirname(HERE)

with sync_playwright() as p:
    browser = p.chromium.launch()
    errors = []

    desktop = browser.new_page(viewport={'width': 1200, 'height': 630}, device_scale_factor=1)
    desktop.on('pageerror', lambda error: errors.append(f'index desktop: {error}'))
    desktop.goto(f'file://{SITE}/index.html', wait_until='networkidle')
    desktop.wait_for_timeout(1200)
    desktop.screenshot(path=f'{SITE}/og.png')

    phone = browser.new_page(viewport={'width': 390, 'height': 844}, device_scale_factor=2, is_mobile=True, has_touch=True)
    phone.on('pageerror', lambda error: errors.append(f'index phone: {error}'))
    phone.goto(f'file://{SITE}/index.html', wait_until='networkidle')
    phone.wait_for_timeout(1200)
    overflow = phone.evaluate('document.documentElement.scrollWidth > window.innerWidth + 1')
    os.makedirs(f'{HERE}/build', exist_ok=True)
    phone.screenshot(path=f'{HERE}/build/phone.png', full_page=True)

    appendix = browser.new_page(viewport={'width': 1280, 'height': 1000})
    appendix.on('pageerror', lambda error: errors.append(f'appendix: {error}'))
    appendix.goto(f'file://{SITE}/appendix.html', wait_until='networkidle')
    appendix.wait_for_timeout(1200)

    print('phone horizontal overflow:', overflow)
    print('appendix height (collapsed):', appendix.evaluate('document.body.scrollHeight'))
    print('errors:', errors)
    browser.close()
