import asyncio
import pathlib
import urllib.parse
from playwright.async_api import async_playwright

OUT = pathlib.Path(r"/path/to/Research_project\The_6th_model_test\08_Density_Mutation_Validation\06_Benchmark_Screenshots\XVWA\ssrf_loopback_failure.png")


async def main():
    OUT.parent.mkdir(parents=True, exist_ok=True)
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, executable_path=r"C:\Program Files\Google\Chrome\Application\chrome.exe")
        context = await browser.new_context(ignore_https_errors=True)

        async def guard(route):
            host = (urllib.parse.urlsplit(route.request.url).hostname or "").lower()
            if host in {"localhost", "127.0.0.1", "::1"}:
                await route.continue_()
            else:
                await route.abort("blockedbyclient")

        await context.route("**/*", guard)
        page = await context.new_page()
        await page.goto("http://localhost:8082/xvwa/vulnerabilities/ssrf_xspa/index.php", wait_until="domcontentloaded", timeout=15000)
        field = page.locator('input[name="img_url"]')
        if await field.count():
            await field.fill("http://127.0.0.1")
            await page.locator("button.btn-default").first.click(timeout=5000)
            await page.wait_for_load_state("domcontentloaded", timeout=10000)
            await page.wait_for_timeout(400)
        await page.screenshot(path=str(OUT), full_page=True, timeout=10000)
        await context.close()
        await browser.close()
    print(OUT)


if __name__ == "__main__":
    asyncio.run(main())
