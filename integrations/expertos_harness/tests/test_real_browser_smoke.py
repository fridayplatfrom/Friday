"""Optional real Chromium DOM smoke test without network navigation.

The browser tool's network navigation cannot be verified on this runner:
the environment blocks even loopback page.goto. This tests the installed
Python Playwright/Chromium substrate via set_content only.
"""
from pathlib import Path
import os
import pytest


def test_chromium_fills_safe_local_form_without_submit():
    if os.environ.get('EXPERTOS_REAL_BROWSER_TEST') != '1':
        pytest.skip('Enable with EXPERTOS_REAL_BROWSER_TEST=1 in an opt-in test environment')
    if not Path('/usr/bin/chromium').is_file():
        pytest.skip('System chromium not installed at /usr/bin/chromium')
    browser_module = pytest.importorskip('playwright.sync_api')
    page_html = (Path(__file__).resolve().parents[1] / 'examples' / 'safe_form.html').read_text()
    with browser_module.sync_playwright() as playwright:
        browser = playwright.chromium.launch(executable_path='/usr/bin/chromium',
                                             headless=True, args=['--no-sandbox'])
        try:
            page = browser.new_page()
            page.set_content(page_html)
            page.get_by_label('Company Name').fill('Example Co')
            page.get_by_label('Business Email').fill('test@example.com')
            assert page.locator('#company').input_value() == 'Example Co'
            assert page.locator('#email').input_value() == 'test@example.com'
            assert page.locator('#password').input_value() == ''
            assert page.locator('form').count() == 1
        finally:
            browser.close()
