"""Safely exercise generated HTTP RFI payloads against local bWAPP only.

Generated RFI hostnames are temporarily mapped to 127.0.0.1 inside the
disposable bWAPP container. Inert canary files are created and removed in the
container. HTTPS rows are skipped; no Internet destinations are contacted.
"""
import asyncio
import csv
import datetime as dt
import pathlib
import subprocess
import urllib.parse

from playwright.async_api import async_playwright

ROOT = pathlib.Path(r"/path/to/Research_project\The_6th_model_test\08_Density_Mutation_Validation")
INPUT = ROOT / "02_App_Payloads" / "density_generated_payloads.csv"
OUT = ROOT / "05_Benchmark_Results" / "rfi_local_only_validation.csv"
SHOT = ROOT / "06_Benchmark_Screenshots" / "bWAPP" / "rfi_local_canary.png"
CONTAINER = "plgenn-bwapp"
ALLOWED_HOSTS = {"attacker.com", "malicious.site", "evil.com"}
MARKER = "PLGENN_LOCAL_RFI_CANARY"


def docker(*args, input_bytes=None):
    return subprocess.run(["docker", *args], input=input_bytes, check=True,
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE)


async def main():
    rows = list(csv.DictReader(INPUT.open(encoding="utf-8-sig", newline="")))
    rfi = [r for r in rows if r["category"] == "Remote File Inclusion"]
    test_rows = []
    skipped = []
    for row in rfi:
        parsed = urllib.parse.urlsplit(row["payload"])
        if parsed.scheme == "http" and parsed.hostname in ALLOWED_HOSTS:
            test_rows.append(row)
        else:
            skipped.append(row)

    old_hosts = docker("exec", CONTAINER, "cat", "/etc/hosts").stdout
    changed = False
    results = []
    try:
        hosts_with_aliases = old_hosts.rstrip() + b"\n127.0.0.1 attacker.com malicious.site evil.com # " + MARKER.encode() + b"\n"
        docker("exec", "-i", CONTAINER, "sh", "-c", "cat > /etc/hosts", input_bytes=hosts_with_aliases)
        changed = True
        # These fixtures are inert text; the PHP fixture emits one fixed marker.
        docker("exec", CONTAINER, "sh", "-c",
               "printf '%s' 'PLGENN_LOCAL_RFI_CANARY_BACKDOOR' > /var/www/html/backdoor.txt; "
               "printf '%s' 'PLGENN_LOCAL_RFI_CANARY_SHELL' > /var/www/html/shell.txt; "
               "printf '%s' \"<?php echo 'PLGENN_LOCAL_RFI_CANARY_PAYLOAD'; ?>\" > /var/www/html/payload.php")

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
            await page.goto("http://localhost:8081/login.php", wait_until="domcontentloaded", timeout=15000)
            if await page.locator('input[name="login"]').count():
                await page.locator('input[name="login"]').fill("bee")
                await page.locator('input[name="password"]').fill("bug")
                await page.locator('button[name="form"]').click()
                await page.wait_for_load_state("domcontentloaded", timeout=10000)
            # Select bWAPP's intended low security level when the control is available.
            try:
                await page.goto("http://localhost:8081/security_level_set.php", wait_until="domcontentloaded", timeout=10000)
                if await page.locator('select[name="security_level"]').count():
                    await page.locator('select[name="security_level"]').select_option("0")
                    await page.locator('button[name="form_security_level"]').click()
            except Exception:
                pass

            for row in test_rows:
                url = "http://localhost:8081/rlfi.php?language=" + urllib.parse.quote(row["payload"], safe="")
                status, outcome, evidence, error = 0, "NO_CANARY_CONFIRMED", "", ""
                try:
                    response = await page.goto(url, wait_until="domcontentloaded", timeout=12000)
                    status = response.status if response else 0
                    text = await page.locator("body").inner_text(timeout=3000)
                    if MARKER in text:
                        outcome, evidence = "LOCAL_RFI_CANARY_CONFIRMED", "inert_local_canary_marker_in_response"
                    if row["mode"] == "Basic" and row["index"] == "1":
                        await page.screenshot(path=str(SHOT), full_page=True, timeout=8000)
                except Exception as exc:
                    error = type(exc).__name__
                    outcome = "REQUEST_ERROR"
                results.append({"Category": row["category"], "Mode": row["mode"], "Index": row["index"],
                                "Payload": row["payload"], "Scheme": "http", "Status": status,
                                "Outcome": outcome, "Confirmed": outcome == "LOCAL_RFI_CANARY_CONFIRMED",
                                "Evidence": evidence, "Error": error,
                                "TestedUtc": dt.datetime.now(dt.timezone.utc).isoformat()})
                print(f"RFI {row['mode']} #{row['index']}: {outcome}", flush=True)
            await context.close()
            await browser.close()
    finally:
        # Remove the transient test fixtures and restore the exact prior hosts file.
        try:
            docker("exec", CONTAINER, "rm", "-f", "/var/www/html/backdoor.txt",
                   "/var/www/html/shell.txt", "/var/www/html/payload.php")
        except Exception:
            pass
        if changed:
            docker("exec", "-i", CONTAINER, "sh", "-c", "cat > /etc/hosts", input_bytes=old_hosts)

    for row in skipped:
        results.append({"Category": row["category"], "Mode": row["mode"], "Index": row["index"],
                        "Payload": row["payload"], "Scheme": urllib.parse.urlsplit(row["payload"]).scheme,
                        "Status": "SKIPPED", "Outcome": "HTTPS_NOT_TESTED_LOCAL_TLS_UNAVAILABLE",
                        "Confirmed": False, "Evidence": "No HTTPS endpoint configured in local lab",
                        "Error": "", "TestedUtc": dt.datetime.now(dt.timezone.utc).isoformat()})
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=list(results[0].keys()))
        writer.writeheader()
        writer.writerows(results)
    print(f"tested_http={len(test_rows)} skipped_https={len(skipped)} confirmed={sum(bool(r['Confirmed']) for r in results)} output={OUT}")


if __name__ == "__main__":
    asyncio.run(main())
