#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DAZN EXTRACTOR — v5.4.1
+ WARP auto-toggle (dazn.m3u + DAZN_WAP.m3u)
+ Auto-push a GitHub con git pull previo
+ CK Hunter + WVD Hunter + KEY Hunter
"""
import os, sys, json, re, time, threading, uuid, secrets, glob
import base64
import subprocess
from datetime import datetime, timedelta, time as dt_time, timezone
from zoneinfo import ZoneInfo
import jwt
import pwinput
from curl_cffi import requests
from pathlib import Path
import urllib.request
from urllib.parse import urlparse
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext, ttk, simpledialog

USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36'
HLS_USER_AGENT = 'AppleCoreMedia/1.0.0.20L563 (Apple TV; U; CPU OS 16_5 like Mac OS X; en_us)'
HLS_BASE_URL_DEFAULT = "https://dcs-ac-live.cdn.indazn.com/hls/dazn-linear-{num}/stream.m3u8?p=web"
WVD_FILE_DEFAULT = "device.wvd"
WIDEVINE_SYSTEM_ID = "edef8ba9-79d6-4ace-a3c8-27dcd51d21ed"

_COUNTRY_FLAGS = {
    "IT": "🇮🇹", "DE": "🇩🇪", "ES": "🇪🇸", "FR": "🇫🇷",
    "GB": "🇬🇧", "UK": "🇬🇧", "PT": "🇵🇹", "AT": "🇦🇹",
    "CH": "🇨🇭", "NL": "🇳🇱", "BE": "🇧🇪", "US": "🇺🇸",
    "CA": "🇨🇦", "BR": "🇧🇷", "AR": "🇦🇷", "MX": "🇲🇽",
    "JP": "🇯🇵", "AU": "🇦🇺",
}

VERSION = "5.4.1"
proxies = None
token = None
pin = None
_token_lock = threading.Lock()
_warp_push_lock = threading.Lock()

PERMANENT_ERROR_CODES = {10803}
PENDING_ERROR_CODES = {10000}
MAX_PENDING_AGE_HOURS = 6


def _widget_alive(w):
    try:
        return w is not None and bool(w.winfo_exists())
    except Exception:
        return False


def _set_token(t):
    global token
    with _token_lock:
        token = t


def _get_token():
    with _token_lock:
        return token


OUTPUT_FILE_EVENTS_DEFAULT = "eventos_recogidos.m3u"
OUTPUT_FILE_EVENTS_PENDING = "eventos_recogidos_pendientes.m3u"
OUTPUT_FILE_CHANNELS_DEFAULT = "dazn.m3u"
OUTPUT_FILE_CHANNELS_WAP = "DAZN_WAP.m3u"
OUTPUT_FILE_HLS_DEFAULT = "dazn_hls.m3u"
EVENTS_SNAPSHOT_FILE = "events_snapshot.json"
ACTIVE_EVENTS_CACHE_FILE = "active_events_cache.json"
CHANNEL_SNAPSHOT_FILE = "channels_snapshot.json"
PENDING_EVENTS_FILE = "pending_events.json"
LOGO_OVERRIDES_FILE = "logo_overrides.json"
CATEGORY_LOGOS_FILE = "category_logos.json"
CONFIG_FILE = "dazn_test_config.json"
EXTERNAL_KEYS_FILE = "external_keys.json"
PROFILES_FILE = "profiles.json"
DEPRECATED_STATICS_FILE = "deprecated_statics.json"
GITHUB_TOKEN_FILE = "TOKEN GITHUP.txt"


# ==============================================================
# 🌐 WARP — control automático
# ==============================================================
def _warp_run(args, timeout=10):
    try:
        return subprocess.run(
            ["warp-cli"] + args,
            capture_output=True, text=True, timeout=timeout,
            creationflags=0x08000000 if os.name == "nt" else 0
        )
    except FileNotFoundError:
        return None
    except Exception as e:
        print(f"⚠️ warp-cli: {e}")
        return None


def _warp_status():
    r = _warp_run(["-j", "status"], timeout=5)
    if not r or r.returncode != 0:
        return None
    try:
        data = json.loads(r.stdout)
        return data.get("status", "").lower()
    except Exception:
        txt = ((r.stdout or "") + (r.stderr or "")).lower()
        if "connected" in txt and "disconnected" not in txt:
            return "connected"
        if "disconnected" in txt:
            return "disconnected"
        return None


def _warp_connect():
    print("🌐 WARP → connect...", end=" ", flush=True)
    r = _warp_run(["connect"], timeout=15)
    if not r or r.returncode != 0:
        print("❌ fallo al ejecutar connect")
        return False
    ok = _warp_wait_state("connected")
    if ok:
        time.sleep(3)   # ⬅ NUEVO: dejar que la red se estabilice
    return ok


def _warp_disconnect():
    print("🌐 WARP → disconnect...", end=" ", flush=True)
    r = _warp_run(["disconnect"], timeout=15)
    if not r or r.returncode != 0:
        print("❌ fallo al ejecutar disconnect")
        return False
    ok = _warp_wait_state("disconnected")
    if ok:
        time.sleep(3)   # ⬅ NUEVO: dejar que la red se estabilice
    return ok


def _warp_wait_state(target, timeout=30):
    deadline = time.time() + timeout
    while time.time() < deadline:
        st = _warp_status()
        if st == target:
            print(f"✅ {target}")
            return True
        time.sleep(0.5)
    print(f"⚠️ timeout esperando '{target}'")
    return False


# ==============================================================
# 🚀 GITHUB auto-push (con git pull previo)
# ==============================================================
def _load_github_token():
    if os.path.exists(GITHUB_TOKEN_FILE):
        try:
            with open(GITHUB_TOKEN_FILE, "r", encoding="utf-8") as f:
                return f.read().strip()
        except Exception:
            pass
    return ""


def _github_auto_push(files=None):
    if not config.get("github_auto_push", False):
        return False
    if not _warp_push_lock.acquire(blocking=False):
        print("⏳ git push ya en curso, salto")
        return False
    try:
        repo_dir = config.get("github_repo_dir", "").strip() or os.getcwd()
        branch = config.get("github_branch", "main")
        remote = config.get("github_remote", "origin")
        token = _load_github_token()
        if not token:
            print("⚠️ git push: no hay token en TOKEN GITHUP.txt")
            return False
        user = config.get("github_user", "").strip()
        repo = config.get("github_repo", "").strip()
        if user and repo:
            url_with_token = f"https://{user}:{token}@github.com/{user}/{repo}.git"
        else:
            url_with_token = None
        if files is None:
            files = [config.get("output_file_channels", OUTPUT_FILE_CHANNELS_DEFAULT),
                     config.get("output_file_wap", OUTPUT_FILE_CHANNELS_WAP)]
        existing = [f for f in files
                    if f and os.path.exists(os.path.join(repo_dir, f))]
        if not existing:
            print("⚠️ git push: ningún archivo existe para subir")
            return False
        for f in existing:
            subprocess.run(["git", "add", f], cwd=repo_dir,
                           capture_output=True, text=True, timeout=30)
        st = subprocess.run(["git", "status", "--porcelain"], cwd=repo_dir,
                            capture_output=True, text=True, timeout=15)
        if not st.stdout.strip():
            print("ℹ️ git push: sin cambios")
            return False
        msg = f"auto: actualizar M3U [{datetime.now().strftime('%Y-%m-%d %H:%M')}]"
        c = subprocess.run(["git", "commit", "-m", msg], cwd=repo_dir,
                           capture_output=True, text=True, timeout=30)
        if c.returncode != 0 and "nothing to commit" not in (c.stdout + c.stderr).lower():
            print(f"⚠️ git commit falló: {(c.stderr or c.stdout)[:200]}")
            return False

        # ⬇⬇ NUEVO: git pull ANTES de push, para traer cambios remotos
        try:
            pull_cmd = ["git", "pull", remote, branch, "--no-rebase",
                        "--allow-unrelated-histories"]
            pull_r = subprocess.run(pull_cmd, cwd=repo_dir,
                                     capture_output=True, text=True, timeout=60)
            if pull_r.returncode != 0:
                print(f"⚠️ git pull aviso: {(pull_r.stderr or pull_r.stdout)[:200]}")
        except Exception as e:
            print(f"⚠️ git pull excepción: {e}")
        # ⬆⬆ FIN NUEVO

        cmd = ["git", "push"]
        if url_with_token:
            cmd.append(url_with_token)
        else:
            cmd.extend([remote, branch])
        p = subprocess.run(cmd, cwd=repo_dir, capture_output=True,
                           text=True, timeout=90)
        if p.returncode == 0:
            print(f"✅ git push OK → {len(existing)} archivo(s): {', '.join(existing)}")
            return True
        err = (p.stderr or p.stdout or "")[:300]
        print(f"⚠️ git push falló: {err}")
        return False
    except Exception as e:
        print(f"⚠️ git push excepción: {e}")
        return False
    finally:
        _warp_push_lock.release()


# ==============================================================
# 🎯 CK HUNTER + KID index
# ==============================================================
STATIC_CLEARKEY_KEYS = {
    "NFL NETWORK":   ("d91b5dc41ef85a25883ca47efb3c6641", "5fa7e0ff1e379a83e44005917e3af5f2"),
    "DAZN 1":        ("6164a0abaa7c53c6875fa1e7fe0bb463", "271510d3e1259571dcc568a232e397eb"),
    "MILAN TV":      ("1943a19a78ea525ba289c57b2b111953", "0144bde540ca8a574661a80df9576d77"),
    "MLB":           ("be087efb6c335793a54c58938b8152ba", "a5d137b588f13fb95cc4758f75f98c6e"),
    "EUROSPORT 1":   ("5b95fea44d1458128174961a2f43244c", "8eac54008e5cb7e3751156ad53ca5625"),
    "EUROSPORT 2":   ("316b4d8767e45e64ad8ba429dca07518", "ae0f31d94668346ca4981930fb8ddfc7"),
    "EUROSPORT 3":   ("ea97375d4da251259b0fdf59d49209bc", "cf02db0cd045fc07febc4a65de0b5ec4"),
    "EUROSPORT 4":   ("d3d146e98d15516cafadf9eb3403dc26", "26a6690fbed68ef1de6fa188dccdd144"),
    "EUROSPORT 5":   ("54af840917185951979f2c7063f820e3", "3ecf8a29acdcd597559c89dcc5c7d689"),
    "EUROSPORT 6":   ("f7299fc3eeec54e786c1c2e143c04585", "1b2731ac7c25ecd07b5c3676d16f1532"),
    "INTER TV":      ("89f9ea4a13bf5beeaa4e7120365d51b9", "181a950b390590eff2f608d3d0ff3a91"),
    "REAL TIME":     ("1c58d34533645c44a52efea2d492642b", "9fb9ddcadf355d65db4db0f0c2d94c6c"),
    "REDBULL TV":    ("5912d48e2b915caf9ae5ab0c3df9aae1", "7b8a244c697735202591656b052eafba"),
    "RALLY TV":      ("1fdaf490829b5a0e96cd54012a00e3e9", "b5ed8b50db846bc0609734146eef797b"),
    "RADIO TV RDS":  ("2689e6467c335599b85ddf05973ab259", "f1c10278c1f7876822fc1796fe142511"),
    "RADIO TV SERIE A": ("2689e6467c335599b85ddf05973ab259", "f1c10278c1f7876822fc1796fe142511"),
    "DISCOVERY":     ("03df6ae7f54857e4b138beb4c6caa35f", "e33dd2d4b603b7994f75232fd9fc6798"),
    "NOVE":          ("698f5c5bbfee53359f23cf476f059f87", "e4a65abe0ee79b67964f05d4af4c614b"),
    "DMAX":          ("5013a40090655ee7991762198ac4c891", "bae6d014d839d5dc28f7edab66e9877a"),
    "UNBEATEN":      ("8ab47741930c476780515f9a00decb0a", "7ab4b9ae5a48aa526e511a913b832769"),
    "FOCUS SERIE A": ("e6767246d539569f8c22a5221ceb43ae", "0ef1864232ba516652bb07a7669ae520"),
}

CHANNEL_NUMBER_MAP = {
    "NFL NETWORK":       "205", "DAZN 1": "206", "MILAN TV": "207", "MLB": "208",
    "EUROSPORT 1 (🇩🇪)": "209", "EUROSPORT 2 (🇩🇪)": "210",
    "EUROSPORT 1": "211", "EUROSPORT 2": "212",
    "INTER TV": "215", "REAL TIME": "216", "REDBULL TV": "217",
    "RALLY TV": "220", "RADIO TV RDS": "223", "RADIO TV SERIE A": "223",
    "DISCOVERY": "225", "EUROSPORT 3": "231", "EUROSPORT 4": "232",
    "EUROSPORT 5": "233", "EUROSPORT 6": "239",
    "NOVE": "241", "DMAX": "242", "UNBEATEN": "522", "FOCUS SERIE A": "226",
}

CHANNEL_STREAM_SPECS = {
    "REDBULL TV": {"manifest_type": "mpd", "license_type": "clearkey", "license_format": "json"},
    "RED BULL TV": {"manifest_type": "mpd", "license_type": "clearkey", "license_format": "json"},
}

SERIE_A_DEFAULT_LOGO = (
    "https://www.reuters.com/resizer/v2/UDYJDGVNL5MXZFFS6KT26AESSI.jpg"
    "?auth=5ae05f996c28104420886db9084ca5c6f4b1e2f5773d28bd88563013e504c30a"
    "&width=720&quality=80"
)
SERIE_B_DEFAULT_LOGO = (
    "https://d5rzfs5ck83rq.cloudfront.net/legab.it/img/news/2024-25/Cover_LNPB_202425.jpg"
)
_SERIE_A_REGEX = re.compile(r"\bserie\s*a\b|\bserie\s*a\s*tim\b|\bserie\s*a\s*enilive\b|\bitalian\s+serie\s+a\b", re.IGNORECASE)
_SERIE_B_REGEX = re.compile(r"\bserie\s*b\b|\bserie\s*bkt\b|\bitalian\s+serie\s+b\b|\blega\s+b\b", re.IGNORECASE)
BLACKLIST_CHANNELS = {"NEWS SERIE A", "NEWS CAMPIONATO", "SERIE A NEWS"}


def _is_blacklisted(title):
    if not title: return False
    t = re.sub(r"\s+", " ", str(title).replace("\u00a0", " ")).strip().upper()
    return t in BLACKLIST_CHANNELS


_KID_KEY_INDEX = None
_KID_KEY_INDEX_MTIME = None
_KID_KEY_INDEX_LOCK = threading.Lock()


def _load_external_keys():
    try:
        if os.path.exists(EXTERNAL_KEYS_FILE):
            with open(EXTERNAL_KEYS_FILE, "r", encoding="utf-8") as f:
                d = json.load(f)
            if not isinstance(d, dict): return {}
            if "linear" in d or "events" in d:
                flat = {}
                for kid, info in (d.get("linear") or {}).items():
                    if isinstance(info, dict):
                        info.setdefault("_category", "linear"); flat[kid] = info
                for kid, info in (d.get("events") or {}).items():
                    if isinstance(info, dict):
                        info.setdefault("_category", "events"); flat[kid] = info
                return flat
            return {k: v for k, v in d.items() if not k.startswith("_") and isinstance(v, dict)}
    except Exception as e:
        print(f"⚠️ external_keys load: {e}")
    return {}


def _save_external_keys(flat_data):
    try:
        existing = {"_meta": {}, "linear": {}, "events": {}}
        if os.path.exists(EXTERNAL_KEYS_FILE):
            try:
                with open(EXTERNAL_KEYS_FILE, "r", encoding="utf-8") as f:
                    cur = json.load(f)
                if isinstance(cur, dict) and ("linear" in cur or "events" in cur):
                    existing = {"_meta": cur.get("_meta", {}),
                                "linear": dict(cur.get("linear") or {}),
                                "events": dict(cur.get("events") or {})}
                elif isinstance(cur, dict):
                    for kid, info in cur.items():
                        if kid.startswith("_") or not isinstance(info, dict): continue
                        if info.get("country") or info.get("channels"):
                            existing["linear"][kid] = info
                        else:
                            existing["events"][kid] = info
            except Exception:
                pass
        for kid, info in flat_data.items():
            if kid.startswith("_") or not isinstance(info, dict): continue
            if not info.get("key") and info.get("status") != "placeholder": continue
            info = {k: v for k, v in info.items() if k != "_category"}
            is_linear = bool(info.get("country") or info.get("channels"))
            if is_linear:
                existing["linear"][kid] = info; existing["events"].pop(kid, None)
            else:
                existing["events"][kid] = info; existing["linear"].pop(kid, None)
        existing["_meta"] = {"version": 2, "updated": datetime.now().isoformat(timespec="seconds"),
                             "count_linear": len(existing["linear"]),
                             "count_events": len(existing["events"])}
        with open(EXTERNAL_KEYS_FILE, "w", encoding="utf-8") as f:
            json.dump(existing, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        print(f"⚠️ external_keys save: {e}")
        return False


def _build_kid_key_index():
    idx = {}
    for name, (kid, key) in STATIC_CLEARKEY_KEYS.items():
        idx[kid.lower().replace("-", "")] = (key.lower().replace("-", ""), f"static:{name}")
    for kid, info in _load_external_keys().items():
        k = kid.lower().replace("-", "")
        if isinstance(info, dict) and info.get("key"):
            cat = info.get("_category", "ext")
            name = info.get("name", "?")
            idx[k] = (info["key"].lower().replace("-", ""), f"{cat}:{name}")
    return idx


def _get_kid_index():
    global _KID_KEY_INDEX, _KID_KEY_INDEX_MTIME
    with _KID_KEY_INDEX_LOCK:
        try:
            cur_mtime = os.path.getmtime(EXTERNAL_KEYS_FILE) if os.path.exists(EXTERNAL_KEYS_FILE) else 0
        except Exception:
            cur_mtime = 0
        if _KID_KEY_INDEX is None or _KID_KEY_INDEX_MTIME != cur_mtime:
            _KID_KEY_INDEX = _build_kid_key_index()
            _KID_KEY_INDEX_MTIME = cur_mtime
        return _KID_KEY_INDEX


def _invalidate_kid_index():
    global _KID_KEY_INDEX, _KID_KEY_INDEX_MTIME
    with _KID_KEY_INDEX_LOCK:
        _KID_KEY_INDEX = None
        _KID_KEY_INDEX_MTIME = None


def _extract_kid_from_mpd(mpd_url, token=None, cdn_name=None, cdn_token=None, timeout=15):
    try:
        headers = {"User-Agent": USER_AGENT, "Origin": "https://www.dazn.com",
                   "Referer": "https://www.dazn.com/", "Accept": "*/*"}
        if cdn_name and cdn_token:
            headers[cdn_name] = cdn_token
        r = requests.get(mpd_url, headers=headers, proxies=proxies,
                         impersonate="chrome", timeout=timeout)
        if r.status_code != 200: return None
        text = r.text
        m = re.search(r'cenc:default_KID\s*=\s*"([0-9a-fA-F\-]+)"', text)
        if not m:
            m = re.search(r'default_KID\s*=\s*"([0-9a-fA-F\-]+)"', text)
        if m: return m.group(1).replace("-", "").lower()
        mpssh = re.search(r'<cenc:pssh[^>]*>([A-Za-z0-9+/=\s]+)</cenc:pssh>', text)
        if mpssh:
            try:
                raw = base64.b64decode(mpssh.group(1).strip())
                for offset in (12, 20, 32):
                    if len(raw) >= offset + 16:
                        cand = raw[offset:offset + 16]
                        if cand.count(0) < 16: return cand.hex().lower()
            except Exception:
                pass
        return None
    except Exception:
        return None


def ck_hunter_lookup(kid_hex):
    if not kid_hex: return None, None
    idx = _get_kid_index()
    hit = idx.get(kid_hex.lower().replace("-", ""))
    if hit: return hit
    return None, None


def ck_hunter_register(kid_hex, key_hex, name="", country=None, channels=None):
    if not kid_hex or not key_hex: return False
    kid_hex = kid_hex.lower().replace("-", "")
    key_hex = key_hex.lower().replace("-", "")
    if len(kid_hex) != 32 or len(key_hex) != 32: return False
    for n, (k, v) in STATIC_CLEARKEY_KEYS.items():
        if k.lower() == kid_hex: return True
    flat = _load_external_keys()
    if kid_hex in flat and isinstance(flat[kid_hex], dict):
        if flat[kid_hex].get("key") == key_hex: return True
    entry = {"key": key_hex, "name": (name or "unknown")[:120]}
    if country: entry["country"] = country
    if channels: entry["channels"] = list(channels)
    if not country and not channels:
        entry["added"] = datetime.now().isoformat(timespec="seconds")
    flat[kid_hex] = entry
    ok = _save_external_keys(flat)
    if ok: _invalidate_kid_index()
    return ok


def ck_hunter_stats():
    static_count = len(STATIC_CLEARKEY_KEYS)
    ext = _load_external_keys()
    by_cat = {}; by_country = {}
    for kid, info in ext.items():
        cat = info.get("_category", "?")
        by_cat[cat] = by_cat.get(cat, 0) + 1
        c = info.get("country")
        if c: by_country[c] = by_country.get(c, 0) + 1
    return {"static": static_count, "external": len(ext),
            "total_indexed": len(_get_kid_index()),
            "by_cat": by_cat, "by_country": by_country}


def ck_hunter_attempt(manifest_url, title="", token=None,
                      cdn_name=None, cdn_token=None, verbose=True):
    if not manifest_url: return None
    kid = _extract_kid_from_mpd(manifest_url, token, cdn_name, cdn_token)
    if not kid:
        if verbose: print("❌ KID no presente en el manifest")
        return None
    key, src = ck_hunter_lookup(kid)
    if not key:
        if verbose: print(f"❌ KID {kid[:12]}... desconocido")
        return None
    if verbose: print(f"✅ coincidencia ({src})")
    return {"kid": kid, "key": key, "source": src}


def _b64_to_hex(s):
    if not s or not isinstance(s, str): return None
    try:
        t = s.strip().replace("-", "+").replace("_", "/")
        pad = (-len(t)) % 4
        t += "=" * pad
        raw = base64.b64decode(t)
        return raw.hex().lower()
    except Exception:
        return None


_wvd_cdm = None
_wvd_lock = threading.Lock()
_wvd_loaded_path = None


def _pywidevine_available():
    try:
        import pywidevine  # noqa
        return True
    except Exception:
        return False


def _wvd_path():
    return config.get("wvd_file", WVD_FILE_DEFAULT)


def _load_wvd_cdm(verbose=True):
    global _wvd_cdm, _wvd_loaded_path
    if not _pywidevine_available():
        if verbose: print("⚠️ pywidevine no instalado")
        return None
    wvd_path = _wvd_path()
    if not os.path.exists(wvd_path):
        if verbose: print(f"⚠️ WVD no encontrado: {wvd_path}")
        return None
    with _wvd_lock:
        if _wvd_cdm is not None and _wvd_loaded_path == wvd_path:
            return _wvd_cdm
        try:
            from pywidevine.cdm import Cdm
            from pywidevine.device import Device
            device = Device.load(wvd_path)
            cdm = Cdm.from_device(device)
            _wvd_cdm = cdm
            _wvd_loaded_path = wvd_path
            return cdm
        except Exception as e:
            if verbose: print(f"❌ Error WVD: {e}")
            return None


def _invalidate_wvd_cache():
    global _wvd_cdm, _wvd_loaded_path
    with _wvd_lock:
        _wvd_cdm = None
        _wvd_loaded_path = None


def _extract_pssh_from_mpd(mpd_url, token=None, cdn_name=None, cdn_token=None, timeout=15):
    try:
        headers = {"User-Agent": USER_AGENT, "Origin": "https://www.dazn.com",
                   "Referer": "https://www.dazn.com/", "Accept": "*/*"}
        if cdn_name and cdn_token:
            headers[cdn_name] = cdn_token
        r = requests.get(mpd_url, headers=headers, proxies=proxies,
                         impersonate="chrome", timeout=timeout)
        if r.status_code != 200: return None
        text = r.text
        m = re.search(r'<ContentProtection[^>]*schemeIdUri=["\']urn:uuid:'
                      + WIDEVINE_SYSTEM_ID +
                      r'["\'][^>]*>.*?<cenc:pssh[^>]*>([A-Za-z0-9+/=\s]+)</cenc:pssh>',
                      text, re.DOTALL | re.IGNORECASE)
        if m: return m.group(1).strip()
        mpssh = re.search(r'<cenc:pssh[^>]*>([A-Za-z0-9+/=\s]+)</cenc:pssh>', text)
        if mpssh: return mpssh.group(1).strip()
        mpro = re.search(r'<mspr:pro[^>]*>([A-Za-z0-9+/=\s]+)</mspr:pro>', text)
        if mpro: return mpro.group(1).strip()
        return None
    except Exception:
        return None


def widevine_extract_keys(pssh_b64, la_url, token, cdn_name=None, cdn_token=None, verbose=True):
    dbg_f = open("wvd_debug.log", "a", encoding="utf-8")
    def _d(msg):
        ts = datetime.now().strftime("%H:%M:%S")
        dbg_f.write(f"[{ts}] {msg}\n"); dbg_f.flush()
        if verbose: print(f"   {msg}")
    if not pssh_b64 or not la_url:
        dbg_f.close(); return None
    try:
        from pywidevine.cdm import Cdm
        from pywidevine.device import Device
        from pywidevine.pssh import PSSH
    except ImportError as e:
        _d(f"❌ pywidevine import: {e}"); dbg_f.close(); return None
    try:
        _pssh_clean = (pssh_b64 or "").strip()
        _pad = (-len(_pssh_clean)) % 4
        if _pad: _pssh_clean += "=" * _pad
        try:
            _pssh_bytes = base64.b64decode(_pssh_clean, validate=False)
            pssh_obj = PSSH(_pssh_bytes)
        except Exception:
            pssh_obj = PSSH(pssh_b64)
    except Exception as e:
        _d(f"❌ PSSH init: {e}"); dbg_f.close(); return None
    wvd_path = config.get("wvd_file", WVD_FILE_DEFAULT)
    try:
        device = Device.load(wvd_path)
        cdm = Cdm.from_device(device)
        sid = cdm.open()
        challenge = cdm.get_license_challenge(sid, pssh_obj)
    except Exception as e:
        _d(f"❌ CDM setup: {e}"); dbg_f.close(); return None
    headers = {
        'authorization': 'Bearer ' + token,
        'content-type': 'application/octet-stream',
        'origin': 'https://www.dazn.com', 'referer': 'https://www.dazn.com/',
        'user-agent': USER_AGENT,
        'x-correlation-id': str(uuid.uuid4()),
        'sec-ch-ua': '"Not:A-Brand";v="99", "Google Chrome";v="142", "Chromium";v="142"',
        'sec-ch-ua-mobile': '?0', 'sec-ch-ua-platform': '"Windows"',
        'sec-fetch-dest': 'empty', 'sec-fetch-mode': 'cors', 'sec-fetch-site': 'cross-site',
    }
    try:
        r = requests.post(la_url, headers=headers, data=challenge,
                          proxies=proxies, impersonate="chrome", timeout=30)
    except Exception as e:
        _d(f"❌ POST: {e}")
        try: cdm.close(sid)
        except: pass
        dbg_f.close(); return None
    if r.status_code != 200:
        _d(f"❌ HTTP {r.status_code}")
        try: cdm.close(sid)
        except: pass
        dbg_f.close(); return None
    try:
        cdm.parse_license(sid, r.content)
    except Exception as e:
        _d(f"❌ parse: {e}")
        try: cdm.close(sid)
        except: pass
        dbg_f.close(); return None
    keys = []
    try:
        for k in cdm.get_keys(sid):
            kid_h = k.kid.hex() if isinstance(k.kid, bytes) else str(k.kid)
            if k.type != 'SIGNING':
                key_h = k.key.hex() if isinstance(k.key, bytes) else str(k.key)
                keys.append({"kid": kid_h, "key": key_h, "type": k.type})
                _d(f"   ✅ {k.type}: {kid_h} : {key_h}")
    except Exception as e:
        _d(f"❌ get_keys: {e}")
    finally:
        try: cdm.close(sid)
        except: pass
    dbg_f.close()
    return keys or None


def widevine_attempt(manifest_url, la_url, title="", token=None,
                      cdn_name=None, cdn_token=None, verbose=True):
    if not manifest_url or not la_url: return None
    pssh = _extract_pssh_from_mpd(manifest_url, token, cdn_name=cdn_name, cdn_token=cdn_token)
    if not pssh:
        if verbose: print("   ❌ PSSH Widevine no presente")
        return None
    keys = widevine_extract_keys(pssh, la_url, token, cdn_name=cdn_name,
                                   cdn_token=cdn_token, verbose=verbose)
    if not keys: return None
    primary = None
    for k in keys:
        try: ck_hunter_register(k["kid"], k["key"], title or "wvd")
        except Exception: pass
        if primary is None: primary = k
    if not primary: return None
    return {"kid": primary["kid"], "key": primary["key"],
            "source": "wvd", "keys": keys, "pssh": pssh}


def key_hunter_request_license(kid_hex, la_url, token, cdn_name=None,
                                cdn_token=None, verbose=True):
    if not kid_hex or not la_url: return None
    try:
        kid_bytes = bytes.fromhex(kid_hex.replace("-", ""))
        kid_b64 = base64.urlsafe_b64encode(kid_bytes).decode().rstrip("=")
    except Exception:
        if verbose: print("   ❌ KID no convertible")
        return None
    payload = {"kids": [kid_b64], "type": "temporary"}
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json, */*",
        "Origin": "https://www.dazn.com", "Referer": "https://www.dazn.com/",
        "User-Agent": USER_AGENT,
        "Authorization": "Bearer " + token,
        "x-correlation-id": str(uuid.uuid4()),
    }
    if cdn_name and cdn_token:
        headers[cdn_name] = cdn_token
    try:
        r = requests.post(la_url, json=payload, headers=headers,
                          proxies=proxies, impersonate="chrome", timeout=20)
    except Exception as e:
        if verbose: print(f"   ❌ Red: {e}")
        return None
    if r.status_code != 200:
        if verbose: print(f"   ❌ HTTP {r.status_code}")
        return None
    try:
        data = r.json()
    except Exception:
        try:
            text = r.content.decode("latin-1", errors="replace")
            for m in re.finditer(r'"k"\s*:\s*"([A-Za-z0-9_\-]+)"', text):
                key_hex = _b64_to_hex(m.group(1))
                if key_hex and len(key_hex) == 32: return key_hex
        except Exception:
            pass
        return None
    keys = data.get("keys") if isinstance(data, dict) else None
    if not isinstance(keys, list): return None
    for k in keys:
        k_raw = k.get("k") or k.get("K") or k.get("key")
        if not k_raw: continue
        key_hex = _b64_to_hex(k_raw)
        if key_hex and len(key_hex) == 32: return key_hex
    return None
# ==============================================================
# NAVEGADOR + CAPTURA DE TOKEN (CDP)
# ==============================================================
BROWSER_DEBUG_PORT = 9223
BROWSER_DEBUG_HOST = "127.0.0.1"
BROWSER_PROFILE_BASE_CHROME = Path.home() / "AppData" / "Local" / "Google" / "Chrome" / "DaznTokenCapture"
BROWSER_PROFILE_BASE_EDGE = Path.home() / "AppData" / "Local" / "Microsoft" / "Edge" / "DaznTokenCapture"


def _browser_profile_dir(name=None, browser="chrome"):
    base = BROWSER_PROFILE_BASE_EDGE if browser == "edge" else BROWSER_PROFILE_BASE_CHROME
    if name:
        safe = re.sub(r"[^A-Za-z0-9_\-]", "_", str(name).strip().lower())[:40] or "default"
        d = base.parent / f"{base.name}_{safe}"
    else:
        d = base
    try: d.mkdir(parents=True, exist_ok=True)
    except Exception: pass
    return d


def _find_chrome_exe():
    cands = [
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        str(Path.home() / "AppData" / "Local" / "Google" / "Chrome" / "Application" / "chrome.exe"),
    ]
    for p in cands:
        if Path(p).exists(): return p
    return None


def _find_edge_exe():
    cands = [
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
        str(Path.home() / "AppData" / "Local" / "Microsoft" / "Edge" / "Application" / "msedge.exe"),
    ]
    for p in cands:
        if Path(p).exists(): return p
    return None


def _find_browser_exe():
    pref = (config.get("browser_type", "auto") or "auto").lower()
    if pref == "chrome":
        p = _find_chrome_exe()
        return (p, "chrome") if p else (None, None)
    if pref == "edge":
        p = _find_edge_exe()
        return (p, "edge") if p else (None, None)
    p = _find_chrome_exe()
    if p: return (p, "chrome")
    p = _find_edge_exe()
    if p: return (p, "edge")
    return (None, None)


def _wait_debug(host, port, timeout=25.0):
    url = f"http://{host}:{port}/json/version"
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=1.5) as r:
                return json.loads(r.read().decode("utf-8"))
        except Exception:
            time.sleep(0.4)
    return None


def _har_entry_from_response(response):
    try:
        url = response.url or ""
        status = response.status or 0
        req = response.request
        if not req: return None
        req_headers = req.headers or {}
        res_headers = response.headers or {}
        ctype = (res_headers.get("content-type") or "").lower()
        body = ""
        url_l = url.lower()
        is_license = any(w in url_l for w in
                         ("license", "clearkey", "drm", "widevine", "playback", "getkey"))
        skip_body = (not is_license) and any(
            x in ctype for x in ("video/", "audio/", "application/octet-stream", "image/"))
        if not skip_body:
            try: body = response.text()
            except Exception:
                try: body = response.body().decode("latin-1", errors="replace")
                except Exception: body = ""
            if len(body) > 200_000:
                body = body[:200_000] + "\n\n... [TRUNCADO]"
        return {
            "startedDateTime": datetime.now(timezone.utc).isoformat(),
            "time": 0,
            "request": {"method": req.method or "GET", "url": url,
                        "httpVersion": "HTTP/1.1",
                        "headers": [{"name": k, "value": v} for k, v in req_headers.items()],
                        "queryString": [], "cookies": [], "headersSize": -1, "bodySize": -1},
            "response": {"status": status, "statusText": "", "httpVersion": "HTTP/1.1",
                         "headers": [{"name": k, "value": v} for k, v in res_headers.items()],
                         "cookies": [],
                         "content": {"size": len(body),
                                     "mimeType": res_headers.get("content-type", ""),
                                     "text": body},
                         "redirectURL": "", "headersSize": -1, "bodySize": len(body)},
            "cache": {}, "timings": {"send": 0, "wait": 0, "receive": 0},
        }
    except Exception:
        return None


def _capture_token_via_cdp(url="https://www.dazn.com/es-ES/home",
                            timeout_sec=120, log=print, save_har=None,
                            profile_dir=None, browser_type=None):
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        log("❌ Playwright no instalado.")
        return None
    exe, bname = _find_browser_exe()
    if browser_type and browser_type != "auto":
        if browser_type == "chrome":
            exe = _find_chrome_exe(); bname = "chrome"
        elif browser_type == "edge":
            exe = _find_edge_exe(); bname = "edge"
    if not exe:
        log("❌ Navegador no encontrado.")
        return None
    log(f"🌐 Navegador: {bname.upper()} ({exe})")
    if save_har is None:
        save_har = bool(config.get("har_recording_enabled", True))
    _pdir = profile_dir if profile_dir is not None else _browser_profile_dir(browser=bname)
    try: Path(_pdir).mkdir(parents=True, exist_ok=True)
    except Exception: pass
    args = [exe, f"--remote-debugging-port={BROWSER_DEBUG_PORT}",
            f"--user-data-dir={_pdir}", "--no-first-run", "--no-default-browser-check",
            "--remote-allow-origins=*", url]
    creationflags = 0
    if hasattr(subprocess, "DETACHED_PROCESS"):
        creationflags = subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP
    log(f"🚀 Iniciando {bname.upper()} en el puerto {BROWSER_DEBUG_PORT}...")
    proc = subprocess.Popen(args, stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL, creationflags=creationflags)
    info = _wait_debug(BROWSER_DEBUG_HOST, BROWSER_DEBUG_PORT, timeout=30.0)
    if not info:
        log("❌ Puerto debug no alcanzable.")
        try: proc.terminate()
        except Exception: pass
        return None
    found_token = {"value": None}
    interesting_responses = []
    pw = None
    try:
        pw = sync_playwright().start()
        browser = pw.chromium.connect_over_cdp(f"http://{BROWSER_DEBUG_HOST}:{BROWSER_DEBUG_PORT}")
        if not browser.contexts:
            log("❌ Sin contexto.")
            return None
        context = browser.contexts[0]

        def _on_request(request):
            if found_token["value"]: return
            try:
                headers = request.headers or {}
                auth = headers.get("authorization") or headers.get("Authorization")
                if auth and auth.startswith("Bearer eyJ"):
                    tok = auth.split(" ", 1)[1].strip()
                    if tok.count(".") == 2:
                        found_token["value"] = tok
                        log(f"🔑 Token capturado ({len(tok)} char)")
            except Exception: pass

        context.on("request", _on_request)
        if save_har:
            def _on_response(response):
                try:
                    u = (response.url or "").lower()
                    if (".mpd" in u or ".m3u8" in u or "playback" in u
                            or "manifest" in u or "license" in u or "widevine" in u
                            or "/rail" in u or "concurrency" in u
                            or "signin" in u or "refreshtoken" in u):
                        interesting_responses.append(response)
                except Exception: pass
            context.on("response", _on_response)

        try:
            page = context.new_page()
            try: page.goto(url, wait_until="domcontentloaded", timeout=30000)
            except Exception: pass
        except Exception:
            page = None

        log(f"🎧 Esperando token (máx {timeout_sec}s)...")
        deadline = time.time() + timeout_sec
        while time.time() < deadline and not found_token["value"]:
            try:
                if page: page.wait_for_timeout(500)
                else: time.sleep(0.5)
            except Exception: time.sleep(0.5)

        if found_token["value"]:
            grace = int(config.get("har_grace_seconds", 45))
            if save_har and grace > 0:
                log(f"✅ Token capturado. {grace}s para navegar...")
                for _ in range(grace):
                    try:
                        if page: page.wait_for_timeout(1000)
                        else: time.sleep(1)
                    except Exception: time.sleep(1)

        if save_har and interesting_responses:
            har_entries = []
            for resp in interesting_responses:
                try:
                    entry = _har_entry_from_response(resp)
                    if entry: har_entries.append(entry)
                except Exception: continue
            if har_entries:
                ts = datetime.now().strftime("%Y%m%d_%H%M%S")
                har_file = f"dazn_capture_{ts}.har"
                try:
                    with open(har_file, "w", encoding="utf-8") as f:
                        json.dump({"log": {"version": "1.2", "entries": har_entries}}, f,
                                  ensure_ascii=False, indent=2)
                    log(f"✅ HAR guardado: {har_file}")
                except Exception as e:
                    log(f"⚠️ HAR: {e}")

        try: browser.close()
        except Exception: pass
    except Exception as e:
        log(f"❌ CDP: {e}")
    finally:
        try:
            if pw: pw.stop()
        except Exception: pass
        try:
            if proc.poll() is None:
                proc.terminate()
                try: proc.wait(timeout=3)
                except Exception: proc.kill()
        except Exception: pass
    return found_token["value"]


def capture_and_save_token(log=print, profile_name=None):
    global VERSION
    pdir = _browser_profile_dir(profile_name) if profile_name else None
    tok = _capture_token_via_cdp(log=log, profile_dir=pdir)
    if not tok:
        log("❌ Token no capturado.")
        return None
    try:
        with open("token.txt", "w", encoding="utf-8") as f:
            f.write(tok)
        _set_token(tok)
        try: VERSION = get_version()
        except Exception: pass
        log(f"💾 Token guardado ({len(tok)} char)")
        return tok
    except Exception as e:
        log(f"❌ {e}")
        return None


def _load_token_safe(do_refresh_if_possible=True):
    with open("token.txt", "r", encoding="utf-8") as f:
        t = f.read().strip()
    if not t or t.count(".") != 2:
        raise ValueError("Token no válido")
    if do_refresh_if_possible:
        try:
            jwt.decode(t, options={"verify_signature": False})
            t = do_refresh(t)
        except Exception:
            print("ℹ️ Token no renovable, uso el guardado.")
    _set_token(t)
    return t


def ascii_clear():
    os.system('cls' if os.name == 'nt' else 'clear')
    print("🎯 DAZN EXTRACTOR — v5.4.1 WARP+AUTO-PUSH\n")


def clear_screen():
    ascii_clear()


def signal_handler(sig, frame):
    print('\nAdiós :)'); quit()


# ==============================================================
# API DAZN
# ==============================================================
def get_single(token, asset_id, pin=None, format='MPEG-DASH'):
    decoded = jwt.decode(token, options={"verify_signature": False})
    headers = {
        'accept': '*/*', 'authorization': 'Bearer ' + token,
        'origin': 'https://www.dazn.com', 'referer': 'https://www.dazn.com/',
        'user-agent': USER_AGENT, 'x-dazn-device': decoded['deviceId'],
        'x-correlation-id': str(uuid.uuid4()),
        'sec-ch-ua': '"Not:A-Brand";v="99", "Google Chrome";v="142", "Chromium";v="142"',
        'sec-ch-ua-mobile': '?0', 'sec-ch-ua-platform': '"Windows"',
        'sec-fetch-dest': 'empty', 'sec-fetch-mode': 'cors', 'sec-fetch-site': 'cross-site',
    }
    if pin: headers['x-age-verification-pin'] = pin
    params = {
        'AppVersion': VERSION, 'DrmType': 'WIDEVINE', 'Format': format,
        'PlayerId': '@dazn/peng-html5-core/web/web', 'Platform': 'web',
        'LanguageCode': 'en', 'Model': 'unknown', 'Secure': 'true',
        'Manufacturer': 'microsoft', 'PlayReadyInitiator': 'false',
        'Capabilities': 'mta', 'AssetId': asset_id, 'MtaLanguageCode': '', 'token': token,
    }
    try:
        r = requests.get('https://api.playback.indazn.com/v5/Playback',
                         params=params, headers=headers, proxies=proxies,
                         impersonate="chrome", timeout=30)
        data = json.loads(r.content)
        pds = data.get('PlaybackDetails') or []
        if not pds:
            err_msg = ""; err_code = None
            odata_err = data.get('odata.error')
            if isinstance(odata_err, dict):
                err_code = odata_err.get('code')
                msg = odata_err.get('message')
                if isinstance(msg, dict):
                    msg = msg.get('value') or msg.get('lang') or ''
                if err_code: err_msg = f"[{err_code}] {msg}"
            if not err_msg:
                for k in ('Error', 'error', 'Message', 'message', 'Code', 'code',
                          'ErrorCode', 'Description'):
                    if data.get(k): err_msg = str(data[k]); break
            if not err_msg: err_msg = json.dumps(data)[:200]
            print(f'   ↳ {err_msg}')
            return None, None, None, None, None, err_code, None, err_msg
        spd = sorted(pds, key=lambda i: i.get('CdnName', ''))
        pd = spd[0]
        ct = pd['CdnToken']
        clearkey_info = None
        for k in ('ClearKey', 'clearKey', 'Keys', 'keys', 'ContentKeys', 'contentKeys'):
            v = pd.get(k)
            if isinstance(v, dict) and v:
                for kid, key in v.items():
                    if isinstance(key, str) and len(key) >= 32:
                        clearkey_info = {"kid": kid, "key": key}; break
                if clearkey_info: break
            elif isinstance(v, list) and v:
                item = v[0]
                if isinstance(item, dict):
                    kid = item.get('kid') or item.get('KID') or item.get('keyId')
                    key = item.get('key') or item.get('KEY') or item.get('k')
                    if kid and key:
                        clearkey_info = {"kid": str(kid), "key": str(key)}; break
        if not clearkey_info:
            def _walk(obj):
                if isinstance(obj, dict):
                    for k in ('ClearKey', 'clearKey', 'clearKeyInfo'):
                        v = obj.get(k)
                        if isinstance(v, dict):
                            kid = v.get('kid') or v.get('KID')
                            key = v.get('key') or v.get('KEY')
                            if kid and key: return {"kid": str(kid), "key": str(key)}
                    for v in obj.values():
                        r = _walk(v)
                        if r: return r
                elif isinstance(obj, list):
                    for it in obj:
                        r = _walk(it)
                        if r: return r
                return None
            clearkey_info = _walk(data)
        return (pd["ManifestUrl"], ct["Name"], ct["Value"],
                pd.get('LaUrl'), (data.get('PlaybackLock') or {}).get('LockId'), None,
                clearkey_info, None)
    except Exception as e:
        print(f'   ↳ get_single: {e}')
        return None, None, None, None, None, None, None, str(e)


def delete_concurrency(token, lock_id):
    if not lock_id: return
    headers = {'authorization': 'Bearer ' + token,
               'origin': 'https://www.dazn.com', 'referer': 'https://www.dazn.com/',
               'user-agent': USER_AGENT, 'x-correlation-id': str(uuid.uuid4())}
    try:
        requests.delete('https://concurrency-v2.playback.indazn.com/v2/concurrency/lock/' + lock_id,
                        headers=headers, proxies=proxies, impersonate="chrome", timeout=15)
    except Exception: pass


def _release_all_locks():
    t = _get_token()
    if not t: return
    try:
        headers = {'authorization': 'Bearer ' + t,
                   'origin': 'https://www.dazn.com', 'referer': 'https://www.dazn.com/',
                   'user-agent': USER_AGENT}
        requests.delete('https://concurrency-v2.playback.indazn.com/v2/concurrency/locks',
                        headers=headers, proxies=proxies, impersonate='chrome', timeout=10)
        print("🧹 Bloqueos liberados.")
    except Exception: pass


def do_refresh(token):
    headers = {
        'authorization': 'Bearer ' + token, 'content-type': 'application/json',
        'origin': 'https://www.dazn.com', 'referer': 'https://www.dazn.com/',
        'user-agent': USER_AGENT,
        'sec-ch-ua': '"Not:A-Brand";v="99", "Google Chrome";v="142", "Chromium";v="142"',
        'sec-ch-ua-mobile': '?0', 'sec-ch-ua-platform': '"Windows"',
    }
    decoded = jwt.decode(token, options={"verify_signature": False})
    r = requests.post('https://ott-authz-bff-prod.ar.indazn.com/v5/RefreshAccessToken',
                      headers=headers, json={'DeviceId': decoded['deviceId'].split('-')[-1]},
                      proxies=proxies, impersonate='chrome', timeout=30)
    token = json.loads(r.content)['AuthToken']['Token']
    with open("token.txt", 'w', encoding='utf-8') as f:
        f.write(token)
    _set_token(token)
    return token


def get_rails(token):
    headers = {'accept': 'application/json, text/plain, */*',
               'content-type': 'application/json',
               'origin': 'https://www.dazn.com', 'referer': 'https://www.dazn.com/',
               'user-agent': USER_AGENT,
               'sec-ch-ua': '"Not:A-Brand";v="99", "Google Chrome";v="142", "Chromium";v="142"',
               'sec-ch-ua-mobile': '?0', 'sec-ch-ua-platform': '"Windows"'}
    decoded = jwt.decode(token, options={"verify_signature": False})
    ent = ''.join(e['id'] + ',' for e in decoded['entitlements']['entitlementSets'])
    params = {'groupId': 'home', 'country': decoded['contentCountry'],
              'openBrowse': 'false', 'userEntitlements': ent}
    try:
        r = requests.get('https://rails.discovery.indazn.com/eu/v8/rails', headers=headers,
                         params=params, proxies=proxies, impersonate='chrome', timeout=30)
        return json.loads(r.content).get('Rails', [])
    except Exception as e:
        print(f'Error rails: {e}'); return []


def get_channel_rails(token):
    headers = {'accept': 'application/json, text/plain, */*',
               'content-type': 'application/json',
               'origin': 'https://www.dazn.com', 'referer': 'https://www.dazn.com/',
               'user-agent': USER_AGENT,
               'sec-ch-ua': '"Not:A-Brand";v="99", "Google Chrome";v="142", "Chromium";v="142"',
               'sec-ch-ua-mobile': '?0', 'sec-ch-ua-platform': '"Windows"'}
    decoded = jwt.decode(token, options={"verify_signature": False})
    ent = ''.join(e['id'] + ',' for e in decoded['entitlements']['entitlementSets'])
    params = {'groupId': 'sport', 'country': decoded['contentCountry'],
              'params': 'PageType:Sport;ContentType:Sport;ContentId:9kn3pow0we2r8hna2p0k4m2ff',
              'openBrowse': 'false', 'userEntitlements': ent}
    try:
        r = requests.get('https://rails.discovery.indazn.com/eu/v8/rails', headers=headers,
                         params=params, proxies=proxies, impersonate='chrome', timeout=30)
        return json.loads(r.content).get('Rails', [])
    except Exception as e:
        print(f'Error channel rails: {e}'); return []


def get_schedule_rails(token):
    headers = {'accept': 'application/json, text/plain, */*',
               'content-type': 'application/json',
               'origin': 'https://www.dazn.com', 'referer': 'https://www.dazn.com/',
               'user-agent': USER_AGENT}
    try:
        decoded = jwt.decode(token, options={"verify_signature": False})
    except Exception:
        return []
    ent = ''.join(e['id'] + ',' for e in decoded.get('entitlements', {}).get('entitlementSets', [])).strip(',')
    country = decoded.get('contentCountry', 'IT')
    attempts = [
        {'groupId': 'schedule', 'country': country,
         'params': 'PageType:Schedule;ContentType:Schedule',
         'openBrowse': 'false', 'userEntitlements': ent},
        {'groupId': 'schedule', 'country': country,
         'openBrowse': 'false', 'userEntitlements': ent},
        {'groupId': 'calendar', 'country': country,
         'openBrowse': 'false', 'userEntitlements': ent},
    ]
    for params in attempts:
        try:
            r = requests.get('https://rails.discovery.indazn.com/eu/v8/rails',
                             headers=headers, params=params, proxies=proxies,
                             impersonate='chrome', timeout=30)
            if r.status_code != 200: continue
            rails = json.loads(r.content).get('Rails', [])
            if rails: return rails
        except Exception:
            continue
    return []


def single_rail(token, rail_id, rail_params, retries=3):
    headers = {'accept': 'application/json, text/plain, */*',
               'authorization': 'Bearer ' + token,
               'content-type': 'application/json',
               'origin': 'https://www.dazn.com', 'referer': 'https://www.dazn.com/',
               'user-agent': USER_AGENT}
    decoded = jwt.decode(token, options={"verify_signature": False})
    params = {'platform': 'web', 'id': rail_id, 'country': decoded['contentCountry'],
              'languageCode': 'en', 'params': rail_params}
    last_err = None
    for attempt in range(retries):
        try:
            r = requests.get('https://rail-router.discovery.indazn.com/eu/v6/Rail',
                             headers=headers, params=params, proxies=proxies,
                             impersonate='chrome', timeout=20)
            if r.status_code in (401, 403, 404): return []
            if r.status_code != 200:
                last_err = f'HTTP {r.status_code}'; time.sleep(1.5 * (attempt + 1)); continue
            try: data = r.json()
            except Exception:
                last_err = 'no-JSON'; time.sleep(1.5 * (attempt + 1)); continue
            return data.get('Tiles', []) or []
        except Exception as e:
            last_err = str(e); time.sleep(1.5 * (attempt + 1))
    if last_err: print(f'⚠️ Rail {rail_id}: {last_err}')
    return []


def get_channels(token):
    print('\n📡 Escaneando canales...')
    channels_data = []
    seen_assets = set()

    def _process_rails(rails, source_name):
        totale = len(rails)
        for i, r in enumerate(rails, 1):
            rail_id = r.get('Id'); rail_params = r.get('Params', '')
            if not rail_id: continue
            print(f'  [{source_name} {i}/{totale}] rail {rail_id}...', end=' ', flush=True)
            try:
                tiles = single_rail(token, rail_id, rail_params, retries=5)
            except Exception as e:
                print(f'❌ {e}'); continue
            if not tiles:
                print('vacío'); continue
            aggiunti = 0
            for t in tiles:
                tt = (t.get('Type') or '').strip()
                if _is_blacklisted(t.get('Title') or ''): continue
                if tt != 'Live' and not _is_linear_channel_tile(t): continue
                aid = t.get('AssetId')
                if not aid or aid in seen_assets: continue
                seen_assets.add(aid); channels_data.append(t); aggiunti += 1
            print(f'✅ {aggiunti} nuevos (tot {len(channels_data)})')

    try:
        rails_sport = get_channel_rails(token) or []
        print(f'📺 {len(rails_sport)} rails deportes'); _process_rails(rails_sport, 'SPORT')
    except Exception as e: print(f'❌ {e}')
    try:
        rails_home = get_rails(token) or []
        print(f'🏠 {len(rails_home)} rails home'); _process_rails(rails_home, 'HOME')
    except Exception as e: print(f'❌ {e}')

    unique = []; seen = set()
    for c in channels_data:
        t = c.get('Title', ''); a = c.get('AssetId', '')
        if t and a and t not in seen:
            seen.add(t); unique.append(c)
    print(f'\n✅ {len(unique)} canales únicos')
    return unique


KNOWN_LIVE_CHANNEL_NAMES = {
    "DAZN 1", "DAZN 2", "DAZN 3", "DAZN 4", "DAZN 5",
    "Eurosport 1", "Eurosport 2", "Eurosport 3", "Eurosport 4", "Eurosport 5",
    "Inter TV", "Milan TV", "Red Bull TV", "NOVE", "Real Time",
    "NFL Network", "Radio TV Serie A", "Unbeaten", "Buongiorno Serie A",
    "Focus Serie A", "DAZN Focus Serie A", "Focus Serie A 24/7", "Focus Serie A HD",
}


def _is_linear_channel_tile(tile):
    title = (tile.get('Title') or '').strip()
    if _is_blacklisted(title): return False
    if title in KNOWN_LIVE_CHANNEL_NAMES: return True
    if _find_clearkey_for_title(title): return True
    comp = tile.get('Competition') or {}
    if isinstance(comp, dict): comp = comp.get('Title') or comp.get('Name') or ''
    if str(comp).strip().lower() == 'live tv': return True
    if tile.get('IsLinear') is True: return True
    if tile.get('EventId'): return False
    if tile.get('ChannelNumber') is not None: return True
    return False


def get_scheduled_events(token, include_live=True, verbose=True):
    if verbose: print('\n📅 Escaneando eventos...')
    events_data = []; seen_events = set()

    def _process_rails(rails, source_name):
        totale = len(rails)
        for i, r in enumerate(rails, 1):
            rail_id = r.get('Id'); rail_params = r.get('Params', '')
            if not rail_id: continue
            if verbose: print(f'  [{source_name} {i}/{totale}] rail {rail_id}...', end=' ', flush=True)
            try:
                tiles = single_rail(token, rail_id, rail_params)
            except Exception as e:
                if verbose: print(f'❌ {e}')
                continue
            if not tiles:
                if verbose: print('vacío')
                continue
            aggiunti = 0
            for t in tiles:
                tt = (t.get('Type') or '').strip()
                if _is_blacklisted(t.get('Title') or ''): continue
                if _is_linear_channel_tile(t): continue
                accept = False
                if tt == 'UpComing': accept = True
                elif include_live and tt == 'Live': accept = True
                if not accept: continue
                aid = t.get('AssetId') or ''; eid = t.get('EventId') or ''
                title = (t.get('Title') or '').strip()
                key = eid or aid
                if not key or key in seen_events or not title: continue
                seen_events.add(key); events_data.append(t); aggiunti += 1
            if verbose: print(f'✅ {aggiunti} eventos (tot {len(events_data)})')

    try:
        rails_sched = get_schedule_rails(token) or []
        if rails_sched:
            print(f'📅 {len(rails_sched)} rails schedule'); _process_rails(rails_sched, 'SCHEDULE')
    except Exception as e: print(f'❌ {e}')
    try:
        rails_sport = get_channel_rails(token) or []
        print(f'📺 {len(rails_sport)} rails deportes'); _process_rails(rails_sport, 'SPORT')
    except Exception as e: print(f'❌ {e}')
    try:
        rails_home = get_rails(token) or []
        print(f'🏠 {len(rails_home)} rails home'); _process_rails(rails_home, 'HOME')
    except Exception as e: print(f'❌ {e}')

    def _ts(e):
        v = e.get('Start') or e.get('EventStartTime') or ''
        try: return datetime.fromisoformat(v.replace('Z', '+00:00')).timestamp()
        except Exception: return float('inf')
    events_data.sort(key=_ts)
    try:
        with open('dazn_events.json', 'w', encoding='utf-8') as f:
            json.dump(events_data, f, ensure_ascii=False, indent=2)
    except Exception: pass
    print(f'\n✅ {len(events_data)} eventos encontrados')
    return events_data
def _clean(v):
    return "" if v is None else re.sub(r"\s+", " ", str(v)).strip()


def _norm(s):
    s = str(s).lower()
    for k, v in {"à": "a", "è": "e", "é": "e", "ì": "i", "ò": "o", "ù": "u",
                 "á": "a", "í": "i", "ó": "o", "ú": "u", "ñ": "n",
                 "'": "", "’": "", "-": " "}.items():
        s = s.replace(k, v)
    return re.sub(r"\s+", " ", s).strip()


def _event_haystack(event):
    title = _clean(event.get('Title', ''))
    sport = event.get('Sport') or {}
    if isinstance(sport, dict): sport = sport.get('Title') or sport.get('Name') or ''
    sport = _clean(sport)
    comp = event.get('Competition') or {}
    if isinstance(comp, dict): comp = comp.get('Title') or comp.get('Name') or ''
    comp = _clean(comp)
    desc = _clean(event.get('Description', ''))
    return _norm(" ".join(filter(None, [title, sport, comp, desc]))), sport, comp


def get_events_filter():
    ft = config.get("events_filter_type", "all"); fv = config.get("events_filter_value")
    if ft == "all" or fv is None: return ("all", None)
    if ft == "competition_list" and not isinstance(fv, list): return ("all", None)
    return (ft, fv)


def save_events_filter(ft, fv):
    config["events_filter_type"] = ft
    config["events_filter_value"] = fv
    save_config()


def apply_event_filter(events, filt):
    tipo, valore = filt
    if tipo == "all" or valore is None: return events
    out = []
    if tipo == "competition_list":
        vals = set(_norm(str(v)) for v in valore)
        for e in events:
            _, _, comp = _event_haystack(e)
            if _norm(comp) in vals: out.append(e)
        return out
    val = _norm(str(valore))
    for e in events:
        hay, sport, comp = _event_haystack(e)
        if tipo == "sport" and _norm(sport) == val: out.append(e)
        elif tipo == "competition" and _norm(comp) == val: out.append(e)
        elif tipo == "title" and val in hay: out.append(e)
    return out


def filter_events_today(events):
    try: rome = ZoneInfo('Europe/Rome')
    except Exception: rome = timezone.utc
    today = datetime.now(rome).date(); out = []
    for e in events:
        v = e.get('Start') or e.get('EventStartTime') or ''
        if not v: continue
        try:
            dt = datetime.fromisoformat(str(v).replace('Z', '+00:00'))
            dt = dt.replace(tzinfo=rome) if dt.tzinfo is None else dt.astimezone(rome)
            if dt.date() == today: out.append(e)
        except Exception:
            continue
    return out


def _event_title(tile): return (tile.get('Title') or 'Evento').strip()
def _event_asset_id(tile): return (tile.get('AssetId') or '').strip()


def _load_events_snapshot():
    try:
        if os.path.exists(EVENTS_SNAPSHOT_FILE):
            with open(EVENTS_SNAPSHOT_FILE, "r", encoding="utf-8") as f:
                d = json.load(f)
                if isinstance(d, dict): return d
    except Exception: pass
    return {}


def _save_events_snapshot(s):
    try:
        with open(EVENTS_SNAPSHOT_FILE, "w", encoding="utf-8") as f:
            json.dump(s, f, ensure_ascii=False, indent=2)
    except Exception: pass


def _load_active_events_cache():
    try:
        if os.path.exists(ACTIVE_EVENTS_CACHE_FILE):
            with open(ACTIVE_EVENTS_CACHE_FILE, "r", encoding="utf-8") as f:
                d = json.load(f)
                if isinstance(d, dict): return d
    except Exception: pass
    return {}


def _save_active_events_cache(cache):
    try:
        with open(ACTIVE_EVENTS_CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(cache, f, ensure_ascii=False, indent=2)
    except Exception: pass


def _event_expired(start_val):
    if not start_val: return True
    try:
        try: rome = ZoneInfo('Europe/Rome')
        except Exception: rome = timezone.utc
        dt = datetime.fromisoformat(str(start_val).replace('Z', '+00:00'))
        if dt.tzinfo is None: dt = dt.replace(tzinfo=timezone.utc)
        return datetime.now(rome).date() > dt.astimezone(rome).date()
    except Exception:
        return True


def _notify_new_events(events_list):
    if not events_list: return []
    old = _load_events_snapshot()
    new_items = []
    updated = dict(old)
    for e in events_list:
        k = str(e.get('EventId') or e.get('AssetId') or '').strip()
        if not k: continue
        if k not in old: new_items.append(_event_title(e))
        updated[k] = _event_title(e)
    _save_events_snapshot(updated)
    return new_items


def _event_override_key(tile):
    title = str(tile.get('Title') or '').strip()
    if title: return title
    eid = str(tile.get('EventId') or '').strip()
    if eid: return eid
    return str(tile.get('AssetId') or '').strip()


def _event_override_key_legacy(tile):
    eid = str(tile.get('EventId') or '').strip()
    if eid: return eid
    return str(tile.get('AssetId') or '').strip()


def _lookup_logos_map(title, logos_map):
    if title in logos_map: return logos_map[title]
    t_norm = title.strip().lower()
    for key, url in logos_map.items():
        k_norm = key.strip().lower()
        if not k_norm or not t_norm.startswith(k_norm): continue
        nxt = t_norm[len(k_norm):len(k_norm) + 1]
        if nxt == '' or nxt in (':', ' ', '-'): return url
    return None


def _extract_tile_image_url(tile):
    IMG_BASE_V3 = ("https://image.discovery.indazn.com/eu/v3/eu/none/{id}"
                   "/fill/center/top/none/80/{w}/{h}/{fmt}/image?brand=dazn")

    def _build(d, w=1920, h=1083):
        if not isinstance(d, dict): return None
        iid = d.get('Id') or d.get('id')
        if not iid or not isinstance(iid, str): return None
        fmt = (d.get('ImageMimeType') or d.get('MimeType') or d.get('Format') or 'webp').lower()
        return IMG_BASE_V3.format(id=iid, w=w, h=h, fmt=fmt)

    def _from_list(imgs):
        if not isinstance(imgs, list): return None
        for it in imgs:
            u = _build(it)
            if u: return u
        return None

    for key, src in [('Image', 'tile-image'), ('PromoImage', 'tile-promo'),
                     ('BackgroundImage', 'tile-background'), ('PortraitImage', 'tile-portrait'),
                     ('LogoImage', 'tile-logo')]:
        u = _build(tile.get(key))
        if u: return u, src
    comp = tile.get('Competition') or {}
    if isinstance(comp, dict):
        u = _from_list(comp.get('Images'))
        if u: return u, 'competition-image'
    sport = tile.get('Sport') or {}
    if isinstance(sport, dict):
        u = _from_list(sport.get('Images'))
        if u: return u, 'sport-image'
    return None, None


def load_logos():
    try:
        if os.path.exists("logos.json"):
            with open("logos.json", "r", encoding='utf-8') as f:
                return json.load(f)
        default = {
            "DAZN 1": "https://image.discovery.indazn.com/eu/v3/linear-channel/none/Logo_LTV_DAZN_1/contain/center/center/none/80/85/70/png/image?brand=dazn",
            "Eurosport 1": "http://schedulesdirect-api20141201-logos.s3.amazonaws.com/stationLogos/s79652_dark_360w_270h.png",
            "NFL Network": "https://image.discovery.indazn.com/eu/v3/linear-channel/none/Logo_LTV_NFL-Network/contain/center/center/none/80/85/70/png/image?brand=dazn",
            "Red Bull TV": "https://image.discovery.indazn.com/eu/v3/linear-channel/none/Logo_LTV_Red-Bull-TV/contain/center/center/none/80/85/70/png/image?brand=dazn",
            "Unbeaten": "https://image.discovery.indazn.com/eu/v3/linear-channel/none/Logo_LTV_Unbeaten/contain/center/center/none/80/85/70/png/image?brand=dazn",
        }
        with open("logos.json", "w", encoding='utf-8') as f:
            json.dump(default, f, indent=2, ensure_ascii=False)
        return default
    except Exception as e:
        print(f"⚠️ Error logos: {e}")
        return {}


def load_logo_overrides():
    try:
        if os.path.exists(LOGO_OVERRIDES_FILE):
            with open(LOGO_OVERRIDES_FILE, "r", encoding="utf-8") as f:
                d = json.load(f)
                return d if isinstance(d, dict) else {}
    except Exception: pass
    return {}


def save_logo_overrides(data):
    try:
        with open(LOGO_OVERRIDES_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        print(f"⚠️ {e}"); return False


def load_category_logos():
    try:
        if os.path.exists(CATEGORY_LOGOS_FILE):
            with open(CATEGORY_LOGOS_FILE, "r", encoding="utf-8") as f:
                d = json.load(f)
                if isinstance(d, dict): return d
        WM = "https://commons.wikimedia.org/wiki/Special:FilePath/"
        default = {"sports": {"ciclismo": WM + "Cycling_(road)_pictogram.svg",
                              "tenis": WM + "Tennis_pictogram.svg",
                              "baloncesto": WM + "Basketball_pictogram.svg"},
                   "competitions": {"la liga": WM + "LaLiga_logo_2023.svg",
                                    "serie a": WM + "Serie_A_logo_2022.svg"}}
        with open(CATEGORY_LOGOS_FILE, "w", encoding="utf-8") as f:
            json.dump(default, f, indent=2, ensure_ascii=False)
        return default
    except Exception:
        return {"sports": {}, "competitions": {}}


def _category_logo(tile, cat_logos):
    def _match(text, mapping):
        t = _norm(text)
        if not t: return None
        for key, url in (mapping or {}).items():
            k = _norm(key)
            if k and (k in t or t in k): return url
        return None
    comp = tile.get('Competition') or {}
    comp_title = (comp.get('Title') or comp.get('Name') or '') if isinstance(comp, dict) else ''
    u = _match(str(comp_title), cat_logos.get('competitions'))
    if u: return u, 'category-competition'
    sport = tile.get('Sport') or {}
    sport_title = (sport.get('Title') or sport.get('Name') or '') if isinstance(sport, dict) else ''
    u = _match(str(sport_title), cat_logos.get('sports'))
    if u: return u, 'category-sport'
    return None, None


def _event_logo(tile, logos_map):
    title = _event_title(tile)
    okey = _event_override_key(tile)
    overrides = load_logo_overrides()
    fb = "https://m.media-amazon.com/images/G/01/digital/video/merch/subs/benefit-id/a-f/daznoriginalses/logos/channels-logo-white._CB578849766_.png"
    if okey and okey in overrides: return overrides[okey], "override"
    legacy_key = _event_override_key_legacy(tile)
    if legacy_key and legacy_key != okey and legacy_key in overrides:
        url = overrides[legacy_key]
        if okey:
            overrides[okey] = url
            try: save_logo_overrides(overrides)
            except Exception: pass
        return url, "override"
    url, src = _extract_tile_image_url(tile)
    if url: return url, src
    mapped = _lookup_logos_map(title, logos_map)
    if mapped: return mapped, "logos.json"
    cat_url, cat_src = _category_logo(tile, load_category_logos())
    if cat_url: return cat_url, cat_src
    if _tile_is_serie_a(tile): return SERIE_A_DEFAULT_LOGO, "serie-a-fallback"
    if _tile_is_serie_b(tile): return SERIE_B_DEFAULT_LOGO, "serie-b-fallback"
    return fb, "dazn-fallback"


def _group_title_for_tile(tile, default_group):
    if _tile_is_serie_a(tile): return "Serie A 🇮🇹", "serie-a"
    if _tile_is_serie_b(tile): return "Serie B 🇮🇹", "serie-b"
    if not _is_linear_channel_tile(tile):
        return config.get("group_title_events", "DAZN Eventos"), "eventos-en-canales"
    return default_group, "default"


def _tile_is_serie_a(tile):
    if not isinstance(tile, dict): return False
    comp = tile.get('Competition') or {}
    if isinstance(comp, dict): comp = comp.get('Title') or comp.get('Name') or ''
    comp = str(comp).strip()
    title = str(tile.get('Title') or '').strip()
    if _SERIE_A_REGEX.search(comp) or _SERIE_A_REGEX.search(title): return True
    return comp.lower() in ('serie a', 'serie a tim', 'serie a enilive')


def _tile_is_serie_b(tile):
    if not isinstance(tile, dict): return False
    comp = tile.get('Competition') or {}
    if isinstance(comp, dict): comp = comp.get('Title') or comp.get('Name') or ''
    comp = str(comp).strip()
    title = str(tile.get('Title') or '').strip()
    if _SERIE_B_REGEX.search(comp) or _SERIE_B_REGEX.search(title): return True
    return comp.lower() in ('serie b', 'serie bkt')


def _load_deprecated_statics():
    try:
        if os.path.exists(DEPRECATED_STATICS_FILE):
            with open(DEPRECATED_STATICS_FILE, "r", encoding="utf-8") as f:
                d = json.load(f)
            if isinstance(d, dict):
                return d.get("deprecated", {}) if "deprecated" in d else d
    except Exception: pass
    return {}


def _save_deprecated_statics(data):
    try:
        with open(DEPRECATED_STATICS_FILE, "w", encoding="utf-8") as f:
            json.dump({"_meta": {"updated": datetime.now().isoformat(timespec="seconds")},
                       "deprecated": data}, f, ensure_ascii=False, indent=2)
        return True
    except Exception: return False


def _deprecate_static_for_title(title, old_kid, new_kid, reason="KID mismatch"):
    if not title: return False
    key = re.sub(r"\s+", " ", str(title).replace("\u00a0", " ")).strip().upper()
    dep = _load_deprecated_statics()
    dep[key] = {"old_kid": (old_kid or "").lower().replace("-", ""),
                "new_kid": (new_kid or "").lower().replace("-", ""),
                "reason": reason, "at": datetime.now().isoformat(timespec="seconds")}
    return _save_deprecated_statics(dep)


def _find_clearkey_for_title(title):
    if not title: return None
    _dep = _load_deprecated_statics()
    _key_norm = re.sub(r"\s+", " ", str(title).replace("\u00a0", " ")).strip().upper()
    if _key_norm in _dep: return None
    t_norm = re.sub(r"\s+", " ", str(title).replace("\u00a0", " ")).strip().upper()
    aliases = {
        "RADIO TV SERIE A": "RADIO TV RDS",
        "NFL NETWORK: LIVE 24/7 COVERAGE": "NFL NETWORK",
        "EUROSPORT 1 (🇮🇹)": "EUROSPORT 1",
        "EUROSPORT 2 (🇮🇹)": "EUROSPORT 2",
        "DAZN FOCUS SERIE A": "FOCUS SERIE A",
        "FOCUS SERIE A 24/7": "FOCUS SERIE A",
    }
    if t_norm in aliases: return STATIC_CLEARKEY_KEYS.get(aliases[t_norm])
    if t_norm in STATIC_CLEARKEY_KEYS: return STATIC_CLEARKEY_KEYS[t_norm]

    def _squash(s): return re.sub(r"\s+", "", s.upper())
    t_sq = _squash(t_norm)
    candidates = []
    for k, kv in STATIC_CLEARKEY_KEYS.items():
        k_sq = _squash(k)
        if k_sq == t_sq: candidates.append((1000, k, kv))
        elif k in t_norm or t_norm in k or k_sq in t_sq or t_sq in k_sq:
            candidates.append((len(k), k, kv))
    if candidates:
        candidates.sort(key=lambda x: -x[0])
        return candidates[0][2]
    return None


def _build_m3u_entry(title, aid, grp_title, group_logo, logo_url,
                     manifest_url, cdn_name, cdn_token, kid_hex, key_hex,
                     manifest_type="mpd", license_type="org.w3.clearkey",
                     license_format="kid_key"):
    kid_clean = (kid_hex or "").lower().replace("-", "")
    key_clean = (key_hex or "").lower().replace("-", "")
    if license_format == "json":
        license_key = json.dumps({kid_clean: key_clean}, separators=(",", ":"))
    else:
        license_key = f"{kid_clean}:{key_clean}"
    return (
        f'#EXTINF:-1 tvg-id="{aid}" tvg-name="{title}" '
        f'group-logo="{group_logo}" tvg-logo="{logo_url}" '
        f'group-title="{grp_title}",{title}\n'
        f'#KODIPROP:inputstream.adaptive.manifest_type={manifest_type}\n'
        f'#KODIPROP:inputstream.adaptive.license_type={license_type}\n'
        f'#KODIPROP:inputstream.adaptive.license_key={license_key}\n'
        f'#KODIPROP:inputstream.adaptive.stream_headers={cdn_name}={cdn_token}\n'
        f'#EXTVLCOPT:http-user-agent={USER_AGENT}\n'
        f'#EXTVLCOPT:http-referrer=https://www.dazn.com/\n'
        f'{manifest_url}\n'
    )


# ==============================================================
# 🚀 GENERACIÓN DUAL (con WARP + sin WARP)
# ==============================================================
def _generate_channels_both_variants(selected_channels=None):
    do_warp = config.get("warp_auto_toggle", True)
    out_normal = config.get("output_file_channels", OUTPUT_FILE_CHANNELS_DEFAULT)
    out_wap = config.get("output_file_wap", OUTPUT_FILE_CHANNELS_WAP)

    if not do_warp:
        print("ℹ️ WARP auto-toggle desactivado")
        generate_dazn_playlist(output_file=out_normal, selected_channels=selected_channels)
        return

    st_initial = _warp_status()
    print(f"\n🌐 Estado inicial de WARP: {st_initial or 'desconocido'}")

    if st_initial == "connected":
        print(f"📄 Generando CON WARP → {out_wap}")
        generate_dazn_playlist(output_file=out_wap, selected_channels=selected_channels)
        if _warp_disconnect():
            print(f"📄 Generando SIN WARP → {out_normal}")
            generate_dazn_playlist(output_file=out_normal, selected_channels=selected_channels)
        _warp_connect()
    else:
        print(f"📄 Generando SIN WARP → {out_normal}")
        generate_dazn_playlist(output_file=out_normal, selected_channels=selected_channels)
        if _warp_connect():
            print(f"📄 Generando CON WARP → {out_wap}")
            generate_dazn_playlist(output_file=out_wap, selected_channels=selected_channels)
        if st_initial == "disconnected":
            _warp_disconnect()

    if config.get("github_auto_push", False):
        _github_auto_push(files=[out_normal, out_wap])


def _generate_events_both_variants(events_list, **kwargs):
    do_warp = config.get("warp_auto_toggle", True)
    out_normal = config.get("output_file_events", OUTPUT_FILE_EVENTS_DEFAULT)
    out_wap = config.get("output_file_events_wap", "eventos_recogidos_WAP.m3u")

    if not do_warp:
        generate_m3u_from_events(events_list, output_file=out_normal, **kwargs)
        return out_normal

    st_initial = _warp_status()
    print(f"\n🌐 Estado inicial de WARP: {st_initial or 'desconocido'}")

    if st_initial == "connected":
        generate_m3u_from_events(events_list, output_file=out_wap, **kwargs)
        if _warp_disconnect():
            generate_m3u_from_events(events_list, output_file=out_normal, **kwargs)
        _warp_connect()
    else:
        generate_m3u_from_events(events_list, output_file=out_normal, **kwargs)
        if _warp_connect():
            generate_m3u_from_events(events_list, output_file=out_wap, **kwargs)
        if st_initial == "disconnected":
            _warp_disconnect()

    if config.get("github_auto_push", False):
        _github_auto_push(files=[out_normal, out_wap])
    return out_normal


def generate_dazn_playlist(output_file=OUTPUT_FILE_CHANNELS_DEFAULT, selected_channels=None):
    console_lock.acquire()
    try:
        print(f"\n🚀 Generando playlist de canales: {output_file}")
        logos = load_logos()
        group_logo = ("https://m.media-amazon.com/images/G/01/digital/video/merch/"
                      "subs/benefit-id/a-f/daznoriginalses/logos/"
                      "channels-logo-white._CB578849766_.png")
        default_group = config.get("group_title", "DAZN Canales 🇮🇹")
        if selected_channels is None:
            all_channels = get_channels(_get_token())
            if not all_channels:
                print("❌ Sin canales"); return False
            selected_channels = all_channels
        print(f"📊 {len(selected_channels)} canales en entrada")
        m3u = "#EXTM3U\n"
        successi = 0; senza_chiavi = []; senza_playback = []
        ck_hunter_wins = 0; key_hunter_wins = 0; wvd_wins = 0

        for i, ch in enumerate(selected_channels, 1):
            title = (ch.get('Title') or '?').strip()
            aid = (ch.get('AssetId') or '').strip()
            grp_title, _ = _group_title_for_tile(ch, default_group)
            logo_url, _ = _event_logo(ch, logos)
            if not logo_url: logo_url = group_logo
            print(f'[{i}/{len(selected_channels)}] {title}...', end=' ', flush=True)
            if not aid:
                print('❌ Sin AssetId'); senza_playback.append(title); continue
            kk_static = _find_clearkey_for_title(title)
            (manifest_url, cdn_name, cdn_token, la_url, lock_id,
             err_code, clearkey_dyn, err_msg) = get_single(_get_token(), aid, pin)
            if not manifest_url:
                print('❌ Playback no disponible'); senza_playback.append(title); continue
            delete_concurrency(_get_token(), lock_id)
            kid_hex = key_hex = None
            if clearkey_dyn and clearkey_dyn.get('kid') and clearkey_dyn.get('key'):
                kid_hex = clearkey_dyn['kid']; key_hex = clearkey_dyn['key']
                try: ck_hunter_register(kid_hex, key_hex, title)
                except Exception: pass
            else:
                print('🔍 Búsqueda KID...', end=' ', flush=True)
                manifest_kid = _extract_kid_from_mpd(manifest_url, _get_token(),
                                                       cdn_name=cdn_name, cdn_token=cdn_token)
                if manifest_kid:
                    db_key, db_src = ck_hunter_lookup(manifest_kid)
                    if db_key:
                        kid_hex, key_hex = manifest_kid, db_key
                        ck_hunter_wins += 1
                        print(f'(KID: {db_src})', end=' ', flush=True)
                    else:
                        try:
                            _flat = _load_external_keys()
                            if manifest_kid not in _flat:
                                _flat[manifest_kid] = {"key": "", "name": title[:120],
                                                        "added": datetime.now().isoformat(timespec="seconds"),
                                                        "status": "placeholder"}
                                _save_external_keys(_flat); _invalidate_kid_index()
                        except Exception: pass
                        print(f'(KID {manifest_kid[:8]}… placeholder)', end=' ', flush=True)
                if not kid_hex and manifest_kid and la_url:
                    print('🔐 KEY Hunter...', end=' ', flush=True)
                    hunted = key_hunter_request_license(manifest_kid, la_url, _get_token(),
                                                        cdn_name=cdn_name, cdn_token=cdn_token,
                                                        verbose=False)
                    if hunted:
                        kid_hex, key_hex = manifest_kid, hunted
                        key_hunter_wins += 1
                        try: ck_hunter_register(manifest_kid, hunted, title)
                        except Exception: pass
                        print('✅', end=' ', flush=True)
                if not kid_hex and kk_static:
                    static_kid, static_key = kk_static
                    static_kid_norm = static_kid.lower().replace('-', '')
                    if manifest_kid is None or manifest_kid == static_kid_norm:
                        kid_hex, key_hex = static_kid_norm, static_key
                    else:
                        try:
                            _deprecate_static_for_title(title, static_kid_norm, manifest_kid)
                        except Exception: pass
            if (not kid_hex) and la_url and config.get("wvd_enabled", True) and _pywidevine_available():
                print('🎬 WVD Hunter...', end=' ', flush=True)
                wvd = widevine_attempt(manifest_url, la_url, title, _get_token(),
                                        cdn_name=cdn_name, cdn_token=cdn_token, verbose=True)
                if wvd:
                    kid_hex, key_hex = wvd["kid"], wvd["key"]
                    wvd_wins += 1
                    print('✅', end=' ', flush=True)
                else:
                    print('✗', end=' ', flush=True)
            if not kid_hex or not key_hex:
                print('❌ Ninguna clave')
                senza_chiavi.append(title); continue
            title_sq = re.sub(r"\s+", "", title.upper())
            spec = (CHANNEL_STREAM_SPECS.get(title.upper())
                    or CHANNEL_STREAM_SPECS.get(title_sq) or {})
            m3u += _build_m3u_entry(title, aid, grp_title, group_logo, logo_url,
                                     manifest_url, cdn_name, cdn_token, kid_hex, key_hex,
                                     manifest_type=spec.get("manifest_type", "mpd"),
                                     license_type=spec.get("license_type", "org.w3.clearkey"),
                                     license_format=spec.get("license_format", "kid_key"))
            successi += 1
            print('✅ OK')
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(m3u)
        print(f"\n📊 RESULTADO CANALES: {successi}/{len(selected_channels)} OK")
        if ck_hunter_wins: print(f"   🎯 KID lookup: {ck_hunter_wins}")
        if key_hunter_wins: print(f"   🔐 KEY Hunter: {key_hunter_wins}")
        if wvd_wins: print(f"   🎬 WVD: {wvd_wins}")
        if senza_chiavi: print(f"   🔑 Sin clave ({len(senza_chiavi)}): " + ", ".join(senza_chiavi[:10]))
        if senza_playback: print(f"   ⚠️ Playback: " + ", ".join(senza_playback[:10]))
        return True
    finally:
        console_lock.release()


def generate_m3u_from_events(events_list, output_file=OUTPUT_FILE_EVENTS_DEFAULT,
                              verbose=True, auto_pending=False,
                              retain_cache=False, use_ck_hunter=True):
    console_lock.acquire()
    try:
        cache = {}
        if retain_cache:
            cache = _load_active_events_cache()
            cache = {k: v for k, v in cache.items() if not _event_expired(v.get("Start", ""))}
        if not events_list and not (retain_cache and cache):
            print("❌ Sin eventos."); return None
        logos = load_logos()
        group_logo = ("https://m.media-amazon.com/images/G/01/digital/video/merch/"
                      "subs/benefit-id/a-f/daznoriginalses/logos/"
                      "channels-logo-white._CB578849766_.png")
        default_group = config.get("group_title_events", "DAZN Eventos")
        print(f"\n🚀 Generando M3U eventos: {output_file} ({len(events_list)} a verificar)")
        m3u = "#EXTM3U\n"
        successi = 0; falliti = []; senza_chiave = []; programmati = []
        retained = 0; ck_hunter_wins = 0; ck_hunter_miss = 0; wvd_wins = 0
        expired_discarded = 0

        for i, tile in enumerate(events_list, 1):
            title = _event_title(tile)
            aid = _event_asset_id(tile)
            eid = tile.get('EventId') or ''
            tt = tile.get('Type') or '-'
            key = eid or aid
            grp_title, _ = _group_title_for_tile(tile, default_group)
            logo_url, logo_src = _event_logo(tile, logos)
            if not logo_url: logo_url = group_logo
            print(f'[{i}/{len(events_list)}] [{tt}] {title}...', end=' ', flush=True)
            if not aid:
                print('❌ Sin AssetId'); falliti.append((tile, title)); continue
            static_kk = _find_clearkey_for_title(title)
            (manifest_url, cdn_name, cdn_token, la_url, lock_id,
             err_code, clearkey_info, err_msg) = get_single(_get_token(), aid, pin)
            if not manifest_url:
                if err_code in PERMANENT_ERROR_CODES:
                    print('🚫 No elegible'); continue
                if err_code in PENDING_ERROR_CODES:
                    msg_lower = (err_msg or "").lower()
                    if "does not exist" in msg_lower:
                        print('🗑 Caducado'); expired_discarded += 1; continue
                    if auto_pending:
                        try: add_pending_event(tile, "Programado")
                        except Exception: pass
                        print('📅 Programado'); programmati.append(title)
                    else:
                        print('📅 No disponible')
                        falliti.append((tile, title))
                    continue
                cd = cache.get(key) if (retain_cache and key) else None
                if cd:
                    kid_hex = cd.get('kid'); key_hex = cd.get('key')
                    if kid_hex and key_hex:
                        m3u += _build_m3u_entry(title, aid, grp_title, group_logo, logo_url,
                                                cd['manifest_url'], cd['cdn_name'],
                                                cd['cdn_token'], kid_hex, key_hex)
                        successi += 1
                        print('♻️ Desde caché'); continue
                print('❌'); falliti.append((tile, title)); continue
            delete_concurrency(_get_token(), lock_id)
            if not clearkey_info and static_kk:
                kid_hex, key_hex = static_kk
                clearkey_info = {"kid": kid_hex, "key": key_hex}
                print('🔐 Estática...', end=' ', flush=True)
            if not clearkey_info and use_ck_hunter:
                print('🔍 CK Hunter...', end=' ', flush=True)
                hunter = ck_hunter_attempt(manifest_url, title, _get_token(),
                                            cdn_name=cdn_name, cdn_token=cdn_token)
                if hunter:
                    clearkey_info = {"kid": hunter['kid'], "key": hunter['key']}
                    ck_hunter_wins += 1
                else:
                    ck_hunter_miss += 1
            if not clearkey_info and la_url:
                print('🔐 KEY Hunter...', end=' ', flush=True)
                manifest_kid = _extract_kid_from_mpd(manifest_url, _get_token(),
                                                       cdn_name=cdn_name, cdn_token=cdn_token)
                if manifest_kid:
                    hunted = key_hunter_request_license(manifest_kid, la_url, _get_token(),
                                                        cdn_name=cdn_name, cdn_token=cdn_token,
                                                        verbose=False)
                    if hunted:
                        clearkey_info = {"kid": manifest_kid, "key": hunted}
                        try: ck_hunter_register(manifest_kid, hunted, title)
                        except Exception: pass
            if not clearkey_info and la_url and config.get("wvd_enabled", True) and _pywidevine_available():
                print('🎬 WVD Hunter...', end=' ', flush=True)
                wvd = widevine_attempt(manifest_url, la_url, title, _get_token(),
                                        cdn_name=cdn_name, cdn_token=cdn_token, verbose=True)
                if wvd:
                    clearkey_info = {"kid": wvd["kid"], "key": wvd["key"]}
                    wvd_wins += 1
            if not clearkey_info:
                print('❌ Ninguna clave')
                senza_chiave.append(title); continue
            kid_hex = clearkey_info['kid']; key_hex = clearkey_info['key']
            try: ck_hunter_register(kid_hex, key_hex, title)
            except Exception: pass
            m3u += _build_m3u_entry(title, aid, grp_title, group_logo, logo_url,
                                     manifest_url, cdn_name, cdn_token, kid_hex, key_hex)
            successi += 1
            print('✅ OK')
            if retain_cache and key:
                cache[key] = {"tile": tile, "Start": tile.get('Start') or tile.get('EventStartTime') or '',
                              "manifest_url": manifest_url, "cdn_name": cdn_name,
                              "cdn_token": cdn_token, "kid": kid_hex, "key": key_hex,
                              "LastOkAt": datetime.now().isoformat(timespec="seconds")}
        if retain_cache:
            present = set((e.get('EventId') or e.get('AssetId') or '') for e in events_list)
            for k, cd in cache.items():
                if k in present: continue
                tile = cd.get("tile") or {}
                title = _event_title(tile) or "Evento"
                aid = tile.get('AssetId') or ''
                grp_title, _ = _group_title_for_tile(tile, default_group)
                logo_url, _ = _event_logo(tile, logos)
                if not logo_url: logo_url = group_logo
                if cd.get('kid') and cd.get('key'):
                    m3u += _build_m3u_entry(title, aid, grp_title, group_logo, logo_url,
                                             cd['manifest_url'], cd['cdn_name'],
                                             cd['cdn_token'], cd['kid'], cd['key'])
                    successi += 1; retained += 1
            _save_active_events_cache(cache)
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(m3u)
        if auto_pending and successi:
            try:
                failed_titles = {t for _, t in falliti} | set(programmati)
                successful_keys = {(e.get('EventId') or e.get('AssetId') or '')
                                    for e in events_list if _event_title(e) not in failed_titles}
                still = [p for p in load_pending_events()
                         if (p.get('EventId') or p.get('AssetId') or '') not in successful_keys]
                save_pending_events(still)
            except Exception as e:
                print(f"⚠️ limpieza pending: {e}")
        print(f"\n📊 RESULTADO: {successi} OK (caché: {retained})")
        if ck_hunter_wins: print(f"   🎯 CK Hunter: {ck_hunter_wins}")
        if wvd_wins: print(f"   🎬 WVD: {wvd_wins}")
        if expired_discarded: print(f"   🗑 Caducados: {expired_discarded}")
        if senza_chiave: print(f"   🔑 Sin clave ({len(senza_chiave)}): " + ", ".join(senza_chiave[:10]))
        if programmati: print(f"   📅 Programados: {len(programmati)}")
        return output_file
    finally:
        console_lock.release()


# ==============================================================
# CONFIGURACIÓN
# ==============================================================
config = {
    "events_scheduler_active": False,
    "events_scheduler_interval_minutes": 15,
    "events_scheduler_mode": "interval",
    "events_fixed_times": ["14:45", "17:45", "20:30"],
    "events_only_today": True,
    "events_include_live": True,
    "events_filter_type": "all",
    "events_filter_value": None,
    "output_file_events": OUTPUT_FILE_EVENTS_DEFAULT,
    "output_file_events_wap": "eventos_recogidos_WAP.m3u",
    "channels_scheduler_active": False,
    "channels_scheduler_interval_minutes": 60,
    "channels_scheduler_mode": "interval",
    "channels_fixed_times": ["14:45", "17:45", "20:30"],
    "channels_regenerate_with_events": False,
    "output_file_channels": OUTPUT_FILE_CHANNELS_DEFAULT,
    "output_file_wap": OUTPUT_FILE_CHANNELS_WAP,
    "pending_watcher_active": True,
    "pending_watcher_interval_sec": 30,
    "pending_lead_minutes": 5,
    "pin": "",
    "group_title": "DAZN Canales 🇮🇹",
    "group_title_events": "DAZN Eventos",
    "selected_channels": [],
    "selected_titles": [],
    "ck_hunter_enabled": True,
    "key_hunter_enabled": True,
    "har_recording_enabled": True,
    "har_grace_seconds": 90,
    "hls_output_enabled": False,
    "output_file_hls": OUTPUT_FILE_HLS_DEFAULT,
    "hls_base_url": HLS_BASE_URL_DEFAULT,
    "wvd_enabled": True,
    "wvd_file": WVD_FILE_DEFAULT,
    "browser_type": "auto",
    "warp_auto_toggle": True,
    "github_auto_push": True,
    "github_repo_dir": "",
    "github_user": "carmenchica3636",
    "github_repo": "listas-iptv",
    "github_branch": "main",
    "github_remote": "origin",
}


def load_config():
    global config
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                for k, v in json.load(f).items():
                    config[k] = v
        except Exception as e:
            print(f"⚠️ config: {e}")


def save_config():
    try:
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"⚠️ save: {e}")


load_config()


# ==============================================================
# PENDING + process
# ==============================================================
pending_events_lock = threading.Lock()
console_lock = threading.Lock()
channels_regen_trigger_lock = threading.Lock()
CHANNELS_REGEN_SKIP_WINDOW_SEC = 180


def load_pending_events():
    try:
        if os.path.exists(PENDING_EVENTS_FILE):
            with open(PENDING_EVENTS_FILE, "r", encoding="utf-8") as f:
                d = json.load(f)
                return d if isinstance(d, list) else []
    except Exception: pass
    return []


def save_pending_events(data):
    try:
        with open(PENDING_EVENTS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        print(f"⚠️ {e}"); return False


def _pending_event_start_ts(ev):
    v = ev.get('Start') or ev.get('EventStartTime') or ''
    if not v: return None
    try: return datetime.fromisoformat(str(v).replace('Z', '+00:00')).timestamp()
    except Exception: return None


def add_pending_event(tile, reason=""):
    data = load_pending_events()
    aid = str(tile.get('AssetId') or '').strip()
    eid = str(tile.get('EventId') or '').strip()
    key = eid or aid
    if not key: return False
    existed = any((x.get('EventId') or x.get('AssetId') or '') == key for x in data)
    data = [x for x in data if (x.get('EventId') or x.get('AssetId') or '') != key]
    entry = dict(tile)
    entry["AssetId"] = aid; entry["EventId"] = eid
    entry["Start"] = tile.get('Start') or tile.get('EventStartTime') or ''
    entry["AddedAt"] = datetime.now().isoformat(timespec="seconds")
    entry["Reason"] = reason or "Manual"
    data.append(entry)
    return save_pending_events(data)


def _process_pending_events(pin_arg):
    if not pending_events_lock.acquire(blocking=False):
        print("⏳ pending en curso"); return []
    try:
        pending = load_pending_events()
        if not pending: return []
        now_dt = datetime.now()
        fresh_pending = []; discarded = 0
        for ev in pending:
            try:
                age_hours = (now_dt - datetime.fromisoformat(ev.get("AddedAt", ""))).total_seconds() / 3600
                if age_hours > MAX_PENDING_AGE_HOURS:
                    discarded += 1; continue
            except Exception: pass
            fresh_pending.append(ev)
        if discarded:
            print(f"🗑 Descartados {discarded} pendientes caducados")
            save_pending_events(fresh_pending); pending = fresh_pending
        lead_sec = max(0, config.get("pending_lead_minutes", 5)) * 60
        now_ts = datetime.now(timezone.utc).timestamp()
        due = []; not_due = []
        for ev in pending:
            start_ts = _pending_event_start_ts(ev)
            if start_ts is None or now_ts >= (start_ts - lead_sec): due.append(ev)
            else: not_due.append(ev)
        if not due: return []
        console_lock.acquire()
        try:
            print(f"\n⏳ Verificando {len(due)}/{len(pending)} pending...")
            ready = []; still = []
            for ev in due:
                aid = ev.get('AssetId') or ''; title = ev.get('Title') or '?'
                if not aid: continue
                try:
                    r = get_single(_get_token(), aid, pin_arg)
                    if r and r[0]:
                        ready_tile = dict(ev)
                        ready_tile['Type'] = ev.get('Type') or 'UpComing'
                        ready.append(ready_tile)
                        print(f"   ✅ {title}")
                    else:
                        ev['LastAttempt'] = datetime.now().isoformat(timespec="seconds")
                        still.append(ev); print(f"   ⏳ {title}")
                except Exception:
                    still.append(ev); print(f"   ⏳ {title}")
            save_pending_events(still + not_due)
        finally: console_lock.release()
        return ready
    finally: pending_events_lock.release()


# ==============================================================
# SCHEDULERS
# ==============================================================
events_scheduler_running = False
events_scheduler_thread = None
events_scheduler_next_update = None
events_scheduler_lock = threading.Lock()

channels_scheduler_running = False
channels_scheduler_thread = None
channels_scheduler_next_update = None
channels_scheduler_lock = threading.Lock()

pending_watcher_running = False
pending_watcher_thread = None


def _parse_hhmm(s):
    try:
        h, m = s.strip().split(":"); h, m = int(h), int(m)
        if 0 <= h <= 23 and 0 <= m <= 59: return h, m
    except Exception: pass
    return None


def _load_channel_snapshot():
    try:
        if os.path.exists(CHANNEL_SNAPSHOT_FILE):
            with open(CHANNEL_SNAPSHOT_FILE, "r", encoding="utf-8") as f:
                d = json.load(f)
                if isinstance(d, dict): return d
    except Exception: pass
    return {"last_run": "", "channels": {}}


def _save_channel_snapshot(channels):
    snap = {"last_run": datetime.now().isoformat(timespec="seconds"),
            "channels": {c.get('AssetId', ''): c.get('Title', '') for c in channels if c.get('AssetId')}}
    try:
        with open(CHANNEL_SNAPSHOT_FILE, "w", encoding="utf-8") as f:
            json.dump(snap, f, ensure_ascii=False, indent=2)
    except Exception: pass


def _diff_channels(new_channels):
    old = _load_channel_snapshot().get("channels", {})
    new = {c.get('AssetId', ''): c.get('Title', '') for c in new_channels if c.get('AssetId')}
    added = {k: v for k, v in new.items() if k not in old}
    removed = {k: v for k, v in old.items() if k not in new}
    if added: print(f"  🆕 {len(added)} canales NUEVOS")
    if removed: print(f"  🔻 {len(removed)} canales DESAPARECIDOS")


def _resolve_channels_selection(all_channels):
    if not all_channels: return []
    sel = list(config.get("selected_channels", []) or [])
    if not sel: return all_channels
    snapshot_ids = set(_load_channel_snapshot().get("channels", {}).keys())
    all_by_id = {c.get('AssetId'): c for c in all_channels if c.get('AssetId')}
    added = [aid for aid in all_by_id if aid not in sel and aid not in snapshot_ids]
    if added:
        print(f"\n🆕 {len(added)} canales nuevos → auto-seleccionados")
        sel.extend(added); config["selected_channels"] = sel; save_config()
    sel_set = set(sel)
    result = [c for c in all_channels if c.get('AssetId') in sel_set]
    return result or all_channels


def _run_channels_scheduler_cycle():
    try:
        _load_token_safe(do_refresh_if_possible=True)
    except Exception as e:
        print(f"⚠️ refresh: {e}"); return
    print("\n📺 Ciclo CANALES...")
    all_ch = get_channels(_get_token())
    if not all_ch:
        print("❌ Sin canales"); return
    _diff_channels(all_ch)
    selected = _resolve_channels_selection(all_ch)
    _generate_channels_both_variants(selected_channels=selected)
    _save_channel_snapshot(all_ch)


def _run_events_scheduler_cycle():
    try:
        _load_token_safe(do_refresh_if_possible=True)
    except Exception as e:
        print(f"⚠️ refresh: {e}"); return
    include_live = config.get("events_include_live", True)
    only_today = config.get("events_only_today", True)
    print("\n🔄 Ciclo EVENTOS...")
    try:
        events = get_scheduled_events(_get_token(), include_live=include_live, verbose=True)
    except Exception as e:
        print(f"❌ {e}"); events = []
    if only_today: events = filter_events_today(events)
    filt = get_events_filter()
    if filt[0] != "all": events = apply_event_filter(events, filt)
    pend = _process_pending_events(pin)
    if pend:
        ks = set((e.get('EventId') or e.get('AssetId') or '') for e in events)
        for p in pend:
            k = p.get('EventId') or p.get('AssetId') or ''
            if k and k not in ks: events.append(p); ks.add(k)
    _notify_new_events(events)
    _generate_events_both_variants(events, auto_pending=True, retain_cache=True,
                                    use_ck_hunter=config.get("ck_hunter_enabled", True))


def events_scheduler_loop():
    global events_scheduler_running, events_scheduler_next_update
    print(f"▶️ Scheduler EVENTOS (cada {config.get('events_scheduler_interval_minutes', 15)} min)")
    try: _run_events_scheduler_cycle()
    except Exception as e: print(f"❌ {e}")
    while events_scheduler_running:
        wait = config.get("events_scheduler_interval_minutes", 15) * 60
        nxt = time.time() + wait
        with events_scheduler_lock: events_scheduler_next_update = nxt
        while events_scheduler_running and time.time() < nxt: time.sleep(1)
        if not events_scheduler_running: break
        try: _run_events_scheduler_cycle()
        except Exception as e: print(f"❌ {e}")
    print("⏹️ Scheduler EVENTOS detenido")


def channels_scheduler_loop():
    global channels_scheduler_running, channels_scheduler_next_update
    print(f"▶️ Scheduler CANALES (cada {config.get('channels_scheduler_interval_minutes', 60)} min)")
    try: _run_channels_scheduler_cycle()
    except Exception as e: print(f"❌ {e}")
    while channels_scheduler_running:
        wait = config.get("channels_scheduler_interval_minutes", 60) * 60
        nxt = time.time() + wait
        with channels_scheduler_lock: channels_scheduler_next_update = nxt
        while channels_scheduler_running and time.time() < nxt: time.sleep(1)
        if not channels_scheduler_running: break
        try: _run_channels_scheduler_cycle()
        except Exception as e: print(f"❌ {e}")
    print("⏹️ Scheduler CANALES detenido")


def pending_watcher_loop():
    global pending_watcher_running
    interval = max(5, config.get("pending_watcher_interval_sec", 30))
    print(f"▶️ Watcher PENDING (cada {interval}s)")
    while pending_watcher_running:
        try:
            if load_pending_events():
                try: _load_token_safe(do_refresh_if_possible=True)
                except Exception: pass
                ready = _process_pending_events(pin)
                if ready:
                    _generate_events_both_variants(ready, auto_pending=True,
                                                    retain_cache=True,
                                                    use_ck_hunter=config.get("ck_hunter_enabled", True))
        except Exception as e:
            print(f"❌ Watcher: {e}")
        for _ in range(interval):
            if not pending_watcher_running: break
            time.sleep(1)
    print("⏹️ Watcher PENDING detenido")


def start_events_scheduler():
    global events_scheduler_running, events_scheduler_thread
    if events_scheduler_running: return
    events_scheduler_running = True; config["events_scheduler_active"] = True; save_config()
    events_scheduler_thread = threading.Thread(target=events_scheduler_loop, daemon=True)
    events_scheduler_thread.start()


def stop_events_scheduler():
    global events_scheduler_running, events_scheduler_next_update
    if not events_scheduler_running: return
    events_scheduler_running = False; config["events_scheduler_active"] = False; save_config()
    with events_scheduler_lock: events_scheduler_next_update = None


def start_channels_scheduler():
    global channels_scheduler_running, channels_scheduler_thread
    if channels_scheduler_running: return
    channels_scheduler_running = True; config["channels_scheduler_active"] = True; save_config()
    channels_scheduler_thread = threading.Thread(target=channels_scheduler_loop, daemon=True)
    channels_scheduler_thread.start()


def stop_channels_scheduler():
    global channels_scheduler_running, channels_scheduler_next_update
    if not channels_scheduler_running: return
    channels_scheduler_running = False; config["channels_scheduler_active"] = False; save_config()
    with channels_scheduler_lock: channels_scheduler_next_update = None


def start_pending_watcher():
    global pending_watcher_running, pending_watcher_thread
    if pending_watcher_running: return
    pending_watcher_running = True
    config["pending_watcher_active"] = True; save_config()
    pending_watcher_thread = threading.Thread(target=pending_watcher_loop, daemon=True)
    pending_watcher_thread.start()


def stop_pending_watcher():
    global pending_watcher_running
    if not pending_watcher_running: return
    pending_watcher_running = False
    config["pending_watcher_active"] = False; save_config()


def get_selected_channels_from_config():
    sel = config.get("selected_channels", [])
    if not sel: return None
    all_ch = get_channels(_get_token())
    if not all_ch: return None
    return _resolve_channels_selection(all_ch)
# ==============================================================
# PERFILES
# ==============================================================
profiles_lock = threading.Lock()


def _load_profiles():
    try:
        if os.path.exists(PROFILES_FILE):
            with open(PROFILES_FILE, "r", encoding="utf-8") as f:
                d = json.load(f)
                if isinstance(d, dict) and "profiles" in d: return d
    except Exception: pass
    return {"active": "", "profiles": {}}


def _save_profiles(data):
    try:
        with open(PROFILES_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"⚠️ profiles.json: {e}"); return False


def list_profiles():
    with profiles_lock:
        data = _load_profiles()
    active = data.get("active", "")
    out = []
    for name, info in (data.get("profiles") or {}).items():
        tok = info.get("token", "") or ""
        out.append({"name": name, "label": info.get("label", name),
                    "country": info.get("country", "?"),
                    "token_short": (tok[:18] + "..." + tok[-8:]) if len(tok) > 30 else (tok or "—"),
                    "created": info.get("created", "?"),
                    "updated": info.get("updated", ""),
                    "active": (name == active)})
    out.sort(key=lambda x: (not x["active"], x["name"]))
    return out


def add_profile(name, token=None, label=None, country=None, set_active=False):
    if not name or not str(name).strip(): return False, "Nombre vacío"
    name = str(name).strip().lower().replace(" ", "_")
    if token is None:
        try:
            with open("token.txt", "r", encoding="utf-8") as f:
                token = f.read().strip()
        except Exception:
            return False, "No hay token en token.txt"
    if not token or token.count(".") != 2:
        return False, "Token no válido"
    if country is None:
        try:
            decoded = jwt.decode(token, options={"verify_signature": False})
            country = decoded.get("contentCountry", "?")
        except Exception: country = "?"
    with profiles_lock:
        data = _load_profiles()
        data.setdefault("profiles", {})
        data["profiles"][name] = {"label": label or name, "token": token,
                                    "country": country,
                                    "created": data["profiles"].get(name, {}).get("created")
                                                or datetime.now().isoformat(timespec="seconds"),
                                    "updated": datetime.now().isoformat(timespec="seconds")}
        if set_active or not data.get("active"): data["active"] = name
        _save_profiles(data)
    if data.get("active") == name:
        try:
            with open("token.txt", "w", encoding="utf-8") as f:
                f.write(token)
            _set_token(token)
        except Exception: pass
    return True, f"Perfil '{name}' guardado ({country})"


def switch_profile(name):
    global VERSION
    name = str(name).strip().lower().replace(" ", "_")
    with profiles_lock:
        data = _load_profiles()
        if name not in (data.get("profiles") or {}):
            return False, f"Perfil '{name}' no encontrado"
        data["active"] = name; _save_profiles(data)
        info = data["profiles"][name]
    tok = info.get("token", "")
    if not tok or tok.count(".") != 2:
        return False, f"Token del perfil '{name}' inválido"
    try:
        with open("token.txt", "w", encoding="utf-8") as f:
            f.write(tok)
    except Exception as e:
        return False, f"Error escribiendo token.txt: {e}"
    _set_token(tok)
    try: VERSION = get_version()
    except Exception: pass
    return True, f"🔀 Cambiado a '{name}'"


def delete_profile(name):
    name = str(name).strip().lower().replace(" ", "_")
    with profiles_lock:
        data = _load_profiles()
        profs = data.get("profiles") or {}
        if name not in profs: return False, "No existe"
        if len(profs) <= 1: return False, "No puedes eliminar el último"
        del profs[name]
        if data.get("active") == name: data["active"] = next(iter(profs))
        _save_profiles(data)
    return True, f"Perfil '{name}' eliminado"


def get_active_profile():
    with profiles_lock:
        data = _load_profiles()
    name = data.get("active", "")
    info = (data.get("profiles") or {}).get(name, {})
    return name, info


# ==============================================================
# HAR IMPORTER
# ==============================================================
def _parse_clearkey_json_body(text):
    out = []
    if not text or not isinstance(text, str): return out
    candidates = [text]
    m = re.search(r'\{[^{}]*"keys"\s*:\s*\[.*?\][^{}]*\}', text, re.DOTALL)
    if m: candidates.append(m.group(0))
    seen = set()
    for cand in candidates:
        try: obj = json.loads(cand)
        except Exception: continue
        keys = obj.get("keys") if isinstance(obj, dict) else None
        if not isinstance(keys, list): continue
        for k in keys:
            if not isinstance(k, dict): continue
            kid_raw = k.get("kid") or k.get("KID")
            key_raw = k.get("k") or k.get("K") or k.get("key") or k.get("KEY")
            if not kid_raw or not key_raw: continue
            kid_hex = _b64_to_hex(kid_raw); key_hex = _b64_to_hex(key_raw)
            if not (kid_hex and key_hex): continue
            if len(kid_hex) != 32 or len(key_hex) != 32: continue
            if (kid_hex, key_hex) in seen: continue
            seen.add((kid_hex, key_hex))
            out.append({"kid": kid_hex, "key": key_hex})
    return out


def auto_import_har_to_db(har_path, log=print, verbose=True):
    try:
        with open(har_path, "r", encoding="utf-8-sig") as f:
            data = json.load(f)
    except Exception as e:
        if verbose: log(f"⚠️ HAR load: {e}")
        return {"added": 0, "updated": 0, "placeholder": 0, "total": 0}
    entries = data.get("log", {}).get("entries", []) or []
    ext = _load_external_keys()
    added = updated = ph_added = 0
    seen = set()
    for entry in entries:
        res = entry.get("response", {}) or {}
        content = res.get("content", {}) or {}
        body = content.get("text") or ""
        if content.get("encoding") == "base64" and body:
            try: body = base64.b64decode(body).decode("utf-8", errors="replace")
            except Exception: body = ""
        if not body: continue
        if "<MPD" in body or "<mpd" in body:
            for m in re.finditer(r'cenc:default_KID\s*=\s*"([0-9a-fA-F\-]+)"', body):
                kid = m.group(1).replace("-", "").lower()
                if len(kid) == 32 and kid not in ext and kid not in seen:
                    ext[kid] = {"key": "", "name": "HAR placeholder",
                                "added": datetime.now().isoformat(timespec="seconds"),
                                "status": "placeholder"}
                    seen.add(kid); ph_added += 1
        for p in _parse_clearkey_json_body(body):
            kid = p["kid"]; key = p["key"]
            if (kid, key) in seen: continue
            seen.add((kid, key))
            cur = ext.get(kid) or {}
            if not isinstance(cur, dict): cur = {}
            if cur.get("key") == key: continue
            existed = kid in ext
            cur["key"] = key; cur.pop("status", None)
            cur.setdefault("name", "HAR import")
            cur.setdefault("added", datetime.now().isoformat(timespec="seconds"))
            ext[kid] = cur
            if existed: updated += 1
            else: added += 1
    if added or updated or ph_added:
        if _save_external_keys(ext): _invalidate_kid_index()
    return {"added": added, "updated": updated, "placeholder": ph_added,
            "total": added + updated + ph_added}


def auto_import_recent_hars(log=print, max_age_sec=600, verbose=True):
    try:
        files = sorted(glob.glob("dazn_capture_*.har"), key=os.path.getmtime, reverse=True)
    except Exception: return {"files": 0, "added": 0}
    now = time.time(); total = {"files": 0, "added": 0, "updated": 0, "placeholder": 0}
    for fp in files:
        try:
            if (now - os.path.getmtime(fp)) > max_age_sec: break
            stats = auto_import_har_to_db(fp, log=log, verbose=verbose)
            total["files"] += 1
            for k in ("added", "updated", "placeholder"): total[k] += stats.get(k, 0)
        except Exception: pass
    return total


# ==============================================================
# LOGIN / TOKEN
# ==============================================================
def do_login(username, password):
    headers = {'accept': '*/*', 'content-type': 'application/json',
               'origin': 'https://www.dazn.com', 'referer': 'https://www.dazn.com/',
               'user-agent': USER_AGENT}
    json_data = {'Email': username, 'Password': password,
                 'Platform': 'web', 'DeviceId': secrets.token_hex(5)}
    r = requests.post('https://authentication-prod.ar.indazn.com/v5/SignIn',
                      headers=headers, json=json_data, proxies=proxies,
                      impersonate='chrome', timeout=30)
    try: return json.loads(r.content)['AuthToken']['Token']
    except Exception: print('Login fallido'); return None


def get_version():
    headers = {'accept': '*/*', 'origin': 'https://www.dazn.com',
               'referer': 'https://www.dazn.com/', 'user-agent': USER_AGENT}
    try:
        r = requests.get('https://pkg.fe.indazn.com/@dazn/peng-html5-core/live-production/web/it/0/version.json',
                         headers=headers, proxies=proxies, impersonate='chrome', timeout=15)
        return json.loads(r.content)['version']
    except Exception: return VERSION


def get_token():
    global VERSION
    ascii_clear()
    pname, pinfo = get_active_profile()
    if pinfo and pinfo.get("token"):
        tok = pinfo["token"]
        if tok.count(".") == 2:
            _set_token(tok)
            try:
                with open("token.txt", "w", encoding="utf-8") as f:
                    f.write(tok)
            except Exception: pass
            try: VERSION = get_version()
            except Exception: pass
            print(f"✅ Token del perfil '{pname}'")
            return tok
    if os.path.exists("token.txt"):
        try:
            with open("token.txt", "r", encoding="utf-8") as f:
                saved = f.read().strip()
            if saved and saved.count(".") == 2:
                _set_token(saved)
                try: VERSION = get_version()
                except Exception: pass
                print("✅ Token cargado desde token.txt")
                return saved
        except Exception: pass
    print("🔑 Capturando token desde el navegador...")
    input("   Pulsa ENTER para abrir el navegador...")
    tok = capture_and_save_token()
    if tok:
        try: VERSION = get_version()
        except Exception: pass
        return tok
    print("❌ Login fallido."); sys.exit(1)


# ==============================================================
# GUI
# ==============================================================
GUI_BG = "#0d1117"; GUI_BG2 = "#161b22"; GUI_FG = "#c9d1d9"
GUI_ACCENT = "#58a6ff"; GUI_GREEN = "#3fb950"; GUI_RED = "#f85149"
GUI_YELLOW = "#d29922"; GUI_MAGENTA = "#bc8cff"; GUI_CYAN = "#79c0ff"
_ANSI_RE = re.compile(r'\x1b\[[0-9;]*m')


class DaznGUI:
    def __init__(self, root):
        self.root = root; self.tk = tk; self.ttk = ttk
        self.scrolledtext = scrolledtext
        self._build_main()
        self._update_status()

    def _build_main(self):
        tk = self.tk
        self.root.title("DAZN EXTRACTOR v5.4.1 — WARP + AUTO-PUSH")
        self.root.geometry("1240x920")
        self.root.configure(bg=GUI_BG); self.root.minsize(1100, 800)
        header = tk.Frame(self.root, bg=GUI_BG2, height=70)
        header.pack(fill="x", side="top"); header.pack_propagate(False)
        tk.Label(header, text="🎯 DAZN EXTRACTOR", bg=GUI_BG2, fg=GUI_ACCENT,
                 font=("Segoe UI", 20, "bold")).pack(side="left", padx=20, pady=10)
        tk.Label(header, text="v5.4.1 — WARP + AUTO-PUSH + git pull",
                 bg=GUI_BG2, fg=GUI_MAGENTA,
                 font=("Segoe UI", 11, "italic bold")).pack(side="left", padx=5)
        self.status_pill = tk.Label(header, text="⏹ DETENIDO", bg=GUI_BG, fg=GUI_FG,
                                    font=("Consolas", 10, "bold"), padx=12, pady=6)
        self.status_pill.pack(side="right", padx=20)
        self.status_bar = tk.Label(self.root, text="Listo.", bg=GUI_BG2, fg=GUI_FG,
                                   font=("Consolas", 9), anchor="w", padx=10, pady=4)
        self.status_bar.pack(fill="x", side="bottom")
        c = tk.Frame(self.root, bg=GUI_BG); c.pack(fill="x", side="bottom", padx=10, pady=(10, 14))

        def row(label, color):
            r = tk.Frame(c, bg=GUI_BG); r.pack(fill="x", pady=5)
            tk.Label(r, text=label, bg=GUI_BG, fg=color,
                     font=("Segoe UI", 10, "bold"), width=16, anchor="w").pack(side="left")
            return r

        r0 = row("🔑 TOKEN", GUI_YELLOW)
        self._btn(r0, "🔑 Capturar Token", self.act_capture_token, GUI_YELLOW)
        self._btn(r0, "🌐 WARP status", self.act_warp_status, GUI_CYAN)

        r1 = row("📺 CANALES", GUI_GREEN)
        self._btn(r1, "▶ Generar M3U", self.act_generate_channels, GUI_GREEN)
        self._btn(r1, "🗑 Reset", self.act_reset_channels, GUI_RED)

        r2 = row("📅 EVENTOS", GUI_MAGENTA)
        self._btn(r2, "🎬 Generar M3U", self.act_generate_events, GUI_MAGENTA)
        self._btn(r2, "⏳ Pending", self.act_pending, GUI_MAGENTA)

        r3 = row("⏰ SCH. EVENTOS", GUI_ACCENT)
        self._btn(r3, "▶ Iniciar", self.act_start_events, GUI_GREEN)
        self._btn(r3, "⏹ Detener", self.act_stop_events, GUI_RED)

        r4 = row("📡 SCH. CANALES", GUI_CYAN)
        self._btn(r4, "▶ Iniciar", self.act_start_channels, GUI_GREEN)
        self._btn(r4, "⏹ Detener", self.act_stop_channels, GUI_RED)

        r5 = row("🚀 GITHUB", GUI_YELLOW)
        self._btn(r5, "⬆ Push ahora", self.act_git_push, GUI_GREEN)
        self._btn(r5, "📊 Estado", self.act_status, GUI_CYAN)
        self._btn(r5, "🗑 Pending", self.act_clear_pending, GUI_RED)

        r6 = row("⚙️ CONFIG.", GUI_YELLOW)
        self._btn(r6, "🎬 WVD", self.act_wvd_manager, GUI_RED)
        self._btn(r6, "📥 HAR", self.act_import_har, GUI_MAGENTA)
        self._btn(r6, "🚪 Salir", self.act_exit, GUI_RED)

        lf = tk.Frame(self.root, bg=GUI_BG)
        lf.pack(fill="both", expand=True, side="top", padx=10, pady=(10, 0))
        self.log_text = self.scrolledtext.ScrolledText(
            lf, bg="#010409", fg=GUI_FG, font=("Consolas", 10),
            insertbackground=GUI_ACCENT, wrap="word", relief="flat",
            borderwidth=0, padx=10, pady=10)
        self.log_text.pack(fill="both", expand=True)
        self.log_text.configure(state="disabled")
        for name, col in [("info", GUI_FG), ("ok", GUI_GREEN), ("warn", GUI_YELLOW),
                          ("err", GUI_RED), ("accent", GUI_ACCENT), ("magenta", GUI_MAGENTA)]:
            self.log_text.tag_config(name, foreground=col)
        self.root.protocol("WM_DELETE_WINDOW", self.act_exit)

    def _btn(self, parent, text, cmd, color):
        tk = self.tk
        b = tk.Button(parent, text=text, command=cmd, bg=GUI_BG2, fg=color,
                      activebackground=color, activeforeground=GUI_BG,
                      font=("Segoe UI", 11, "bold"), relief="flat", borderwidth=1,
                      highlightthickness=0, padx=12, pady=7, cursor="hand2")
        b.pack(side="left", padx=3)
        b.bind("<Enter>", lambda e: b.configure(bg=color, fg=GUI_BG))
        b.bind("<Leave>", lambda e: b.configure(bg=GUI_BG2, fg=color))

    def log(self, text, tag="info"):
        def _w():
            if not _widget_alive(self.log_text): return
            try:
                self.log_text.configure(state="normal")
                self.log_text.insert("end", text + "\n", tag)
                self.log_text.see("end"); self.log_text.configure(state="disabled")
            except Exception: pass
        try: self.root.after(0, _w)
        except Exception: pass

    def clear_log(self):
        def _c():
            if not _widget_alive(self.log_text): return
            try:
                self.log_text.configure(state="normal")
                self.log_text.delete("1.0", "end")
                self.log_text.configure(state="disabled")
            except Exception: pass
        try: self.root.after(0, _c)
        except Exception: pass

    def run_async(self, fn, *a, **kw):
        def _w():
            try: fn(*a, **kw)
            except Exception as e:
                import traceback
                self.log(f"❌ {e}", "err")
                self.log(traceback.format_exc(), "err")
        threading.Thread(target=_w, daemon=True).start()

    def _update_status(self):
        try:
            parts = []
            if events_scheduler_running: parts.append("⏰ EVENTOS")
            if channels_scheduler_running: parts.append("📡 CANALES")
            st = ck_hunter_stats()
            if _widget_alive(self.status_pill):
                self.status_pill.configure(
                    text=" | ".join(parts) if parts else "⏹ DETENIDO",
                    fg=GUI_GREEN if parts else GUI_RED)
                w = _warp_status() or "?"
                self.status_bar.configure(
                    text=f"🌐 WARP: {w} | CK: {st['total_indexed']} KID | "
                         f"Pending: {len(load_pending_events())} | "
                         f"Push: {'ON' if config.get('github_auto_push') else 'OFF'} | "
                         f"WARP toggle: {'ON' if config.get('warp_auto_toggle') else 'OFF'}")
        except Exception: pass
        try:
            if _widget_alive(self.root):
                self.root.after(3000, self._update_status)
        except Exception: pass

    def act_capture_token(self):
        self.clear_log(); self.log("🔑 Capturando token...", "accent")
        self.run_async(lambda: capture_and_save_token(log=self.log))

    def act_warp_status(self):
        w = _warp_status()
        self.log(f"🌐 WARP: {w or 'desconocido'}", "ok")

    def act_git_push(self):
        self.log("⬆ Forzando push a GitHub...", "accent")
        def _do():
            ok = _github_auto_push()
            self.log(f"{'✅' if ok else '⚠️'} push → {ok}", "ok" if ok else "warn")
        self.run_async(_do)

    def act_clear_pending(self):
        if not messagebox.askyesno("Confirmar", "¿Vaciar pending_events.json?"): return
        save_pending_events([])
        self.log("🗑 Pendientes vaciados", "warn")

    def act_generate_channels(self):
        self.clear_log(); self.log("▶ Generando canales...", "accent")
        self.run_async(self._do_gen_channels)

    def _do_gen_channels(self):
        try: _load_token_safe(do_refresh_if_possible=True)
        except Exception as e: self.log(f"⚠️ {e}", "warn"); return
        s = get_selected_channels_from_config() or get_channels(_get_token())
        _generate_channels_both_variants(selected_channels=s)

    def act_generate_events(self):
        self.clear_log(); self.log("🎬 Generando eventos...", "accent")
        self.run_async(self._do_gen_events)

    def _do_gen_events(self):
        try: _load_token_safe(do_refresh_if_possible=True)
        except Exception as e: self.log(f"⚠️ {e}", "warn"); return
        ev = get_scheduled_events(_get_token(), config.get("events_include_live", True), True)
        if config.get("events_only_today"): ev = filter_events_today(ev)
        if not ev: self.log("⚠️ Sin eventos", "warn"); return
        _generate_events_both_variants(ev, auto_pending=True, retain_cache=True,
                                        use_ck_hunter=config.get("ck_hunter_enabled", True))

    def act_reset_channels(self):
        config["selected_channels"] = []; save_config()
        self.log("✅ Reset", "ok")

    def act_pending(self):
        self.clear_log()
        pend = load_pending_events()
        self.log(f"⏳ {len(pend)} pendientes:", "accent")
        for ev in pend[:30]:
            self.log(f"  · {ev.get('Title', '?')[:80]} ({ev.get('AddedAt', '?')})")

    def act_start_events(self):
        start_events_scheduler(); self.log("✅ Scheduler eventos ON", "ok")

    def act_stop_events(self):
        stop_events_scheduler(); self.log("⏹ Scheduler eventos OFF", "warn")

    def act_start_channels(self):
        start_channels_scheduler(); self.log("✅ Scheduler canales ON", "ok")

    def act_stop_channels(self):
        stop_channels_scheduler(); self.log("⏹ Scheduler canales OFF", "warn")

    def act_wvd_manager(self):
        tk = self.tk
        d = tk.Toplevel(self.root); d.title("WVD"); d.geometry("700x400")
        d.configure(bg=GUI_BG)
        tk.Label(d, text="🎬 WIDEVINE CDM", bg=GUI_BG, fg=GUI_RED,
                 font=("Segoe UI", 14, "bold")).pack(pady=12)
        path = _wvd_path()
        tk.Label(d, text=f"Archivo: {path}\nExiste: {os.path.exists(path)}\n"
                          f"pywidevine: {_pywidevine_available()}",
                 bg=GUI_BG, fg=GUI_FG, font=("Consolas", 10), justify="left").pack(padx=20, pady=10)
        def pick():
            p = filedialog.askopenfilename(title="WVD", filetypes=[("WVD", "*.wvd")])
            if p:
                config["wvd_file"] = p; save_config(); _invalidate_wvd_cache()
                self.log(f"✅ WVD: {p}", "ok"); d.destroy()
        tk.Button(d, text="📂 Elegir WVD", command=pick).pack(pady=10)

    def act_import_har(self):
        p = filedialog.askopenfilename(title="HAR", filetypes=[("HAR", "*.har")])
        if not p: return
        self.log(f"📥 Importando {os.path.basename(p)}...", "accent")
        def _do():
            stats = auto_import_har_to_db(p, log=self.log)
            self.log(f"✅ Import: +{stats['added']} claves, +{stats['placeholder']} placeholders", "ok")
        self.run_async(_do)

    def act_status(self):
        self.clear_log()
        st = ck_hunter_stats()
        self.log("=" * 55, "accent")
        self.log("  ESTADO", "accent")
        self.log("=" * 55, "accent")
        self.log(f"🌐 WARP: {_warp_status() or '?'}", "accent")
        self.log(f"🎯 CK Hunter: {st['total_indexed']} KID", "accent")
        self.log(f"⏳ Pendientes: {len(load_pending_events())}", "accent")
        self.log(f"🚀 Auto-push: {'ON' if config.get('github_auto_push') else 'OFF'}", "accent")
        self.log(f"🌐 WARP toggle: {'ON' if config.get('warp_auto_toggle') else 'OFF'}", "accent")

    def act_exit(self):
        if events_scheduler_running: stop_events_scheduler()
        if channels_scheduler_running: stop_channels_scheduler()
        try: self.root.destroy()
        except Exception: pass


class _GuiStdout:
    def __init__(self, gui): self.gui = gui; self.buffer = ""
    def write(self, text):
        if not text: return
        text = _ANSI_RE.sub("", text); self.buffer += text
        while "\n" in self.buffer:
            line, self.buffer = self.buffer.split("\n", 1)
            if line.strip() == "": self.gui.log(""); continue
            tag = "info"
            if "❌" in line: tag = "err"
            elif "⚠️" in line: tag = "warn"
            elif "✅" in line: tag = "ok"
            elif "🌐" in line: tag = "accent"
            self.gui.log(line, tag)
    def flush(self): pass


def main_gui():
    global _gui_instance, pin
    try: get_token()
    except Exception as e:
        print(f"❌ {e}"); sys.exit(1)
    pin = config.get('pin', '')
    try: _release_all_locks()
    except Exception: pass
    root = tk.Tk()
    _gui_instance = DaznGUI(root)
    sys.stdout = _GuiStdout(_gui_instance)
    try: start_events_scheduler()
    except Exception as e: _gui_instance.log(f"⚠️ {e}", "warn")
    try: start_channels_scheduler()
    except Exception as e: _gui_instance.log(f"⚠️ {e}", "warn")
    if config.get("pending_watcher_active", True):
        try: start_pending_watcher()
        except Exception as e: _gui_instance.log(f"⚠️ {e}", "warn")
    _gui_instance.log("=" * 55, "accent")
    _gui_instance.log("  🎯 DAZN EXTRACTOR v5.4.1", "accent")
    _gui_instance.log(f"  WARP: {config.get('warp_auto_toggle')} | "
                       f"Push GitHub: {config.get('github_auto_push')}", "accent")
    _gui_instance.log("=" * 55, "accent")
    try: root.mainloop()
    finally: sys.stdout = sys.__stdout__


if __name__ == "__main__":
    import signal
    signal.signal(signal.SIGINT, signal_handler)
    main_gui()    