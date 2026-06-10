"""Capture a Strava session for the kudos bot.

Strava now blocks *automated* email/OTP login on this account (the persistent
"An unexpected error occurred" wall). So instead of automating the login form,
we log in ONCE by hand in a real browser and save the resulting session
(cookies + localStorage). give_kudos.py then reuses that session and never
touches the login form.

Usage:
    ./venv/bin/python save_session.py

A Firefox window opens on Strava's login page. Log in normally — password or
one-time code, your choice; do it like a human. Tick "Remember me" so the
session lasts. Once you can see your own feed/dashboard, return to the terminal
and press Enter. The session is written to strava_state.json, which is
gitignored — treat that file like a password.
"""
import os

from playwright.sync_api import sync_playwright

STATE_FILE = os.environ.get("STRAVA_STATE_FILE", "strava_state.json")


def main():
    with sync_playwright() as p:
        browser = p.firefox.launch(headless=False)  # does not work in chrome
        context = browser.new_context()
        page = context.new_page()
        page.goto("https://www.strava.com/login")

        print("\n" + "=" * 64)
        print("A Firefox window is open. Log in to Strava BY HAND")
        print("(password or one-time code). Tick 'Remember me'.")
        print("When you can see your own feed/dashboard, come back here.")
        print("=" * 64)
        input("\nPress Enter once you're logged in to save the session... ")

        # Sanity check: hitting the dashboard should NOT bounce us to /login.
        page.goto("https://www.strava.com/dashboard")
        page.wait_for_timeout(2000)
        if "/login" in page.url:
            print("\nStill landing on /login — you don't look logged in.")
            print("Session NOT saved. Re-run and finish logging in first.")
            browser.close()
            return

        context.storage_state(path=STATE_FILE)
        print(f"\nSaved session to {STATE_FILE}. Keep it secret — it's a "
              "credential.\nYou can now run:  ./venv/bin/python give_kudos.py")
        browser.close()


if __name__ == "__main__":
    main()
