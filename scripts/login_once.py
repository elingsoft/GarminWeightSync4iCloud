#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""One-time Garmin login on the Mac: seeds cached tokens for watcher.py.

Run once (and again only if watcher.py reports dead tokens):
  GARMIN_EMAIL=you@example.com /Users/elingsoft/GarminWeightSync/venv/bin/python login_once.py
Prompts for the password (never stored) and, if MFA is enabled, for the
one-time code. Tokens are saved by the garminconnect library itself
(typically ~/.garminconnect/garmin_tokens.json) and auto-refreshed later.

Note (2026-11-03, from the installed garminconnect 0.3.x):
  The MFA callback belongs to the CONSTRUCTOR:
      Garmin(email, password, prompt_mfa=prompt_mfa)
  and then client.login() with no arguments. Passing prompt_mfa to login()
  raises TypeError on this version.
"""
import getpass
import os
import sys


def main():
    from garminconnect import Garmin
    email = os.environ.get("GARMIN_EMAIL") or input("Garmin email: ").strip()
    password = getpass.getpass("Garmin password (not stored): ")

    def prompt_mfa():
        return input("MFA code: ").strip()

    try:
        client = Garmin(email, password, prompt_mfa=prompt_mfa)
    except TypeError:
        # Older signature: constructor takes no prompt_mfa.
        client = Garmin(email, password)
    client.login(tokenstore="~/.garminconnect/garmin_tokens.json")
    print("Login OK, tokens cached. watcher.py can now upload without a password.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
