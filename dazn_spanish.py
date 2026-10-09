#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DAZN EXTRACTOR — SUPERFUSION v2 ATOMIC
(ClearKey + CK HUNTER + KEY HUNTER + WVD HUNTER + PERFILES + HAR→KID + HAR AUTO + GRACE + KID/KEY MANAGER)
[v5.3.8-ES] Traducción al español · Eliminados Dropbox y Telegram · Añadido soporte Edge (Playwright)
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

VERSION = "5.3.8-ES"
proxies = None
token = None
pin = None
_token_lock = threading.Lock()

PERMANENT_ERROR_CODES = {10803}
PENDING_ERROR_CODES = {10000}

def _widget_alive(w):
    try:
        return w is not None and bool(w.winfo_exists())
    except Exception:
        return False

def _safe_after(widget, ms, func):
    if not _widget_alive(widget):
        return None
    try:
        return widget.after(ms, func)
    except Exception:
        return None

def _safe_after_cancel(widget, aid):
    if aid is None:
        return
    try:
        widget.after_cancel(aid)
    except Exception:
        pass

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
    "NFL NETWORK":       "205",
    "DAZN 1":            "206",
    "MILAN TV":          "207",
    "MLB":               "208",
    "EUROSPORT 1 (🇩🇪)": "209",
    "EUROSPORT 2 (🇩🇪)": "210",
    "EUROSPORT 1":       "211",
    "EUROSPORT 2":       "212",
    "INTER TV":          "215",
    "REAL TIME":         "216",
    "REDBULL TV":        "217",
    "RALLY TV":          "220",
    "RADIO TV RDS":      "223",
    "RADIO TV SERIE A":  "223",
    "DISCOVERY":         "225",
    "EUROSPORT 3":       "231",
    "EUROSPORT 4":       "232",
    "EUROSPORT 5":       "233",
    "EUROSPORT 6":       "239",
    "NOVE":              "241",
    "DMAX":              "242",
    "UNBEATEN":          "522",
    "FOCUS SERIE A":     "226",
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

BLACKLIST_CHANNELS = {
    "NEWS SERIE A",
    "NEWS CAMPIONATO",
    "SERIE A NEWS",
}

def _is_blacklisted(title):
    if not title:
        return False
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
            if not isinstance(d, dict):
                return {}
            if "linear" in d or "events" in d:
                flat = {}
                for kid, info in (d.get("linear") or {}).items():
                    if isinstance(info, dict):
                        info.setdefault("_category", "linear")
                        flat[kid] = info
                for kid, info in (d.get("events") or {}).items():
                    if isinstance(info, dict):
                        info.setdefault("_category", "events")
                        flat[kid] = info
                return flat
            return {k: v for k, v in d.items()
                    if not k.startswith("_") and isinstance(v, dict)}
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
                    existing = {
                        "_meta": cur.get("_meta", {}),
                        "linear": dict(cur.get("linear") or {}),
                        "events": dict(cur.get("events") or {}),
                    }
                elif isinstance(cur, dict):
                    for kid, info in cur.items():
                        if kid.startswith("_") or not isinstance(info, dict):
                            continue
                        if info.get("country") or info.get("channels"):
                            existing["linear"][kid] = info
                        else:
                            existing["events"][kid] = info
            except Exception:
                pass

        for kid, info in flat_data.items():
            if kid.startswith("_") or not isinstance(info, dict):
                continue
            if not info.get("key") and info.get("status") != "placeholder":
                continue
            info = {k: v for k, v in info.items() if k != "_category"}
            is_linear = bool(info.get("country") or info.get("channels"))
            if is_linear:
                existing["linear"][kid] = info
                existing["events"].pop(kid, None)
            else:
                existing["events"][kid] = info
                existing["linear"].pop(kid, None)

        existing["_meta"] = {
            "version": 2,
            "updated": datetime.now().isoformat(timespec="seconds"),
            "count_linear": len(existing["linear"]),
            "count_events": len(existing["events"]),
            "note": "Las claves en STATIC_CLEARKEY_KEYS del código NO se duplican aquí",
        }

        with open(EXTERNAL_KEYS_FILE, "w", encoding="utf-8") as f:
            json.dump(existing, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        print(f"⚠️ external_keys save: {e}")
        return False

def _build_kid_key_index():
    idx = {}
    for name, (kid, key) in STATIC_CLEARKEY_KEYS.items():
        idx[kid.lower().replace("-", "")] = (
            key.lower().replace("-", ""), f"static:{name}")
    for kid, info in _load_external_keys().items():
        k = kid.lower().replace("-", "")
        if isinstance(info, dict) and info.get("key"):
            cat = info.get("_category", "ext")
            name = info.get("name", "?")
            idx[k] = (info["key"].lower().replace("-", ""),
                      f"{cat}:{name}")
    return idx

def _get_kid_index():
    global _KID_KEY_INDEX, _KID_KEY_INDEX_MTIME
    with _KID_KEY_INDEX_LOCK:
        try:
            cur_mtime = os.path.getmtime(EXTERNAL_KEYS_FILE) \
                if os.path.exists(EXTERNAL_KEYS_FILE) else 0
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
        headers = {
            "User-Agent": USER_AGENT,
            "Origin": "https://www.dazn.com",
            "Referer": "https://www.dazn.com/",
            "Accept": "*/*",
        }
        if cdn_name and cdn_token:
            headers[cdn_name] = cdn_token
        r = requests.get(mpd_url, headers=headers, proxies=proxies,
                         impersonate="chrome", timeout=timeout)
        if r.status_code != 200:
            return None
        text = r.text
        m = re.search(r'cenc:default_KID\s*=\s*"([0-9a-fA-F\-]+)"', text)
        if not m:
            m = re.search(r'default_KID\s*=\s*"([0-9a-fA-F\-]+)"', text)
        if m:
            return m.group(1).replace("-", "").lower()
        mpssh = re.search(r'<cenc:pssh[^>]*>([A-Za-z0-9+/=\s]+)</cenc:pssh>', text)
        if mpssh:
            try:
                raw = base64.b64decode(mpssh.group(1).strip())
                for offset in (12, 20, 32):
                    if len(raw) >= offset + 16:
                        cand = raw[offset:offset + 16]
                        if cand.count(0) < 16:
                            return cand.hex().lower()
            except Exception:
                pass
        return None
    except Exception:
        return None

def ck_hunter_lookup(kid_hex):
    if not kid_hex:
        return None, None
    idx = _get_kid_index()
    hit = idx.get(kid_hex.lower().replace("-", ""))
    if hit:
        return hit
    return None, None

def ck_hunter_register(kid_hex, key_hex, name="", country=None, channels=None):
    if not kid_hex or not key_hex:
        return False
    kid_hex = kid_hex.lower().replace("-", "")
    key_hex = key_hex.lower().replace("-", "")
    if len(kid_hex) != 32 or len(key_hex) != 32:
        return False
    for n, (k, v) in STATIC_CLEARKEY_KEYS.items():
        if k.lower() == kid_hex:
            return True
    flat = _load_external_keys()
    if kid_hex in flat and isinstance(flat[kid_hex], dict):
        if flat[kid_hex].get("key") == key_hex:
            return True
    entry = {"key": key_hex, "name": (name or "unknown")[:120]}
    if country:
        entry["country"] = country
    if channels:
        entry["channels"] = list(channels)
    if not country and not channels:
        entry["added"] = datetime.now().isoformat(timespec="seconds")
    flat[kid_hex] = entry
    ok = _save_external_keys(flat)
    if ok:
        _invalidate_kid_index()
    return ok

def ck_hunter_stats():
    static_count = len(STATIC_CLEARKEY_KEYS)
    ext = _load_external_keys()
    by_cat = {}
    by_country = {}
    for kid, info in ext.items():
        cat = info.get("_category", "?")
        by_cat[cat] = by_cat.get(cat, 0) + 1
        c = info.get("country")
        if c:
            by_country[c] = by_country.get(c, 0) + 1
    return {
        "static": static_count,
        "external": len(ext),
        "total_indexed": len(_get_kid_index()),
        "by_cat": by_cat,
        "by_country": by_country,
    }

def ck_hunter_attempt(manifest_url, title="", token=None,
                      cdn_name=None, cdn_token=None, verbose=True):
    if not manifest_url:
        return None
    kid = _extract_kid_from_mpd(manifest_url, token, cdn_name, cdn_token)
    if not kid:
        if verbose:
            print("❌ KID no presente en el manifest")
        return None
    key, src = ck_hunter_lookup(kid)
    if not key:
        if verbose:
            print(f"❌ KID {kid[:12]}... desconocido")
        return None
    if verbose:
        print(f"✅ coincidencia ({src})")
    return {"kid": kid, "key": key, "source": src}

def key_hunter_request_license(kid_hex, la_url, token,
                                cdn_name=None, cdn_token=None,
                                verbose=True):
    if not kid_hex or not la_url:
        return None
    try:
        kid_bytes = bytes.fromhex(kid_hex.replace("-", ""))
        kid_b64 = base64.urlsafe_b64encode(kid_bytes).decode().rstrip("=")
    except Exception:
        if verbose:
            print("   ❌ KID no convertible a base64url")
        return None
    payload = {"kids": [kid_b64], "type": "temporary"}
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json, */*",
        "Origin": "https://www.dazn.com",
        "Referer": "https://www.dazn.com/",
        "User-Agent": USER_AGENT,
        "Authorization": "Bearer " + token,
        "x-correlation-id": str(uuid.uuid4()),
    }
    if cdn_name and cdn_token:
        headers[cdn_name] = cdn_token
    if verbose:
        print(f"   🔐 POST licencia a {la_url[:70]}...")
    try:
        r = requests.post(la_url, json=payload, headers=headers,
                          proxies=proxies, impersonate="chrome", timeout=20)
    except Exception as e:
        if verbose:
            print(f"   ❌ Red: {e}")
        return None
    if r.status_code != 200:
        if verbose:
            print(f"   ❌ HTTP {r.status_code}: {r.text[:200]}")
        return None
    try:
        data = r.json()
    except Exception:
        try:
            text = r.content.decode("latin-1", errors="replace")
            for m in re.finditer(r'"k"\s*:\s*"([A-Za-z0-9_\-]+)"', text):
                key_hex = _b64_to_hex(m.group(1))
                if key_hex and len(key_hex) == 32:
                    if verbose:
                        print("   ✅ KEY encontrada (fallback binario)")
                    return key_hex
        except Exception:
            pass
        if verbose:
            print(f"   ❌ No-JSON: {r.content[:80]!r}")
        return None
    keys = data.get("keys") if isinstance(data, dict) else None
    if not isinstance(keys, list):
        if verbose:
            print("   ❌ Sin campo 'keys'")
        return None
    for k in keys:
        k_raw = k.get("k") or k.get("K") or k.get("key")
        if not k_raw:
            continue
        key_hex = _b64_to_hex(k_raw)
        if key_hex and len(key_hex) == 32:
            if verbose:
                print("   ✅ KEY encontrada vía license request!")
            return key_hex
    if verbose:
        print("   ❌ Ninguna KEY válida en la respuesta")
    return None

# ==============================================================
# 🎬 WVD / WIDEVINE HUNTER  [estilo SuperMike v5.3.8-ES]
# ==============================================================
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
        if verbose:
            print("⚠️ pywidevine no instalado → pip install pywidevine")
        return None
    wvd_path = _wvd_path()
    if not os.path.exists(wvd_path):
        if verbose:
            print(f"⚠️ WVD no encontrado: {wvd_path}")
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
            if verbose:
                lvl = getattr(device, "security_level", "?")
                print(f"✅ WVD cargado: {wvd_path} (L{lvl})")
            return cdm
        except Exception as e:
            if verbose:
                print(f"❌ Error cargando WVD: {e}")
            return None

def _invalidate_wvd_cache():
    global _wvd_cdm, _wvd_loaded_path
    with _wvd_lock:
        _wvd_cdm = None
        _wvd_loaded_path = None

def _extract_pssh_from_mpd(mpd_url, token=None, cdn_name=None,
                            cdn_token=None, timeout=15):
    try:
        headers = {
            "User-Agent": USER_AGENT,
            "Origin": "https://www.dazn.com",
            "Referer": "https://www.dazn.com/",
            "Accept": "*/*",
        }
        if cdn_name and cdn_token:
            headers[cdn_name] = cdn_token
        r = requests.get(mpd_url, headers=headers, proxies=proxies,
                         impersonate="chrome", timeout=timeout)
        if r.status_code != 200:
            return None
        text = r.text
        m = re.search(
            r'<ContentProtection[^>]*schemeIdUri=["\']urn:uuid:'
            + WIDEVINE_SYSTEM_ID +
            r'["\'][^>]*>.*?<cenc:pssh[^>]*>([A-Za-z0-9+/=\s]+)</cenc:pssh>',
            text, re.DOTALL | re.IGNORECASE)
        if m:
            return m.group(1).strip()
        mpssh = re.search(r'<cenc:pssh[^>]*>([A-Za-z0-9+/=\s]+)</cenc:pssh>', text)
        if mpssh:
            return mpssh.group(1).strip()
        mpro = re.search(r'<mspr:pro[^>]*>([A-Za-z0-9+/=\s]+)</mspr:pro>', text)
        if mpro:
            return mpro.group(1).strip()
        return None
    except Exception:
        return None

def widevine_extract_keys(pssh_b64, la_url, token,
                           cdn_name=None, cdn_token=None,
                           verbose=True):
    """
    [v5.3.8-ES] Réplica EXACTA de do_cdm() del DAZN Extractor SuperMike.
    Headers minimalistas en minúsculas + impersonate Chrome estándar.
    """
    dbg_f = open("wvd_debug.log", "a", encoding="utf-8")
    def _d(msg):
        ts = datetime.now().strftime("%H:%M:%S")
        dbg_f.write(f"[{ts}] {msg}\n")
        dbg_f.flush()
        if verbose:
            print(f"   {msg}")

    _d("══════ WVD EXTRACT START (SuperMike do_cdm style) ══════")
    _d(f"PSSH len={len(pssh_b64) if pssh_b64 else 0}")
    _d(f"LaUrl: {la_url[:100] if la_url else 'None'}")
    _d(f"Token: {'presente' if token else 'FALTANTE'} ({len(token) if token else 0} char)")

    if not pssh_b64 or not la_url:
        _d("❌ pssh_b64 o la_url faltante")
        dbg_f.close(); return None

    try:
        from pywidevine.cdm import Cdm
        from pywidevine.device import Device
        from pywidevine.pssh import PSSH
    except ImportError as e:
        _d(f"❌ pywidevine import: {e}")
        dbg_f.close(); return None

    try:
        _pssh_clean = (pssh_b64 or "").strip()
        if isinstance(_pssh_clean, str):
            _pad = (-len(_pssh_clean)) % 4
            if _pad:
                _pssh_clean += "=" * _pad
            try:
                _pssh_bytes = base64.b64decode(_pssh_clean, validate=False)
                pssh_obj = PSSH(_pssh_bytes)
                _d(f"✅ PSSH init OK (bytes, {len(_pssh_bytes)}B)")
            except Exception:
                pssh_obj = PSSH(pssh_b64)
                _d(f"✅ PSSH init OK (str fallback)")
        else:
            pssh_obj = PSSH(_pssh_clean)
            _d(f"✅ PSSH init OK (direct)")
    except Exception as e:
        _d(f"❌ PSSH init: {type(e).__name__}: {e}")
        dbg_f.close(); return None

    wvd_path = config.get("wvd_file", WVD_FILE_DEFAULT)
    try:
        device = Device.load(wvd_path)
        cdm = Cdm.from_device(device)
        sid = cdm.open()
        challenge = cdm.get_license_challenge(sid, pssh_obj)
        _d(f"✅ CDM OK — challenge {len(challenge)} byte")
    except Exception as e:
        _d(f"❌ CDM setup: {type(e).__name__}: {e}")
        dbg_f.close(); return None

    headers = {
        'authorization': 'Bearer ' + token,
        'content-type': 'application/octet-stream',
        'origin': 'https://www.dazn.com',
        'referer': 'https://www.dazn.com/',
        'user-agent': USER_AGENT,
        'x-correlation-id': str(uuid.uuid4()),
        'sec-ch-ua': '"Not:A-Brand";v="99", "Google Chrome";v="142", "Chromium";v="142"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"Windows"',
        'sec-fetch-dest': 'empty',
        'sec-fetch-mode': 'cors',
        'sec-fetch-site': 'cross-site',
    }
    _d(f"Headers enviados: {sorted(headers.keys())}")

    try:
        r = requests.post(la_url, headers=headers, data=challenge,
                          proxies=proxies, impersonate="chrome", timeout=30)
    except Exception as e:
        _d(f"❌ POST EXCEPCIÓN: {type(e).__name__}: {e}")
        try: cdm.close(sid)
        except: pass
        dbg_f.close(); return None

    _d(f"📥 RESPUESTA: status={r.status_code}")
    _d(f"   content-type: {r.headers.get('content-type', '?')}")
    _d(f"   content-length: {len(r.content)} byte")
    if len(r.content) > 0 and r.status_code != 200:
        try:
            _d(f"   primeros 200 char: {r.content[:200].decode('utf-8', errors='replace')!r}")
        except Exception:
            pass

    if r.status_code != 200:
        _d(f"❌ HTTP {r.status_code} — return None")
        try: cdm.close(sid)
        except: pass
        dbg_f.close(); return None

    try:
        cdm.parse_license(sid, r.content)
        _d("✅ parse_license OK")
    except Exception as e:
        _d(f"❌ parse_license FAILED: {e}")
        try: cdm.close(sid)
        except: pass
        dbg_f.close(); return None

    keys = []
    try:
        all_k = cdm.get_keys(sid)
        _d(f"get_keys → {len(all_k)} claves totales")
        for k in all_k:
            kid_h = k.kid.hex() if isinstance(k.kid, bytes) else str(k.kid)
            if k.type != 'SIGNING':
                key_h = k.key.hex() if isinstance(k.key, bytes) else str(k.key)
                keys.append({"kid": kid_h, "key": key_h, "type": k.type})
                _d(f"   ✅ {k.type}: {kid_h} : {key_h}")
            else:
                _d(f"   • {k.type}: {kid_h} (skip)")
    except Exception as e:
        _d(f"❌ get_keys FAILED: {e}")
    finally:
        try: cdm.close(sid)
        except: pass

    _d(f"🏁 RETURN: {len(keys)} CONTENT keys")
    _d("══════ END ══════\n")
    dbg_f.close()
    return keys or None

def widevine_attempt(manifest_url, la_url, title="",
                      token=None, cdn_name=None, cdn_token=None,
                      verbose=True):
    if not manifest_url or not la_url:
        return None
    pssh = _extract_pssh_from_mpd(
        manifest_url, token, cdn_name=cdn_name, cdn_token=cdn_token)
    if not pssh:
        if verbose:
            print("   ❌ PSSH Widevine no presente en el manifest")
        return None
    keys = widevine_extract_keys(
        pssh, la_url, token,
        cdn_name=cdn_name, cdn_token=cdn_token, verbose=verbose)
    if not keys:
        return None
    primary = None
    for k in keys:
        try:
            ck_hunter_register(k["kid"], k["key"], title or "wvd")
        except Exception:
            pass
        if primary is None:
            primary = k
    if not primary:
        return None
    return {
        "kid": primary["kid"],
        "key": primary["key"],
        "source": "wvd",
        "keys": keys,
        "pssh": pssh,
    }

# ==============================================================
# 🩹 AUTO-HEALING
# ==============================================================
_deprecated_lock = threading.Lock()

def _load_deprecated_statics():
    with _deprecated_lock:
        try:
            if os.path.exists(DEPRECATED_STATICS_FILE):
                with open(DEPRECATED_STATICS_FILE, "r", encoding="utf-8") as f:
                    d = json.load(f)
                if isinstance(d, dict):
                    return d.get("deprecated", {}) if "deprecated" in d else d
        except Exception:
            pass
        return {}

def _save_deprecated_statics(data):
    with _deprecated_lock:
        try:
            with open(DEPRECATED_STATICS_FILE, "w", encoding="utf-8") as f:
                json.dump({
                    "_meta": {
                        "version": 1,
                        "updated": datetime.now().isoformat(timespec="seconds"),
                        "count": len(data),
                    },
                    "deprecated": data,
                }, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            print(f"⚠️ deprecated_statics save: {e}")
            return False

def _deprecate_static_for_title(title, old_kid, new_kid, reason="KID mismatch"):
    if not title:
        return False
    key = re.sub(r"\s+", " ", str(title).replace("\u00a0", " ")).strip().upper()
    dep = _load_deprecated_statics()
    dep[key] = {
        "old_kid": (old_kid or "").lower().replace("-", ""),
        "new_kid": (new_kid or "").lower().replace("-", ""),
        "reason": reason,
        "at": datetime.now().isoformat(timespec="seconds"),
    }
    return _save_deprecated_statics(dep)

def _restore_static_for_title(title):
    key = re.sub(r"\s+", " ", str(title).replace("\u00a0", " ")).strip().upper()
    dep = _load_deprecated_statics()
    if key in dep:
        del dep[key]
        _save_deprecated_statics(dep)
        return True
    return False

# ==============================================================
# 🔬 ANÁLISIS HAR
# ==============================================================
def _har_extract_all_mpds(har_path):
    results = []
    seen_kids = set()
    try:
        with open(har_path, "r", encoding="utf-8-sig") as f:
            data = json.load(f)
    except Exception as e:
        print(f"⚠️ HAR load: {e}")
        return []
    entries = data.get("log", {}).get("entries", []) or []

    def _extract_kid_from_text(text):
        if not text:
            return None
        m = re.search(r'cenc:default_KID\s*=\s*"([0-9a-fA-F\-]+)"', text)
        if not m:
            m = re.search(r'default_KID\s*=\s*"([0-9a-fA-F\-]+)"', text)
        if m:
            return m.group(1).replace("-", "").lower()
        mpssh = re.search(r'<cenc:pssh[^>]*>([A-Za-z0-9+/=\s]+)</cenc:pssh>', text)
        if mpssh:
            try:
                raw = base64.b64decode(mpssh.group(1).strip())
                for offset in (12, 20, 32):
                    if len(raw) >= offset + 16:
                        cand = raw[offset:offset + 16]
                        if cand.count(0) < 16:
                            return cand.hex().lower()
            except Exception:
                pass
        return None

    for entry in entries:
        req = entry.get("request", {})
        res = entry.get("response", {})
        url = req.get("url", "") or ""
        method = req.get("method", "GET")
        status = res.get("status", 0)
        req_headers = req.get("headers", []) or []
        hdrs = {}
        for h in req_headers:
            n = h.get("name", "").lower()
            v = h.get("value", "")
            if n:
                hdrs[n] = v
        content = res.get("content", {}) or {}
        body = content.get("text") or ""
        if content.get("encoding") == "base64" and body:
            try:
                body = base64.b64decode(body).decode("utf-8", errors="replace")
            except Exception:
                body = ""
        if ".mpd" in url.lower():
            kid = _extract_kid_from_text(body) if body else None
            if kid and kid not in seen_kids:
                seen_kids.add(kid)
                results.append({
                    "url": url, "method": method, "status": status,
                    "kid": kid, "type": "mpd-url",
                    "body_snippet": body[:2000], "headers": hdrs,
                })
            elif not kid and url:
                results.append({
                    "url": url, "method": method, "status": status,
                    "kid": None, "type": "mpd-url-nokid",
                    "body_snippet": body[:2000], "headers": hdrs,
                })
            continue
        if body and ("<MPD" in body or "<mpd" in body) and "cenc:" in body:
            kid = _extract_kid_from_text(body)
            if kid and kid not in seen_kids:
                seen_kids.add(kid)
                results.append({
                    "url": url, "method": method, "status": status,
                    "kid": kid, "type": "mpd-body",
                    "body_snippet": body[:2000], "headers": hdrs,
                })
    return results

def _b64_to_hex(s):
    if not s or not isinstance(s, str):
        return None
    try:
        t = s.strip().replace("-", "+").replace("_", "/")
        pad = (-len(t)) % 4
        t += "=" * pad
        raw = base64.b64decode(t)
        return raw.hex().lower()
    except Exception:
        return None

def _parse_clearkey_json_body(text):
    out = []
    if not text or not isinstance(text, str):
        return out
    candidates = []
    candidates.append(text)
    m = re.search(r'\{[^{}]*"keys"\s*:\s*\[.*?\][^{}]*\}', text, re.DOTALL)
    if m:
        candidates.append(m.group(0))
    seen = set()
    for cand in candidates:
        try:
            obj = json.loads(cand)
        except Exception:
            continue
        keys = obj.get("keys") if isinstance(obj, dict) else None
        if not isinstance(keys, list):
            continue
        for k in keys:
            if not isinstance(k, dict):
                continue
            kid_raw = k.get("kid") or k.get("KID")
            key_raw = k.get("k") or k.get("K") or k.get("key") or k.get("KEY")
            if not kid_raw or not key_raw:
                continue
            kid_hex = _b64_to_hex(kid_raw)
            key_hex = _b64_to_hex(key_raw)
            if not (kid_hex and key_hex):
                continue
            if len(kid_hex) != 32 or len(key_hex) != 32:
                continue
            if (kid_hex, key_hex) in seen:
                continue
            seen.add((kid_hex, key_hex))
            out.append({"kid": kid_hex, "key": key_hex})
    return out

def _har_extract_license_keys(har_path):
    results = []
    seen = set()
    try:
        with open(har_path, "r", encoding="utf-8-sig") as f:
            data = json.load(f)
    except Exception as e:
        print(f"⚠️ HAR license load: {e}")
        return []
    entries = data.get("log", {}).get("entries", []) or []
    for entry in entries:
        req = entry.get("request", {}) or {}
        res = entry.get("response", {}) or {}
        url = req.get("url", "") or ""
        method = (req.get("method", "GET") or "GET").upper()
        status = res.get("status", 0)
        content = res.get("content", {}) or {}
        body = content.get("text") or ""
        if content.get("encoding") == "base64" and body:
            try:
                body = base64.b64decode(body).decode("utf-8", errors="replace")
            except Exception:
                body = ""
        if not body:
            continue
        url_l = url.lower()
        is_license_url = any(w in url_l for w in
                             ("license", "clearkey", "widevine", "drm", "playback", "key"))
        has_clearkey_shape = ('"kty"' in body or '"keys"' in body) and '"kid"' in body.lower()
        if not is_license_url and not has_clearkey_shape:
            continue
        if "<MPD" in body or "<mpd" in body or "<html" in body.lower():
            continue
        pairs = _parse_clearkey_json_body(body)
        for p in pairs:
            t = (p["kid"], p["key"])
            if t in seen:
                continue
            seen.add(t)
            results.append({
                "url": url, "method": method, "status": status,
                "kid": p["kid"], "key": p["key"],
                "type": "license-clearkey",
            })
    return results

def _har_analyze_vs_db(har_path):
    mpds = _har_extract_all_mpds(har_path)
    license_keys = _har_extract_license_keys(har_path)
    idx = _get_kid_index()
    in_db = []
    static = []
    new = []
    no_kid = []
    license_known = []
    license_new = []
    license_kids = set()
    for lk in license_keys:
        kid = lk["kid"]
        license_kids.add(kid)
        static_hit = None
        for n, (sk, sv) in STATIC_CLEARKEY_KEYS.items():
            if sk.lower().replace("-", "") == kid:
                static_hit = n
                break
        if static_hit:
            license_known.append({**lk, "source": f"static:{static_hit}"})
            continue
        hit = idx.get(kid)
        if hit:
            license_known.append({**lk, "source": hit[1]})
        else:
            license_new.append(lk)
    for m in mpds:
        kid = m.get("kid")
        url = m.get("url", "")
        if not kid:
            no_kid.append(m)
            continue
        if kid in license_kids:
            continue
        hit = idx.get(kid.lower())
        if not hit:
            new.append(m)
            continue
        key, src = hit
        entry = {
            "kid": kid, "key": key, "source": src,
            "url": url, "status": m.get("status"),
        }
        if src.startswith("static:"):
            static.append(entry)
        else:
            in_db.append(entry)
    return {
        "total_mpds": len(mpds),
        "kids_found": len([m for m in mpds if m.get("kid")]),
        "total_license_keys": len(license_keys),
        "in_db": in_db,
        "static": static,
        "new": new,
        "no_kid": no_kid,
        "license_new": license_new,
        "license_known": license_known,
    }

def ck_hunter_add_placeholders(kid_list, default_name="HAR placeholder"):
    if not kid_list:
        return 0, 0
    flat = _load_external_keys()
    added = 0
    skipped = 0
    for item in kid_list:
        kid = (item.get("kid") if isinstance(item, dict) else str(item)).lower().replace("-", "")
        if not kid or len(kid) != 32:
            skipped += 1
            continue
        if any(k.lower() == kid for k, _ in STATIC_CLEARKEY_KEYS.values()):
            skipped += 1
            continue
        if kid in flat:
            skipped += 1
            continue
        name_val = (item.get("name") if isinstance(item, dict) else default_name) or default_name
        flat[kid] = {
            "key": "",
            "name": name_val[:120],
            "added": datetime.now().isoformat(timespec="seconds"),
            "status": "placeholder",
        }
        added += 1
    if added:
        _save_external_keys(flat)
        _invalidate_kid_index()
    return added, skipped

def import_external_json(path, log=print):
    with open(path, "r", encoding="utf-8-sig") as f:
        incoming = json.load(f)
    if not isinstance(incoming, dict):
        raise ValueError("El archivo no contiene un objeto JSON válido")
    flat_in = {}
    if "linear" in incoming or "events" in incoming:
        for kid, info in (incoming.get("linear") or {}).items():
            if isinstance(info, dict):
                d = dict(info)
                d.setdefault("country", d.get("country") or "?")
                flat_in[kid] = d
        for kid, info in (incoming.get("events") or {}).items():
            if isinstance(info, dict):
                flat_in[kid] = dict(info)
    else:
        for kid, info in incoming.items():
            if kid.startswith("_") or not isinstance(info, dict):
                continue
            flat_in[kid] = dict(info)
    if not flat_in:
        return {"total": 0, "added": 0, "updated": 0,
                "placeholder": 0, "already": 0, "static_skip": 0, "invalid": 0}
    static_kids = {sk.lower().replace("-", "") for sk, _ in STATIC_CLEARKEY_KEYS.values()}
    current = _load_external_keys()
    current_lower = {k.lower().replace("-", ""): k for k in current}
    added_c = updated_c = added_ph = already = skipped_static = invalid = 0
    for kid, info in flat_in.items():
        k = kid.lower().replace("-", "")
        if len(k) != 32 or any(c not in "0123456789abcdef" for c in k):
            invalid += 1
            continue
        if k in static_kids:
            skipped_static += 1
            continue
        kv = (info.get("key") or "").lower().replace("-", "")
        if kv and (len(kv) != 32 or any(c not in "0123456789abcdef" for c in kv)):
            invalid += 1
            continue
        existing = current.get(k) or {}
        if not isinstance(existing, dict):
            existing = {}
        if kv and len(kv) == 32:
            if not existing.get("key"):
                existing["key"] = kv
                existing.pop("status", None)
                added_c += 1
            elif existing.get("key") != kv:
                existing["key"] = kv
                existing.pop("status", None)
                updated_c += 1
            else:
                already += 1
        else:
            if not existing.get("key"):
                if k in current:
                    already += 1
                else:
                    existing.setdefault("status", "placeholder")
                    added_ph += 1
            else:
                already += 1
        for f in ("name", "country", "channels", "source",
                  "asset_id", "type", "start"):
            if info.get(f) is not None and not existing.get(f):
                existing[f] = info[f]
        if not existing.get("name"):
            existing["name"] = info.get("name") or "import"
        existing.setdefault("added", datetime.now().isoformat(timespec="seconds"))
        current[k] = existing
    if _save_external_keys(current):
        _invalidate_kid_index()
    return {
        "total": len(flat_in),
        "added": added_c,
        "updated": updated_c,
        "placeholder": added_ph,
        "already": already,
        "static_skip": skipped_static,
        "invalid": invalid,
    }

profiles_lock = threading.Lock()

def _load_profiles():
    try:
        if os.path.exists(PROFILES_FILE):
            with open(PROFILES_FILE, "r", encoding="utf-8") as f:
                d = json.load(f)
                if isinstance(d, dict) and "profiles" in d:
                    return d
    except Exception:
        pass
    return {"active": "", "profiles": {}}

def _save_profiles(data):
    try:
        with open(PROFILES_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"⚠️ Error guardando profiles.json: {e}")
        return False

def list_profiles():
    with profiles_lock:
        data = _load_profiles()
    active = data.get("active", "")
    out = []
    for name, info in (data.get("profiles") or {}).items():
        tok = info.get("token", "") or ""
        out.append({
            "name": name,
            "label": info.get("label", name),
            "country": info.get("country", "?"),
            "token_short": (tok[:18] + "..." + tok[-8:]) if len(tok) > 30 else (tok or "—"),
            "created": info.get("created", "?"),
            "updated": info.get("updated", ""),
            "active": (name == active),
        })
    out.sort(key=lambda x: (not x["active"], x["name"]))
    return out

def add_profile(name, token=None, label=None, country=None, set_active=False):
    if not name or not str(name).strip():
        return False, "Nombre vacío"
    name = str(name).strip().lower().replace(" ", "_")
    if token is None:
        try:
            with open("token.txt", "r", encoding="utf-8") as f:
                token = f.read().strip()
        except Exception:
            return False, "No hay token en token.txt para importar"
    if not token or token.count(".") != 2:
        return False, "Token no válido (formato JWT incorrecto)"
    if country is None:
        try:
            decoded = jwt.decode(token, options={"verify_signature": False})
            country = decoded.get("contentCountry", "?")
        except Exception:
            country = "?"
    with profiles_lock:
        data = _load_profiles()
        data.setdefault("profiles", {})
        data["profiles"][name] = {
            "label": label or name,
            "token": token,
            "country": country,
            "created": data["profiles"].get(name, {}).get("created")
                       or datetime.now().isoformat(timespec="seconds"),
            "updated": datetime.now().isoformat(timespec="seconds"),
        }
        if set_active or not data.get("active"):
            data["active"] = name
        _save_profiles(data)
    if data.get("active") == name:
        try:
            with open("token.txt", "w", encoding="utf-8") as f:
                f.write(token)
            _set_token(token)
        except Exception:
            pass
    warn = ""
    low = name.lower()
    expected = None
    if low.startswith(("alemania", "germania", "german", "de")):
        expected = "DE"
    elif low.startswith(("italia", "italy", "it")):
        expected = "IT"
    elif low.startswith(("espana", "spain", "es")):
        expected = "ES"
    elif low.startswith(("francia", "france", "fr")):
        expected = "FR"
    elif low.startswith(("portugal", "portogallo", "pt")):
        expected = "PT"
    if expected and country and country != expected:
        warn = (f"  ⚠️ ATENCIÓN: el nombre sugiere {expected} "
                f"pero el token es para {country}! ¿Iniciaste sesión con la cuenta correcta?")
    return True, f"Perfil '{name}' guardado ({country}){warn}"

def switch_profile(name):
    global VERSION
    name = str(name).strip().lower().replace(" ", "_")
    with profiles_lock:
        data = _load_profiles()
        if name not in (data.get("profiles") or {}):
            return False, f"Perfil '{name}' no encontrado"
        data["active"] = name
        _save_profiles(data)
        info = data["profiles"][name]
    tok = info.get("token", "")
    if not tok or tok.count(".") != 2:
        return False, f"Token del perfil '{name}' no válido"
    tmp_path = "token.txt.tmp"
    try:
        with open(tmp_path, "w", encoding="utf-8") as f:
            f.write(tok)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_path, "token.txt")
    except Exception as e:
        try:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
        except Exception:
            pass
        return False, f"Error escribiendo token.txt: {e}"
    _set_token(tok)
    try:
        VERSION = get_version()
    except Exception:
        pass
    diag = ""
    real_country = info.get("country", "?")
    try:
        decoded = jwt.decode(tok, options={"verify_signature": False})
        real_country = decoded.get("contentCountry", real_country)
        exp = decoded.get("exp")
        if exp:
            exp_dt = datetime.fromtimestamp(exp, tz=timezone.utc)
            now_utc = datetime.now(timezone.utc)
            if exp_dt < now_utc:
                diag = f" ⚠️ TOKEN EXPIRADO el {exp_dt.strftime('%d/%m %H:%M')} UTC — ¡vuelve a lanzar 🔑 Capturar Token!"
            else:
                mins = int((exp_dt - now_utc).total_seconds() / 60)
                diag = f" 🔑 válido {mins} min"
    except Exception:
        pass
    if real_country != info.get("country"):
        try:
            with profiles_lock:
                data = _load_profiles()
                if name in (data.get("profiles") or {}):
                    data["profiles"][name]["country"] = real_country
                    _save_profiles(data)
        except Exception:
            pass
    try:
        _release_all_locks()
    except Exception:
        pass
    return True, (f"🔀 Cambiado a '{name}' ({info.get('label','')}) "
                  f"— país REAL del token: {real_country}{diag}")

def delete_profile(name):
    name = str(name).strip().lower().replace(" ", "_")
    with profiles_lock:
        data = _load_profiles()
        profs = data.get("profiles") or {}
        if name not in profs:
            return False, "No existe"
        if len(profs) <= 1:
            return False, "No puedes eliminar el último perfil"
        del profs[name]
        if data.get("active") == name:
            data["active"] = next(iter(profs))
        _save_profiles(data)
    return True, f"Perfil '{name}' eliminado"

def get_active_profile():
    with profiles_lock:
        data = _load_profiles()
    name = data.get("active", "")
    info = (data.get("profiles") or {}).get(name, {})
    return name, info

def rename_profile(old_name, new_name):
    old_name = str(old_name).strip().lower().replace(" ", "_")
    new_name = str(new_name).strip().lower().replace(" ", "_")
    if not new_name:
        return False, "Nuevo nombre vacío"
    with profiles_lock:
        data = _load_profiles()
        profs = data.get("profiles") or {}
        if old_name not in profs:
            return False, "Perfil no encontrado"
        if new_name in profs:
            return False, "Nombre ya en uso"
        profs[new_name] = profs.pop(old_name)
        if data.get("active") == old_name:
            data["active"] = new_name
        _save_profiles(data)
    return True, f"Renombrado '{old_name}' → '{new_name}'"

def load_logos():
    try:
        if os.path.exists("logos.json"):
            with open("logos.json", "r", encoding='utf-8') as f:
                return json.load(f)
        default = {
            "DAZN 1": "https://image.discovery.indazn.com/eu/v3/linear-channel/none/Logo_LTV_DAZN_1/contain/center/center/none/80/85/70/png/image?brand=dazn",
            "DAZN 2": "https://image.discovery.indazn.com/eu/v3/linear-channel/none/Logo_LTV_Eurosport_2/contain/center/center/none/80/85/70/png/image?brand=dazn",
            "Eurosport 1": "http://schedulesdirect-api20141201-logos.s3.amazonaws.com/stationLogos/s79652_dark_360w_270h.png",
            "Inter TV": "https://commons.wikimedia.org/wiki/Special:FilePath/Inter_TV_-_Logo_2021.png",
            "Milan TV": "https://commons.wikimedia.org/wiki/Special:FilePath/Milan_TV_-_Logo_2016.png",
            "NOVE": "https://image.discovery.indazn.com/eu/v3/linear-channel/none/Logo_LTV_NOVE/contain/center/center/none/80/85/70/png/image?brand=dazn",
            "Real Time": "https://image.discovery.indazn.com/eu/v3/linear-channel/none/Logo_LTV_Real_Time/contain/center/center/none/80/85/70/png/image?brand=dazn",
            "NFL Network": "https://image.discovery.indazn.com/eu/v3/linear-channel/none/Logo_LTV_NFL-Network/contain/center/center/none/80/85/70/png/image?brand=dazn",
            "Radio TV Serie A": "https://image.discovery.indazn.com/eu/v3/linear-channel/none/Logo_Radio_TV_Serie_A/contain/center/center/none/80/85/70/png/image?brand=dazn",
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
    except Exception:
        pass
    return {}

def save_logo_overrides(data):
    try:
        with open(LOGO_OVERRIDES_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        print(f"⚠️ {e}")
        return False

def load_pending_events():
    try:
        if os.path.exists(PENDING_EVENTS_FILE):
            with open(PENDING_EVENTS_FILE, "r", encoding="utf-8") as f:
                d = json.load(f)
                return d if isinstance(d, list) else []
    except Exception:
        pass
    return []

def save_pending_events(data):
    try:
        with open(PENDING_EVENTS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        print(f"⚠️ {e}")
        return False

pending_events_lock = threading.Lock()
console_lock = threading.Lock()
channels_regen_trigger_lock = threading.Lock()

def _pending_event_start_ts(ev):
    v = ev.get('Start') or ev.get('EventStartTime') or ''
    if not v:
        return None
    try:
        return datetime.fromisoformat(str(v).replace('Z', '+00:00')).timestamp()
    except Exception:
        return None

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
    try:
        d.mkdir(parents=True, exist_ok=True)
    except Exception:
        pass
    return d

def _find_chrome_exe():
    cands = [
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        str(Path.home() / "AppData" / "Local" / "Google" / "Chrome" / "Application" / "chrome.exe"),
    ]
    for p in cands:
        if Path(p).exists():
            return p
    return None

def _find_edge_exe():
    cands = [
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
        str(Path.home() / "AppData" / "Local" / "Microsoft" / "Edge" / "Application" / "msedge.exe"),
    ]
    for p in cands:
        if Path(p).exists():
            return p
    return None

def _find_browser_exe():
    """Devuelve (ruta_exe, nombre_navegador) del navegador configurado o autodetectado.
    Config 'browser_type': 'auto' | 'chrome' | 'edge'."""
    pref = (config.get("browser_type", "auto") or "auto").lower()
    if pref == "chrome":
        p = _find_chrome_exe()
        return (p, "chrome") if p else (None, None)
    if pref == "edge":
        p = _find_edge_exe()
        return (p, "edge") if p else (None, None)
    p = _find_chrome_exe()
    if p:
        return (p, "chrome")
    p = _find_edge_exe()
    if p:
        return (p, "edge")
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
        if not req:
            return None
        req_headers = req.headers or {}
        res_headers = response.headers or {}
        ctype = (res_headers.get("content-type") or "").lower()
        body = ""
        url_l = url.lower()
        is_license = any(w in url_l for w in
                         ("license", "clearkey", "drm", "widevine",
                          "playback", "getkey"))
        skip_body = (not is_license) and any(
            x in ctype for x in ("video/", "audio/",
                                  "application/octet-stream", "image/")
        )
        if not skip_body:
            try:
                body = response.text()
            except Exception:
                try:
                    raw = response.body()
                    body = raw.decode("latin-1", errors="replace")
                except Exception:
                    body = ""
            if len(body) > 200_000:
                body = body[:200_000] + "\n\n... [TRUNCADO]"
        entry = {
            "startedDateTime": datetime.now(timezone.utc).isoformat(),
            "time": 0,
            "request": {
                "method": req.method or "GET",
                "url": url,
                "httpVersion": "HTTP/1.1",
                "headers": [{"name": k, "value": v} for k, v in req_headers.items()],
                "queryString": [],
                "cookies": [],
                "headersSize": -1,
                "bodySize": -1,
            },
            "response": {
                "status": status,
                "statusText": "",
                "httpVersion": "HTTP/1.1",
                "headers": [{"name": k, "value": v} for k, v in res_headers.items()],
                "cookies": [],
                "content": {
                    "size": len(body),
                    "mimeType": res_headers.get("content-type", ""),
                    "text": body,
                },
                "redirectURL": "",
                "headersSize": -1,
                "bodySize": len(body),
            },
            "cache": {},
            "timings": {"send": 0, "wait": 0, "receive": 0},
        }
        return entry
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
        # Override explícito
        if browser_type == "chrome":
            exe = _find_chrome_exe(); bname = "chrome"
        elif browser_type == "edge":
            exe = _find_edge_exe(); bname = "edge"
    if not exe:
        log("❌ Navegador no encontrado (Chrome ni Edge).")
        return None
    log(f"🌐 Navegador: {bname.upper()} ({exe})")
    if save_har is None:
        save_har = bool(config.get("har_recording_enabled", True))
    _pdir = profile_dir if profile_dir is not None else _browser_profile_dir(browser=bname)
    try:
        Path(_pdir).mkdir(parents=True, exist_ok=True)
    except Exception:
        pass
    args = [
        exe,
        f"--remote-debugging-port={BROWSER_DEBUG_PORT}",
        f"--user-data-dir={_pdir}",
        "--no-first-run", "--no-default-browser-check",
        "--remote-allow-origins=*", url,
    ]
    creationflags = 0
    if hasattr(subprocess, "DETACHED_PROCESS"):
        creationflags = subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP
    log(f"🚀 Iniciando {bname.upper()} en el puerto {BROWSER_DEBUG_PORT}...")
    log(f"   user-data-dir: {_pdir}")
    proc = subprocess.Popen(args, stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL, creationflags=creationflags)
    info = _wait_debug(BROWSER_DEBUG_HOST, BROWSER_DEBUG_PORT, timeout=30.0)
    if not info:
        log("❌ Puerto de debug no alcanzable.")
        try: proc.terminate()
        except Exception: pass
        return None
    found_token = {"value": None}
    interesting_responses = []
    pw = None
    try:
        pw = sync_playwright().start()
        browser = pw.chromium.connect_over_cdp(
            f"http://{BROWSER_DEBUG_HOST}:{BROWSER_DEBUG_PORT}")
        if not browser.contexts:
            log("❌ Sin contexto del navegador.")
            return None
        context = browser.contexts[0]

        def _on_request(request):
            if found_token["value"]:
                return
            try:
                headers = request.headers or {}
                auth = headers.get("authorization") or headers.get("Authorization")
                if auth and auth.startswith("Bearer eyJ"):
                    tok = auth.split(" ", 1)[1].strip()
                    if tok.count(".") == 2:
                        found_token["value"] = tok
                        log(f"🔑 Token capturado ({len(tok)} char)")
            except Exception:
                pass

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
                except Exception:
                    pass

            context.on("response", _on_response)
            log("📼 Grabación HAR activa (registro MPD / manifest / license)")

        try:
            page = context.new_page()
            try:
                page.goto(url, wait_until="domcontentloaded", timeout=30000)
            except Exception:
                pass
        except Exception:
            page = None

        log(f"🎧 Esperando token (máx {timeout_sec}s)...")
        deadline = time.time() + timeout_sec
        while time.time() < deadline and not found_token["value"]:
            try:
                if page:
                    page.wait_for_timeout(500)
                else:
                    time.sleep(0.5)
            except Exception:
                time.sleep(0.5)

        if found_token["value"]:
            grace = int(config.get("har_grace_seconds", 45))
            if save_har and grace > 0:
                log(f"✅ ¡Token capturado!")
                log(f"⏳ Tienes {grace}s para navegar en DAZN (canales, eventos, etc.)")
                log(f"   El HAR se guardará automáticamente al final del temporizador")
                for remaining in range(grace, 0, -1):
                    try:
                        if page:
                            page.wait_for_timeout(1000)
                        else:
                            time.sleep(1)
                    except Exception:
                        time.sleep(1)
                    if remaining % 10 == 0 and remaining != grace:
                        log(f"   ⏳ {remaining}s restantes...")
                log(f"⏹ Tiempo agotado → guardo HAR y cierro el navegador")

        if save_har and interesting_responses:
            log(f"📼 Procesando {len(interesting_responses)} respuestas para HAR...")
            har_entries = []
            for resp in interesting_responses:
                try:
                    entry = _har_entry_from_response(resp)
                    if entry:
                        har_entries.append(entry)
                except Exception:
                    continue
            if har_entries:
                ts = datetime.now().strftime("%Y%m%d_%H%M%S")
                har_file = f"dazn_capture_{ts}.har"
                try:
                    har_data = {
                        "log": {
                            "version": "1.2",
                            "creator": {"name": "DAZN Extractor", "version": VERSION},
                            "browser": {"name": f"{bname.upper()} (CDP)", "version": "142"},
                            "pages": [],
                            "entries": har_entries,
                        }
                    }
                    with open(har_file, "w", encoding="utf-8") as f:
                        json.dump(har_data, f, ensure_ascii=False, indent=2)
                    size_kb = os.path.getsize(har_file) / 1024
                    log(f"✅ HAR guardado: {har_file} ({size_kb:.1f} KB, {len(har_entries)} entries)")
                    try:
                        report = _har_analyze_vs_db(har_file)
                        in_db = len(report["in_db"]) + len(report["static"])
                        new_kids = len(report["new"])
                        license_new = len(report.get("license_new") or [])
                        if in_db or new_kids or license_new:
                            log(f"🎯 HAR vs DB → {in_db} ya conocidos, {new_kids} KID NUEVOS, "
                                f"{license_new} pares completos nuevos")
                            if new_kids > 0 or license_new > 0:
                                log(f"   💡 Usa 🔑 Gestor KID/KEY → 📥 Importar HAR")
                    except Exception:
                        pass
                except Exception as e:
                    log(f"⚠️ Error guardando HAR: {e}")
        elif save_har:
            log("📼 Ninguna respuesta interesante para registrar en el HAR")

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

# ==============================================================
# 📥 AUTO-IMPORT HAR → DB
# ==============================================================
def auto_import_har_to_db(har_path, log=print, verbose=True):
    try:
        report = _har_analyze_vs_db(har_path)
    except Exception as e:
        if verbose:
            log(f"⚠️ auto_import_har: análisis fallido: {e}")
        return {"added": 0, "updated": 0, "placeholder": 0, "total": 0}

    ext = _load_external_keys()
    added = updated = ph_added = 0

    complete = (report.get("license_new") or []) + (report.get("license_known") or [])
    seen_k = set()
    for lk in complete:
        kid = lk.get("kid")
        key = lk.get("key")
        if not (kid and key) or kid in seen_k:
            continue
        seen_k.add(kid)
        cur = ext.get(kid) or {}
        if not isinstance(cur, dict):
            cur = {}
        if cur.get("key") == key:
            continue
        existed = kid in ext
        cur["key"] = key
        cur.pop("status", None)
        cur.setdefault("name", "HAR auto-import")
        cur.setdefault("added", datetime.now().isoformat(timespec="seconds"))
        ext[kid] = cur
        if existed:
            updated += 1
        else:
            added += 1

    for o in (report.get("new") or []):
        k = o.get("kid")
        if not k or k in ext:
            continue
        ext[k] = {
            "key": "",
            "name": "HAR placeholder",
            "added": datetime.now().isoformat(timespec="seconds"),
            "status": "placeholder",
        }
        ph_added += 1

    if added or updated or ph_added:
        if _save_external_keys(ext):
            _invalidate_kid_index()
    else:
        if verbose:
            log(f"ℹ️ HAR ya todo en el DB ({len(complete)} pares, "
                f"{len(report.get('new') or [])} KID)")

    return {
        "added": added,
        "updated": updated,
        "placeholder": ph_added,
        "total": len(complete) + len(report.get("new") or []),
    }


def auto_import_recent_hars(log=print, max_age_sec=600, verbose=True):
    try:
        files = sorted(
            glob.glob("dazn_capture_*.har"),
            key=os.path.getmtime, reverse=True
        )
    except Exception as e:
        if verbose:
            log(f"⚠️ auto_import_recent_hars: {e}")
        return {"added": 0, "updated": 0, "placeholder": 0, "files": 0}

    now = time.time()
    total = {"added": 0, "updated": 0, "placeholder": 0, "files": 0}

    for fp in files:
        try:
            age = now - os.path.getmtime(fp)
            if age > max_age_sec:
                break
            stats = auto_import_har_to_db(fp, log=log, verbose=verbose)
            if stats["added"] or stats["updated"] or stats["placeholder"]:
                if verbose:
                    log(f"   📥 {os.path.basename(fp)}: "
                        f"+{stats['added']} completos, "
                        f"~{stats['updated']} act., "
                        f"+{stats['placeholder']} placeholder")
            total["added"] += stats["added"]
            total["updated"] += stats["updated"]
            total["placeholder"] += stats["placeholder"]
            total["files"] += 1
        except Exception as e:
            if verbose:
                log(f"⚠️ HAR {fp}: {e}")

    if total["files"] and (total["added"] or total["updated"] or total["placeholder"]):
        log(f"✅ Auto-import HAR: {total['files']} archivos → "
            f"+{total['added']} completos, "
            f"~{total['updated']} act., "
            f"+{total['placeholder']} placeholder")

    return total

def capture_and_save_token(log=print, profile_name=None):
    global VERSION
    pdir = _browser_profile_dir(profile_name) if profile_name else None
    if profile_name and pdir:
        log(f"🌐 Navegador AISLADO para el perfil '{profile_name}':")
        log(f"   {pdir}")
        log(f"   (si es una cuenta nueva, inicia SESIÓN con la nueva cuenta)")
    tok = _capture_token_via_cdp(log=log, profile_dir=pdir)
    if not tok:
        log("❌ Token no capturado.")
        return None
    try:
        with open("token.txt", "w", encoding="utf-8") as f:
            f.write(tok)
        _set_token(tok)
        target_name = None
        if profile_name:
            target_name = str(profile_name).strip().lower().replace(" ", "_")
        else:
            target_name, _ = get_active_profile()
        if target_name:
            try:
                decoded = jwt.decode(tok, options={"verify_signature": False})
                country = decoded.get("contentCountry", "?")
            except Exception:
                country = "?"
            with profiles_lock:
                data = _load_profiles()
                profs = data.get("profiles") or {}
                if target_name in profs:
                    profs[target_name]["token"] = tok
                    profs[target_name]["country"] = country
                    profs[target_name]["updated"] = datetime.now().isoformat(timespec="seconds")
                    _save_profiles(data)
                    log(f"👤 Perfil '{target_name}' actualizado con el nuevo token ({country})")
                else:
                    log(f"⚠️ Perfil '{target_name}' no está en profiles.json — "
                        f"el token está en token.txt, se guardará por el llamador")
        try: VERSION = get_version()
        except Exception: pass
        log(f"💾 Token guardado ({len(tok)} char)")

        try:
            stats = auto_import_recent_hars(log=log, max_age_sec=300)
            if stats["files"] == 0:
                log("ℹ️ Ningún HAR reciente para importar")
        except Exception as e:
            log(f"⚠️ Auto-import HAR: {e}")

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
    print("🎯 DAZN EXTRACTOR — SUPERFUSION v2 ATOMIC\n")

def clear_screen():
    ascii_clear()

def signal_handler(sig, frame):
    print('\nAdiós :)'); quit()

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
                         params=params, headers=headers,
                         proxies=proxies, impersonate="chrome", timeout=30)
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
                    if data.get(k):
                        err_msg = str(data[k]); break
            if not err_msg: err_msg = json.dumps(data)[:200]
            print(f'   ↳ {err_msg}')
            return None, None, None, None, None, err_code, None
        spd = sorted(pds, key=lambda i: i.get('CdnName', ''))
        pd = spd[0]
        ct = pd['CdnToken']
        clearkey_info = None
        for k in ('ClearKey', 'clearKey', 'Keys', 'keys', 'ContentKeys', 'contentKeys'):
            v = pd.get(k)
            if isinstance(v, dict) and v:
                for kid, key in v.items():
                    if isinstance(key, str) and len(key) >= 32:
                        clearkey_info = {"kid": kid, "key": key}
                        break
                if clearkey_info: break
            elif isinstance(v, list) and v:
                item = v[0]
                if isinstance(item, dict):
                    kid = item.get('kid') or item.get('KID') or item.get('keyId')
                    key = item.get('key') or item.get('KEY') or item.get('k')
                    if kid and key:
                        clearkey_info = {"kid": str(kid), "key": str(key)}
                        break
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
                clearkey_info)
    except Exception as e:
        print(f'   ↳ get_single: {e}')
        return None, None, None, None, None, None, None

def delete_concurrency(token, lock_id):
    if not lock_id: return
    headers = {
        'authorization': 'Bearer ' + token,
        'origin': 'https://www.dazn.com', 'referer': 'https://www.dazn.com/',
        'user-agent': USER_AGENT, 'x-correlation-id': str(uuid.uuid4()),
    }
    try:
        requests.delete('https://concurrency-v2.playback.indazn.com/v2/concurrency/lock/' + lock_id,
                        headers=headers, proxies=proxies, impersonate="chrome", timeout=15)
    except Exception:
        pass

def _release_all_locks():
    t = _get_token()
    if not t: return
    try:
        headers = {'authorization': 'Bearer ' + t,
                   'origin': 'https://www.dazn.com', 'referer': 'https://www.dazn.com/',
                   'user-agent': USER_AGENT}
        requests.delete('https://concurrency-v2.playback.indazn.com/v2/concurrency/locks',
                        headers=headers, proxies=proxies, impersonate='chrome', timeout=10)
        print("🧹 Bloqueos de concurrencia liberados.")
    except Exception:
        pass

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
    pname, pinfo = get_active_profile()
    if pname and pinfo:
        try:
            with profiles_lock:
                data = _load_profiles()
                if pname in (data.get("profiles") or {}):
                    data["profiles"][pname]["token"] = token
                    data["profiles"][pname]["updated"] = datetime.now().isoformat(timespec="seconds")
                    _save_profiles(data)
        except Exception:
            pass
    return token

def get_rails(token):
    headers = {
        'accept': 'application/json, text/plain, */*', 'content-type': 'application/json',
        'origin': 'https://www.dazn.com', 'referer': 'https://www.dazn.com/',
        'user-agent': USER_AGENT,
        'sec-ch-ua': '"Not:A-Brand";v="99", "Google Chrome";v="142", "Chromium";v="142"',
        'sec-ch-ua-mobile': '?0', 'sec-ch-ua-platform': '"Windows"',
    }
    decoded = jwt.decode(token, options={"verify_signature": False})
    ent = ''.join(e['id'] + ',' for e in decoded['entitlements']['entitlementSets'])
    params = {'groupId': 'home', 'country': decoded['contentCountry'],
              'openBrowse': 'false', 'userEntitlements': ent}
    try:
        r = requests.get('https://rails.discovery.indazn.com/eu/v8/rails', headers=headers,
                         params=params, proxies=proxies, impersonate='chrome', timeout=30)
        return json.loads(r.content).get('Rails', [])
    except Exception as e:
        print(f'Error obteniendo rails: {e}'); return []

def get_channel_rails(token):
    headers = {
        'accept': 'application/json, text/plain, */*', 'content-type': 'application/json',
        'origin': 'https://www.dazn.com', 'referer': 'https://www.dazn.com/',
        'user-agent': USER_AGENT,
        'sec-ch-ua': '"Not:A-Brand";v="99", "Google Chrome";v="142", "Chromium";v="142"',
        'sec-ch-ua-mobile': '?0', 'sec-ch-ua-platform': '"Windows"',
    }
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
        print(f'Error obteniendo rails de canales: {e}'); return []

def get_schedule_rails(token):
    headers = {
        'accept': 'application/json, text/plain, */*', 'content-type': 'application/json',
        'origin': 'https://www.dazn.com', 'referer': 'https://www.dazn.com/',
        'user-agent': USER_AGENT,
    }
    try:
        decoded = jwt.decode(token, options={"verify_signature": False})
    except Exception:
        return []
    ent = ''.join(e['id'] + ',' for e in decoded.get('entitlements', {}).get('entitlementSets', [])).strip(',')
    country = decoded.get('contentCountry', 'IT')
    attempts = [
        {'groupId': 'schedule', 'country': country, 'params': 'PageType:Schedule;ContentType:Schedule',
         'openBrowse': 'false', 'userEntitlements': ent},
        {'groupId': 'schedule', 'country': country, 'openBrowse': 'false', 'userEntitlements': ent},
        {'groupId': 'calendar', 'country': country, 'openBrowse': 'false', 'userEntitlements': ent},
    ]
    for params in attempts:
        try:
            r = requests.get('https://rails.discovery.indazn.com/eu/v8/rails', headers=headers,
                             params=params, proxies=proxies, impersonate='chrome', timeout=30)
            if r.status_code != 200: continue
            rails = json.loads(r.content).get('Rails', [])
            if rails: return rails
        except Exception:
            continue
    return []

def single_rail(token, rail_id, rail_params, retries=3):
    headers = {
        'accept': 'application/json, text/plain, */*', 'authorization': 'Bearer ' + token,
        'content-type': 'application/json',
        'origin': 'https://www.dazn.com', 'referer': 'https://www.dazn.com/',
        'user-agent': USER_AGENT,
    }
    decoded = jwt.decode(token, options={"verify_signature": False})
    params = {'platform': 'web', 'id': rail_id, 'country': decoded['contentCountry'],
              'languageCode': 'en', 'params': rail_params}
    last_err = None
    for attempt in range(retries):
        try:
            r = requests.get('https://rail-router.discovery.indazn.com/eu/v6/Rail',
                             headers=headers, params=params,
                             proxies=proxies, impersonate='chrome', timeout=20)
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
                if _is_blacklisted(t.get('Title') or ''):
                    continue
                if tt != 'Live' and not _is_linear_channel_tile(t):
                    continue
                aid = t.get('AssetId')
                if not aid or aid in seen_assets: continue
                seen_assets.add(aid); channels_data.append(t); aggiunti += 1
            print(f'✅ {aggiunti} nuevos (tot {len(channels_data)})')

    try:
        rails_sport = get_channel_rails(token) or []
        print(f'📺 {len(rails_sport)} rails deportes'); _process_rails(rails_sport, 'SPORT')
    except Exception as e:
        print(f'❌ {e}')
    try:
        rails_home = get_rails(token) or []
        print(f'🏠 {len(rails_home)} rails home'); _process_rails(rails_home, 'HOME')
    except Exception as e:
        print(f'❌ {e}')

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
    "Focus Serie A", "DAZN Focus Serie A", "Focus Serie A 24/7",
    "Focus Serie A HD",
}

def _is_linear_channel_tile(tile):
    title = (tile.get('Title') or '').strip()
    if _is_blacklisted(title):
        return False
    if title in KNOWN_LIVE_CHANNEL_NAMES:
        return True
    if _find_clearkey_for_title(title):
        return True
    comp = tile.get('Competition') or {}
    if isinstance(comp, dict):
        comp = comp.get('Title') or comp.get('Name') or ''
    if str(comp).strip().lower() == 'live tv':
        return True
    if tile.get('IsLinear') is True:
        return True
    if tile.get('EventId'):
        return False
    if tile.get('ChannelNumber') is not None:
        return True
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
                if _is_blacklisted(t.get('Title') or ''):
                    continue
                if _is_linear_channel_tile(t):
                    continue
                accept = False
                if tt == 'UpComing': accept = True
                elif include_live and tt == 'Live':
                    accept = True
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
    except Exception as e:
        print(f'❌ {e}')
    try:
        rails_sport = get_channel_rails(token) or []
        print(f'📺 {len(rails_sport)} rails deportes'); _process_rails(rails_sport, 'SPORT')
    except Exception as e:
        print(f'❌ {e}')
    try:
        rails_home = get_rails(token) or []
        print(f'🏠 {len(rails_home)} rails home'); _process_rails(rails_home, 'HOME')
    except Exception as e:
        print(f'❌ {e}')

    def _ts(e):
        v = e.get('Start') or e.get('EventStartTime') or ''
        try: return datetime.fromisoformat(v.replace('Z', '+00:00')).timestamp()
        except Exception: return float('inf')
    events_data.sort(key=_ts)
    try:
        with open('dazn_events.json', 'w', encoding='utf-8') as f:
            json.dump(events_data, f, ensure_ascii=False, indent=2)
    except Exception:
        pass
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

def _titles_bullet_list(events_list, limit=20):
    titles = [_event_title(e) for e in events_list]
    lines = "\n".join(f"• {t}" for t in titles[:limit])
    extra = f"\n... y otros {len(titles) - limit}" if len(titles) > limit else ""
    return lines + extra

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
        if nxt == '' or nxt in (':', ' ', '-'):
            return url
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

def load_category_logos():
    try:
        if os.path.exists(CATEGORY_LOGOS_FILE):
            with open(CATEGORY_LOGOS_FILE, "r", encoding="utf-8") as f:
                d = json.load(f)
                if isinstance(d, dict): return d
        WM = "https://commons.wikimedia.org/wiki/Special:FilePath/"
        default = {
            "sports": {
                "ciclismo": WM + "Cycling_(road)_pictogram.svg",
                "tenis": WM + "Tennis_pictogram.svg",
                "baloncesto": WM + "Basketball_pictogram.svg",
            },
            "competitions": {
                "la liga": WM + "LaLiga_logo_2023.svg",
                "serie a": WM + "Serie_A_logo_2022.svg",
            }
        }
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

def _find_clearkey_for_title(title):
    if not title:
        return None
    _dep = _load_deprecated_statics()
    _key_norm = re.sub(r"\s+", " ", str(title).replace("\u00a0", " ")).strip().upper()
    if _key_norm in _dep:
        return None
    t_norm = re.sub(r"\s+", " ", str(title).replace("\u00a0", " ")).strip().upper()
    aliases = {
        "RADIO TV SERIE A":              "RADIO TV RDS",
        "NFL NETWORK: LIVE 24/7 COVERAGE": "NFL NETWORK",
        "EUROSPORT 1 (🇮🇹)":              "EUROSPORT 1",
        "EUROSPORT 2 (🇮🇹)":              "EUROSPORT 2",
        "DAZN FOCUS SERIE A":            "FOCUS SERIE A",
        "FOCUS SERIE A 24/7":            "FOCUS SERIE A",
        "FOCUS SERIE A 🇮🇹":             "FOCUS SERIE A",
        "FOCUS SERIE A HD":              "FOCUS SERIE A",
        "FOCUS SERIE A LIVE":            "FOCUS SERIE A",
        "FOCUS SERIE A (HD)":            "FOCUS SERIE A",
    }
    if t_norm in aliases:
        return STATIC_CLEARKEY_KEYS.get(aliases[t_norm])
    if t_norm in STATIC_CLEARKEY_KEYS:
        return STATIC_CLEARKEY_KEYS[t_norm]

    def _squash(s):
        return re.sub(r"\s+", "", s.upper())

    t_sq = _squash(t_norm)
    candidates = []
    for k, kv in STATIC_CLEARKEY_KEYS.items():
        k_sq = _squash(k)
        if k_sq == t_sq:
            candidates.append((1000, k, kv))
        elif k in t_norm or t_norm in k or k_sq in t_sq or t_sq in k_sq:
            candidates.append((len(k), k, kv))
    if candidates:
        candidates.sort(key=lambda x: -x[0])
        return candidates[0][2]
    if re.search(r"\bfocus\b", t_norm) and re.search(r"\bserie\s*a\b", t_norm):
        return STATIC_CLEARKEY_KEYS.get("FOCUS SERIE A")
    return None

def _build_m3u_entry(title, aid, grp_title, group_logo, logo_url,
                     manifest_url, cdn_name, cdn_token, kid_hex, key_hex,
                     manifest_type="mpd", license_type="org.w3.clearkey",
                     license_format="kid_key"):
    if license_format == "json":
        license_key = json.dumps({kid_hex: key_hex}, separators=(",", ":"))
    else:
        license_key = f"{kid_hex}:{key_hex}"
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

def _resolve_channel_number(title):
    if not title:
        return None
    t = re.sub(r"\s+", " ", str(title).replace("\u00a0", " ")).strip().upper()
    if t in CHANNEL_NUMBER_MAP:
        return CHANNEL_NUMBER_MAP[t]
    t2 = t.split(":")[0].strip()
    if t2 and t2 in CHANNEL_NUMBER_MAP:
        return CHANNEL_NUMBER_MAP[t2]
    for suffix in (" (🇮🇹)", " (🇩🇪)", " (🇪🇸)", " (🇬🇧)", " (🇫🇷)"):
        if t + suffix in CHANNEL_NUMBER_MAP:
            return CHANNEL_NUMBER_MAP[t + suffix]
        if t2 + suffix in CHANNEL_NUMBER_MAP:
            return CHANNEL_NUMBER_MAP[t2 + suffix]
    t_clean = re.sub(r"\s*\([^)]*\)\s*$", "", t).strip()
    if t_clean in CHANNEL_NUMBER_MAP:
        return CHANNEL_NUMBER_MAP[t_clean]
    return None

def _title_for_hls(title, country_code):
    title = (title or "").strip()
    if not title:
        return title
    if re.search(r"\([\U0001F1E6-\U0001F1FF]{2}\)", title):
        return title
    flag = _COUNTRY_FLAGS.get((country_code or "").upper())
    if flag:
        return f"{title} ({flag})"
    return title

def _build_hls_m3u_entry(title, channel_number, kid_hex, key_hex,
                         base_url=None):
    if base_url is None:
        base_url = config.get("hls_base_url") or HLS_BASE_URL_DEFAULT
    try:
        stream_url = base_url.format(num=channel_number)
    except Exception:
        stream_url = base_url
    license_key = json.dumps({kid_hex: key_hex}, separators=(",", ":"))
    return (
        f'#EXTINF:-1,{title}\n'
        f'#KODIPROP:inputstream.adaptive.manifest_type=m3u8\n'
        f'#KODIPROP:inputstream.adaptive.license_type=clearkey\n'
        f'#KODIPROP:inputstream.adaptive.license_key={license_key}\n'
        f'#EXTVLCOPT:http-user-agent={HLS_USER_AGENT}\n'
        f'{stream_url}\n'
    )

def generate_dazn_playlist(output_file=OUTPUT_FILE_CHANNELS_DEFAULT,
                            selected_channels=None):
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
        successi = 0
        senza_chiavi = []
        senza_playback = []
        ck_hunter_wins = 0
        key_hunter_wins = 0
        wvd_wins = 0
        kid_mismatch_skip = 0
        auto_deprecate = 0
        hls_entries = []
        hls_skipped_no_num = []
        pname, pinfo = get_active_profile()
        active_country = (pinfo or {}).get("country", "") or ""

        for i, ch in enumerate(selected_channels, 1):
            title = (ch.get('Title') or '?').strip()
            aid = (ch.get('AssetId') or '').strip()
            grp_title, _ = _group_title_for_tile(ch, default_group)
            logo_url, _ = _event_logo(ch, logos)
            if not logo_url: logo_url = group_logo
            print(f'[{i}/{len(selected_channels)}] {title}...', end=' ', flush=True)
            if not aid:
                print('❌ Sin AssetId')
                senza_playback.append(title)
                continue
            kk_static = _find_clearkey_for_title(title)
            (manifest_url, cdn_name, cdn_token, la_url, lock_id,
             err_code, clearkey_dyn) = get_single(_get_token(), aid, pin)
            if not manifest_url:
                print('❌ Playback no disponible')
                senza_playback.append(title)
                continue
            delete_concurrency(_get_token(), lock_id)
            kid_hex = key_hex = None
            manifest_kid = None

            if clearkey_dyn and clearkey_dyn.get('kid') and clearkey_dyn.get('key'):
                kid_hex = clearkey_dyn['kid']
                key_hex = clearkey_dyn['key']
                try:
                    ck_hunter_register(kid_hex, key_hex, title)
                except Exception:
                    pass
            else:
                print('🔍 Búsqueda KID...', end=' ', flush=True)
                manifest_kid = _extract_kid_from_mpd(
                    manifest_url, _get_token(),
                    cdn_name=cdn_name, cdn_token=cdn_token)
                if manifest_kid:
                    db_key, db_src = ck_hunter_lookup(manifest_kid)
                    if db_key:
                        kid_hex, key_hex = manifest_kid, db_key
                        ck_hunter_wins += 1
                        print(f'(KID: {db_src})', end=' ', flush=True)
                    else:
                        try:
                            ck_hunter_add_placeholders(
                                [{"kid": manifest_kid, "name": title}],
                                default_name=title
                            )
                            print(f'(KID {manifest_kid[:8]}… nuevo → placeholder)',
                                  end=' ', flush=True)
                        except Exception:
                            pass

                if not kid_hex and manifest_kid and la_url:
                    print('🔐 KEY Hunter...', end=' ', flush=True)
                    hunted = key_hunter_request_license(
                        manifest_kid, la_url, _get_token(),
                        cdn_name=cdn_name, cdn_token=cdn_token,
                        verbose=False
                    )
                    if hunted:
                        kid_hex, key_hex = manifest_kid, hunted
                        key_hunter_wins += 1
                        try:
                            ck_hunter_register(manifest_kid, hunted, title)
                        except Exception:
                            pass
                        print('✅', end=' ', flush=True)

                if not kid_hex and kk_static:
                    static_kid, static_key = kk_static
                    static_kid_norm = static_kid.lower().replace('-', '')
                    if manifest_kid is None:
                        kid_hex, key_hex = static_kid_norm, static_key
                    elif manifest_kid == static_kid_norm:
                        kid_hex, key_hex = static_kid_norm, static_key
                    else:
                        print(f'⚠️ KID mismatch '
                              f'(estática={static_kid_norm[:8]}…, '
                              f'stream={manifest_kid[:8]}…) — canal de otro país',
                              end=' ', flush=True)
                        kid_mismatch_skip += 1
                        try:
                            _deprecate_static_for_title(
                                title, static_kid_norm, manifest_kid,
                                reason="KID mismatch auto-detectado"
                            )
                            ck_hunter_add_placeholders(
                                [{"kid": manifest_kid, "name": title}],
                                default_name=title
                            )
                            auto_deprecate += 1
                            print(f' 🩹 auto-deprecada + placeholder registrado',
                                  end=' ', flush=True)
                        except Exception:
                            pass

            if (not kid_hex) and la_url and config.get("wvd_enabled", True) \
                    and _pywidevine_available():
                print('🎬 WVD Hunter...', end=' ', flush=True)
                wvd = widevine_attempt(
                    manifest_url, la_url, title, _get_token(),
                    cdn_name=cdn_name, cdn_token=cdn_token, verbose=True)
                if wvd:
                    kid_hex, key_hex = wvd["kid"], wvd["key"]
                    wvd_wins += 1
                    print('✅', end=' ', flush=True)
                else:
                    print('✗', end=' ', flush=True)

            if not kid_hex or not key_hex:
                print('❌ Ninguna clave válida (API + KID-DB + KEY Hunter + estática + WVD)')
                senza_chiavi.append(title)
                continue

            title_sq = re.sub(r"\s+", "", title.upper())
            spec = (CHANNEL_STREAM_SPECS.get(title.upper())
                    or CHANNEL_STREAM_SPECS.get(title_sq)
                    or {})
            m3u += _build_m3u_entry(
                title, aid, grp_title, group_logo, logo_url,
                manifest_url, cdn_name, cdn_token, kid_hex, key_hex,
                manifest_type=spec.get("manifest_type", "mpd"),
                license_type=spec.get("license_type", "org.w3.clearkey"),
                license_format=spec.get("license_format", "kid_key"),
            )
            successi += 1
            if config.get("hls_output_enabled", True):
                ch_num = _resolve_channel_number(title)
                if ch_num:
                    hls_title = _title_for_hls(title, active_country)
                    hls_entries.append((hls_title, ch_num, kid_hex, key_hex))
                else:
                    hls_skipped_no_num.append(title)
            print('✅ OK')

        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(m3u)

        print(f"\n📊 RESULTADO CANALES: {successi}/{len(selected_channels)} OK")
        if ck_hunter_wins:
            print(f"   🎯 KID lookup (DB): {ck_hunter_wins} resueltos vía KID matching")
        if key_hunter_wins:
            print(f"   🔐 KEY Hunter: {key_hunter_wins} resueltos vía license server")
        if wvd_wins:
            print(f"   🎬 WVD Widevine: {wvd_wins} resueltos vía WVD.wvd")
        if kid_mismatch_skip:
            print(f"   ⚠️ KID mismatch estática: {kid_mismatch_skip}")
        if auto_deprecate:
            print(f"   🩹 Estáticas auto-deprecadas: {auto_deprecate} "
                  f"(ver deprecated_statics.json)")
        if senza_chiavi:
            print(f"   🔑 Sin clave ({len(senza_chiavi)}): "
                  + ", ".join(senza_chiavi[:10]))
        if senza_playback:
            print(f"   ⚠️ Playback no disponible ({len(senza_playback)}): "
                  + ", ".join(senza_playback[:10]))

        if config.get("hls_output_enabled", True) and hls_entries:
            hls_file = config.get("output_file_hls", OUTPUT_FILE_HLS_DEFAULT)
            hls_m3u = "#EXTM3U\n"
            for (htitle, hnum, hkid, hkey) in hls_entries:
                hls_m3u += _build_hls_m3u_entry(htitle, hnum, hkid, hkey)
            try:
                with open(hls_file, "w", encoding="utf-8") as f:
                    f.write(hls_m3u)
                print(f"\n📻 Archivo HLS generado: {hls_file} "
                      f"({len(hls_entries)} canales AppleCoreMedia)")
                if hls_skipped_no_num:
                    print(f"   ⚠️ HLS skip (sin número de canal): {len(hls_skipped_no_num)} "
                          f"→ " + ", ".join(hls_skipped_no_num[:8]))
            except Exception as e:
                print(f"⚠️ Error escribiendo HLS: {e}")
        elif config.get("hls_output_enabled", True):
            print(f"\n📻 HLS: ningún canal mapeado → archivo no generado")

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
        successi = 0
        falliti = []
        senza_chiave = []
        programmati = []
        retained = 0
        ck_hunter_wins = 0
        ck_hunter_miss = 0
        wvd_wins = 0

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
                print('❌ Sin AssetId')
                falliti.append((tile, title))
                continue
            static_kk = _find_clearkey_for_title(title)
            (manifest_url, cdn_name, cdn_token, la_url, lock_id,
             err_code, clearkey_info) = get_single(_get_token(), aid, pin)
            if not manifest_url:
                if err_code in PERMANENT_ERROR_CODES:
                    print('🚫 No elegible')
                    continue
                if err_code in PENDING_ERROR_CODES:
                    if auto_pending:
                        try: add_pending_event(tile, "Media no disponible (programado)")
                        except Exception: pass
                        print('📅 Programado')
                        programmati.append(title)
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
                        print('♻️ Desde caché')
                        continue
                print('❌')
                falliti.append((tile, title))
                continue

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
                manifest_kid = _extract_kid_from_mpd(
                    manifest_url, _get_token(),
                    cdn_name=cdn_name, cdn_token=cdn_token)
                if manifest_kid:
                    hunted = key_hunter_request_license(
                        manifest_kid, la_url, _get_token(),
                        cdn_name=cdn_name, cdn_token=cdn_token,
                        verbose=False
                    )
                    if hunted:
                        clearkey_info = {"kid": manifest_kid, "key": hunted}
                        try:
                            ck_hunter_register(manifest_kid, hunted, title)
                        except Exception:
                            pass

            if not clearkey_info and la_url and config.get("wvd_enabled", True) \
                    and _pywidevine_available():
                print('🎬 WVD Hunter...', end=' ', flush=True)
                wvd = widevine_attempt(
                    manifest_url, la_url, title, _get_token(),
                    cdn_name=cdn_name, cdn_token=cdn_token, verbose=True)
                if wvd:
                    clearkey_info = {"kid": wvd["kid"], "key": wvd["key"]}
                    wvd_wins += 1

            if not clearkey_info:
                print('❌ Ninguna clave (estática + API + CK Hunter + KEY Hunter + WVD)')
                senza_chiave.append(title)
                continue

            kid_hex = clearkey_info['kid']
            key_hex = clearkey_info['key']
            try:
                ck_hunter_register(kid_hex, key_hex, title)
            except Exception:
                pass

            m3u += _build_m3u_entry(title, aid, grp_title, group_logo, logo_url,
                                     manifest_url, cdn_name, cdn_token, kid_hex, key_hex)
            successi += 1
            print('✅ OK')

            if retain_cache and key:
                cache[key] = {
                    "tile": tile,
                    "Start": tile.get('Start') or tile.get('EventStartTime') or '',
                    "manifest_url": manifest_url,
                    "cdn_name": cdn_name,
                    "cdn_token": cdn_token,
                    "kid": kid_hex,
                    "key": key_hex,
                    "LastOkAt": datetime.now().isoformat(timespec="seconds"),
                }

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
                    successi += 1
                    retained += 1
            _save_active_events_cache(cache)

        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(m3u)

        ts = datetime.now().strftime('%Y%m%d_%H%M%S')
        try:
            with open(f"dazn_events_details_{ts}.json", 'w', encoding='utf-8') as f:
                json.dump({"successi": successi, "retained": retained,
                           "ck_hunter_wins": ck_hunter_wins,
                           "ck_hunter_miss": ck_hunter_miss,
                           "wvd_wins": wvd_wins,
                           "falliti": len(falliti)}, f, indent=2)
        except Exception:
            pass

        if auto_pending and successi:
            try:
                failed_titles = {t for _, t in falliti} | set(programmati)
                successful_keys = {
                    (e.get('EventId') or e.get('AssetId') or '')
                    for e in events_list
                    if _event_title(e) not in failed_titles
                }
                still = [p for p in load_pending_events()
                         if (p.get('EventId') or p.get('AssetId') or '')
                            not in successful_keys]
                save_pending_events(still)
            except Exception as e:
                print(f"⚠️ limpieza pending: {e}")

        print(f"\n📊 RESULTADO: {successi} OK (de los cuales {retained} desde caché)")
        if ck_hunter_wins:
            print(f"   🎯 CK Hunter: {ck_hunter_wins} recuperados vía KID matching")
        if ck_hunter_miss:
            print(f"   🔍 CK Hunter miss: {ck_hunter_miss}")
        if wvd_wins:
            print(f"   🎬 WVD Widevine: {wvd_wins} resueltos vía WVD.wvd")
        if senza_chiave:
            print(f"   🔑 Sin clave ({len(senza_chiave)}): "
                  + ", ".join(senza_chiave[:10]))
        if programmati:
            print(f"   📅 Programados ({len(programmati)}): " + ", ".join(programmati[:10]))
        if falliti:
            print(f"   ⚠️ Fallidos ({len(falliti)}): "
                  + ", ".join(t for _, t in falliti[:10]))

        return output_file
    finally:
        console_lock.release()

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
    "channels_scheduler_active": False,
    "channels_scheduler_interval_minutes": 60,
    "channels_scheduler_mode": "interval",
    "channels_fixed_times": ["14:45", "17:45", "20:30"],
    "channels_regenerate_with_events": False,
    "output_file_channels": OUTPUT_FILE_CHANNELS_DEFAULT,
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
    "browser_type": "auto",   # "auto" | "chrome" | "edge"
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

def add_pending_event(tile, reason=""):
    data = load_pending_events()
    aid = str(tile.get('AssetId') or '').strip()
    eid = str(tile.get('EventId') or '').strip()
    key = eid or aid
    if not key: return False
    existed = any((x.get('EventId') or x.get('AssetId') or '') == key for x in data)
    data = [x for x in data if (x.get('EventId') or x.get('AssetId') or '') != key]
    entry = dict(tile)
    entry["AssetId"] = aid
    entry["EventId"] = eid
    entry["Start"] = tile.get('Start') or tile.get('EventStartTime') or ''
    entry["AddedAt"] = datetime.now().isoformat(timespec="seconds")
    entry["Reason"] = reason or "Añadido manualmente"
    data.append(entry)
    ok = save_pending_events(data)
    if ok and not existed:
        threading.Thread(target=_trigger_channels_regen_for_new_pending, daemon=True).start()
    return ok

def remove_pending_event(key):
    data = load_pending_events()
    key = str(key or '').strip()
    data = [x for x in data if (x.get('EventId') or x.get('AssetId') or '') != key]
    save_pending_events(data)

CHANNELS_REGEN_SKIP_WINDOW_SEC = 180

def _trigger_channels_regen_for_new_pending():
    if not channels_regen_trigger_lock.acquire(blocking=False):
        return
    try:
        try:
            last_run_str = _load_channel_snapshot().get("last_run", "")
            if last_run_str:
                last_run_dt = datetime.fromisoformat(last_run_str)
                if (datetime.now() - last_run_dt).total_seconds() < CHANNELS_REGEN_SKIP_WINDOW_SEC:
                    return
        except Exception:
            pass
        try:
            print("\n📺 Nuevo pending → regenero canales...")
            _run_channels_scheduler_cycle()
        except Exception as e:
            print(f"❌ {e}")
    finally:
        channels_regen_trigger_lock.release()

def find_event_title(*keywords):
    if not keywords:
        print("⚠️ Pasa al menos una palabra clave.")
        return []
    ev = get_scheduled_events(_get_token(), True, False) or []
    needles = [_norm(k) for k in keywords]
    trovati = []
    for e in ev:
        hay = _norm(str(e.get('Title') or ''))
        if all(n in hay for n in needles):
            trovati.append(e)
    if not trovati:
        print(f"❌ Ningún evento para: {', '.join(keywords)}")
        return []
    print(f"✅ {len(trovati)} encontrados:\n")
    for e in trovati:
        print(f"  Título: {e.get('Title')!r}")
        print(f"  Inicio: {e.get('Start') or e.get('EventStartTime') or '?'}")
        print(f"  Clave:  {_event_override_key(e)!r}")
        print("  " + "-" * 50)
    return trovati

def debug_dump_sample_tiles(n=3):
    ev = get_scheduled_events(_get_token(), True, False) or []
    sample = ev[:n]
    print(json.dumps(sample, indent=2, ensure_ascii=False))
    try:
        with open('tile_debug.json', 'w', encoding='utf-8') as f:
            json.dump(sample, f, indent=2, ensure_ascii=False)
    except Exception:
        pass
    return sample

def ck_hunter_scan_event(event_title_or_tile, debug=False):
    if isinstance(event_title_or_tile, str):
        ev = get_scheduled_events(_get_token(), True, False) or []
        matches = [e for e in ev if _norm(event_title_or_tile) in _norm(e.get('Title') or '')]
        if not matches:
            print(f"❌ Ninguna coincidencia para {event_title_or_tile!r}")
            return None
        tile = matches[0]
    else:
        tile = event_title_or_tile
    aid = _event_asset_id(tile)
    title = _event_title(tile)
    print(f"🔎 {title} (asset={aid})")
    r = get_single(_get_token(), aid, pin)
    manifest_url, cdn_name, cdn_token = r[0], r[1], r[2]
    if not manifest_url:
        print("   ❌ Sin manifest")
        return None
    kid = _extract_kid_from_mpd(manifest_url, _get_token(),
                                cdn_name=cdn_name, cdn_token=cdn_token)
    if not kid:
        print("   ❌ KID no extraído")
        return None
    print(f"   KID: {kid}")
    key, src = ck_hunter_lookup(kid)
    if key:
        print(f"   ✅ ¡Encontrado! key={key} (source: {src})")
    else:
        print(f"   ❌ KID desconocido — hay que añadirlo a external_keys.json")
    if debug:
        print(f"   manifest: {manifest_url}")
        if r[3]:
            print(f"   la_url:   {r[3]}")
    return {"kid": kid, "key": key, "source": src}

# ==============================================================
# 🔑 GESTOR MANUAL KID / KEY
# ==============================================================
def _validate_hex32(s):
    if not s:
        return False
    s = s.strip().lower().replace("-", "").replace(" ", "")
    return len(s) == 32 and all(c in "0123456789abcdef" for c in s)

def _normalize_hex32(s):
    if not s:
        return ""
    return s.strip().lower().replace("-", "").replace(" ", "")

def open_kid_key_manager_tkinter(parent=None):
    try:
        import tkinter as tk
        from tkinter import ttk, messagebox, filedialog, simpledialog
    except ImportError:
        print("❌ tkinter no disponible.")
        return
    standalone = (parent is None)
    root = tk.Tk() if standalone else tk.Toplevel(parent)
    if not standalone:
        try: root.transient(parent)
        except Exception: pass
    root.title("🔑 Gestor pares KID / KEY — CK Hunter")
    root.geometry("1200x800")
    root.configure(bg="#0d1117")
    try: root.grab_set()
    except Exception: pass
    header = tk.Frame(root, bg="#1a1a2e", height=60)
    header.pack(fill="x"); header.pack_propagate(False)
    tk.Label(header, text="🔑 Gestor pares KID / KEY",
             bg="#1a1a2e", fg="#00d4ff",
             font=("Segoe UI", 15, "bold")).pack(side="left", padx=20, pady=15)
    tk.Label(header, text="Completa las KEY faltantes · pega JSON · importar HAR",
             bg="#1a1a2e", fg="#bc8cff",
             font=("Segoe UI", 10, "italic")).pack(side="right", padx=20)
    info = tk.Label(root, text="", bg="#0d1117", fg="#8b949e",
                    font=("Segoe UI", 9, "italic"), anchor="w")
    info.pack(fill="x", padx=12, pady=(8, 4))
    ff = tk.Frame(root, bg="#0d1117"); ff.pack(fill="x", padx=12, pady=4)
    tk.Label(ff, text="🔎 Filtrar:", bg="#0d1117", fg="#c9d1d9").pack(side="left")
    fv = tk.StringVar()
    tk.Entry(ff, textvariable=fv, width=40, bg="#161b22", fg="#c9d1d9",
             insertbackground="#c9d1d9", relief="flat").pack(side="left", padx=6)
    only_incomplete = tk.IntVar(value=1)
    tk.Checkbutton(ff, text="Solo KID sin KEY", variable=only_incomplete,
                   bg="#0d1117", fg="#c9d1d9", selectcolor="#161b22",
                   activebackground="#0d1117",
                   activeforeground="#58a6ff").pack(side="left", padx=10)
    tf = tk.Frame(root, bg="#0d1117"); tf.pack(fill="both", expand=True, padx=12, pady=5)
    style = ttk.Style()
    try: style.theme_use("clam")
    except Exception: pass
    style.configure("KidKey.Treeview", background="#161b22", foreground="#c9d1d9",
                    fieldbackground="#161b22", rowheight=24, borderwidth=0)
    style.configure("KidKey.Treeview.Heading", background="#21262d",
                    foreground="#58a6ff", font=("Segoe UI", 10, "bold"))
    style.map("KidKey.Treeview", background=[("selected", "#1f6feb")])
    tree = ttk.Treeview(tf,
                        columns=("cat", "kid", "key", "name", "stato"),
                        show="headings", height=14,
                        style="KidKey.Treeview", selectmode="browse")
    for col, txt, w in [("cat", "Categoría", 90),
                        ("kid", "KID", 300),
                        ("key", "KEY", 300),
                        ("name", "Nombre", 260),
                        ("stato", "Estado", 110)]:
        tree.heading(col, text=txt); tree.column(col, width=w)
    vsb = ttk.Scrollbar(tf, orient="vertical", command=tree.yview)
    tree.configure(yscroll=vsb.set); vsb.pack(side="right", fill="y")
    tree.pack(side="left", fill="both", expand=True)
    rows_cache = []

    def _load_rows():
        ext = _load_external_keys()
        rows = []
        for kid, inf in ext.items():
            if not isinstance(inf, dict):
                continue
            cat = inf.get("_category") or (
                "linear" if (inf.get("country") or inf.get("channels")) else "events")
            key = inf.get("key") or ""
            rows.append({
                "kid": kid, "key": key,
                "name": inf.get("name") or "?",
                "cat": cat,
                "status": inf.get("status") or ("ok" if key else "missing_key"),
            })
        rows.sort(key=lambda r: (bool(r["key"]), r["cat"], r["name"]))
        return rows

    def refresh(*a):
        nonlocal rows_cache
        rows_cache = _load_rows()
        filt = fv.get().strip().lower()
        only_missing = bool(only_incomplete.get())
        for iid in tree.get_children():
            tree.delete(iid)
        for i, r in enumerate(rows_cache):
            if only_missing and r["key"]:
                continue
            hay = f"{r['kid']} {r['name']} {r['cat']}".lower()
            if filt and filt not in hay:
                continue
            if r["key"]:
                st = "✅ ok"
            elif r["status"] == "placeholder":
                st = "📌 placeholder"
            else:
                st = "❌ sin KEY"
            tree.insert("", "end", iid=f"row_{i}",
                        values=(r["cat"], r["kid"], r["key"] or "(vacía)",
                                r["name"], st))
        total = len(rows_cache)
        missing = sum(1 for r in rows_cache if not r["key"])
        info.config(
            text=f"📊 Total KID: {total}   |   ✅ con KEY: {total - missing}   |   ❌ sin KEY: {missing}")

    fv.trace_add("write", refresh)
    only_incomplete.trace_add("write", refresh)

    def _get_selected():
        s = tree.selection()
        if not s:
            return None
        try:
            idx = int(s[0].split("_")[1])
        except Exception:
            return None
        return rows_cache[idx] if 0 <= idx < len(rows_cache) else None

    ef = tk.LabelFrame(root, text="✏️ Modificar / Añadir par KID + KEY",
                       bg="#0d1117", fg="#58a6ff",
                       font=("Segoe UI", 10, "bold"))
    ef.pack(fill="x", padx=12, pady=(8, 4))
    fields = tk.Frame(ef, bg="#0d1117"); fields.pack(fill="x", padx=8, pady=6)

    def _field(parent, label, default=""):
        r = tk.Frame(parent, bg="#0d1117"); r.pack(fill="x", pady=2)
        tk.Label(r, text=label, bg="#0d1117", fg="#c9d1d9",
                 font=("Segoe UI", 10, "bold"), width=20, anchor="w").pack(side="left")
        v = tk.StringVar(value=default)
        tk.Entry(r, textvariable=v, bg="#161b22", fg="#c9d1d9",
                 insertbackground="#58a6ff", relief="flat",
                 font=("Consolas", 10)).pack(
                     side="left", fill="x", expand=True, padx=6, ipady=3)
        return v

    kid_v  = _field(fields, "KID (32 hex):")
    key_v  = _field(fields, "KEY (32 hex):")
    name_v = _field(fields, "Nombre:")
    cat_v  = _field(fields, "Categoría (linear/events):", "events")

    status_lbl = tk.Label(ef, text="", bg="#0d1117", fg="#8b949e",
                          font=("Segoe UI", 9, "italic"), anchor="w")
    status_lbl.pack(fill="x", padx=8, pady=(0, 6))

    def on_select(evt=None):
        r = _get_selected()
        if not r:
            return
        kid_v.set(r["kid"])
        key_v.set(r["key"])
        name_v.set(r["name"])
        cat_v.set(r["cat"])
        if not r["key"]:
            status_lbl.config(
                text="⚠️ KID sin KEY: pega la KEY (o JSON ClearKey) y guarda.",
                fg="#d29922")
        else:
            status_lbl.config(
                text=f"✅ Par completo (categoría: {r['cat']}).",
                fg="#3fb950")

    tree.bind("<<TreeviewSelect>>", on_select)

    def clear_fields():
        kid_v.set(""); key_v.set(""); name_v.set("")
        cat_v.set("events")
        status_lbl.config(text="", fg="#8b949e")
        try: tree.selection_remove(tree.selection())
        except Exception: pass

    def save_entry():
        kid = _normalize_hex32(kid_v.get())
        key = _normalize_hex32(key_v.get())
        name = name_v.get().strip() or "manual"
        cat = (cat_v.get().strip() or "events").lower()
        if cat not in ("linear", "events"):
            cat = "events"
        if not _validate_hex32(kid):
            messagebox.showerror("KID no válido",
                                 "El KID debe tener 32 caracteres hexadecimales (0-9 a-f).",
                                 parent=root)
            return
        if key and not _validate_hex32(key):
            messagebox.showerror("KEY no válida",
                                 "La KEY debe tener 32 caracteres hexadecimales (0-9 a-f).",
                                 parent=root)
            return
        ext = _load_external_keys()
        entry = ext.get(kid) or {}
        if not isinstance(entry, dict):
            entry = {}
        if key:
            entry["key"] = key
            entry.pop("status", None)
        else:
            entry.setdefault("key", "")
            entry["status"] = "placeholder"
        entry["name"] = name[:120]
        if cat == "linear":
            entry.setdefault("country", entry.get("country") or "?")
        else:
            entry.pop("country", None)
            entry.pop("channels", None)
        if not entry.get("added"):
            entry["added"] = datetime.now().isoformat(timespec="seconds")
        ext[kid] = entry
        if _save_external_keys(ext):
            _invalidate_kid_index()
            status_lbl.config(
                text=f"✅ Guardado {kid[:12]}... ({'con KEY' if key else 'placeholder'})",
                fg="#3fb950")
            refresh()
            for i, r in enumerate(rows_cache):
                if r["kid"] == kid:
                    try: tree.selection_set(f"row_{i}")
                    except Exception: pass
                    break
        else:
            messagebox.showerror("Error", "Guardado fallido.", parent=root)

    def delete_entry():
        r = _get_selected()
        if not r:
            messagebox.showinfo("Sin selección", "Selecciona una fila.", parent=root)
            return
        kid = r["kid"]
        if any(k.lower() == kid for k, _ in STATIC_CLEARKEY_KEYS.values()):
            messagebox.showwarning(
                "Clave estática",
                "Esta clave está definida estáticamente en el código, no se puede eliminar desde aquí.",
                parent=root)
            return
        if not messagebox.askyesno("Confirmar",
                                   f"¿Eliminar el KID\n{kid}\ndel DB?", parent=root):
            return
        ext = _load_external_keys()
        ext.pop(kid, None)
        _save_external_keys(ext)
        _invalidate_kid_index()
        refresh(); clear_fields()
        status_lbl.config(text=f"🗑 Eliminado {kid[:12]}...", fg="#f85149")

    def paste_from_clipboard():
        try:
            cb = root.clipboard_get()
        except Exception:
            cb = ""
        if not cb:
            messagebox.showinfo("Portapapeles vacío", "Ningún texto en el portapapeles.", parent=root)
            return
        cb = cb.strip()
        try:
            obj = json.loads(cb)
            keys = obj.get("keys") if isinstance(obj, dict) else None
            if isinstance(keys, list) and keys:
                k0 = keys[0]
                kb = k0.get("kid") or k0.get("KID")
                kv = k0.get("k") or k0.get("K") or k0.get("key") or k0.get("KEY")
                kid_h = _b64_to_hex(kb) if kb else None
                key_h = _b64_to_hex(kv) if kv else None
                if kid_h: kid_v.set(kid_h)
                if key_h: key_v.set(key_h)
                status_lbl.config(
                    text="✅ Extraído JSON ClearKey del portapapeles.",
                    fg="#3fb950")
                return
        except Exception:
            pass
        found = re.findall(r"[0-9a-fA-F]{32}|[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}", cb)
        if len(found) >= 2:
            kid_v.set(_normalize_hex32(found[0]))
            key_v.set(_normalize_hex32(found[1]))
            status_lbl.config(text="✅ Extraído KID + KEY del portapapeles.",
                              fg="#3fb950")
        elif len(found) == 1:
            if not kid_v.get():
                kid_v.set(_normalize_hex32(found[0]))
            else:
                key_v.set(_normalize_hex32(found[0]))
            status_lbl.config(text="✅ Un solo valor pegado.",
                              fg="#3fb950")
        else:
            status_lbl.config(
                text="⚠️ No reconocido. Pega manualmente KID y KEY.",
                fg="#d29922")

    def import_from_har():
        path = filedialog.askopenfilename(
            title="Abrir HAR para auto-import KID/KEY",
            filetypes=[("HAR", "*.har"), ("Todos", "*.*")])
        if not path:
            return
        try:
            stats = auto_import_har_to_db(path, log=print, verbose=False)
        except Exception as e:
            messagebox.showerror("Error", str(e), parent=root)
            return
        refresh()
        msg = (f"✅ Import HAR completado\n\n"
               f"• Pares COMPLETOS añadidos:   {stats['added']}\n"
               f"• Pares actualizados:         {stats['updated']}\n"
               f"• Placeholder sin KEY:        {stats['placeholder']}\n\n"
               f"Total de entradas procesadas: {stats['total']}")
        messagebox.showinfo("Import HAR", msg, parent=root)
        status_lbl.config(
            text=f"📥 Import: +{stats['added']} completos, "
                 f"~{stats['updated']} actualizados, +{stats['placeholder']} placeholder",
            fg="#58a6ff")

    def import_external_json_gui():
        path = filedialog.askopenfilename(
            title="Importar JSON claves externas (external_keys_export.json)",
            filetypes=[("JSON", "*.json"), ("Todos", "*.*")])
        if not path:
            return
        try:
            stats = import_external_json(path)
        except Exception as e:
            messagebox.showerror("Error", str(e), parent=root)
            return
        refresh()
        msg = (f"✅ Import JSON completado\n\n"
               f"📄 Archivo: {os.path.basename(path)}\n\n"
               f"• Nuevos pares completos:    {stats['added']}\n"
               f"• Pares actualizados:        {stats['updated']}\n"
               f"• Placeholder añadidos:      {stats['placeholder']}\n"
               f"• Ya presentes (sin cambios): {stats['already']}\n"
               f"• Estáticos (skip):          {stats['static_skip']}\n"
               f"• No válidos (skip):         {stats['invalid']}\n\n"
               f"Total de entradas en el archivo: {stats['total']}")
        messagebox.showinfo("Import JSON", msg, parent=root)
        status_lbl.config(
            text=f"📥 JSON: +{stats['added']} nuevos, ~{stats['updated']} act., "
                 f"+{stats['placeholder']} placeholder",
            fg="#22c55e")

    def key_hunter_selected():
        r = _get_selected()
        if not r:
            messagebox.showinfo("Sin selección",
                "Selecciona un KID sin KEY.", parent=root)
            return
        kid = r["kid"]
        if r["key"]:
            messagebox.showinfo("Ya completo",
                f"El KID {kid[:12]}… ya tiene una KEY.", parent=root)
            return
        la_url = simpledialog.askstring(
            "LaUrl license server",
            "Pega la 'LaUrl' del canal (de la respuesta API Playback):",
            parent=root)
        if not la_url:
            return

        def _run():
            key = key_hunter_request_license(
                kid, la_url.strip(), _get_token(),
                verbose=True
            )
            def _done():
                if key:
                    ext = _load_external_keys()
                    entry = ext.get(kid) or {}
                    if not isinstance(entry, dict):
                        entry = {}
                    entry["key"] = key
                    entry.pop("status", None)
                    entry.setdefault("name", r["name"])
                    entry.setdefault("added", datetime.now().isoformat(timespec="seconds"))
                    ext[kid] = entry
                    _save_external_keys(ext)
                    _invalidate_kid_index()
                    refresh()
                    messagebox.showinfo("✅ KEY encontrada",
                        f"KEY para {kid[:12]}…:\n{key}", parent=root)
                else:
                    messagebox.showerror("❌ Fallido",
                        "KEY Hunter no encontró la KEY.\n"
                        "Revisa la consola para más detalles.", parent=root)
            if _widget_alive(root):
                root.after(0, _done)

        threading.Thread(target=_run, daemon=True).start()

    bf = tk.Frame(root, bg="#0d1117"); bf.pack(fill="x", padx=12, pady=(4, 10))

    def _btn(text, cmd, color):
        b = tk.Button(bf, text=text, command=cmd, bg="#161b22", fg=color,
                      activebackground=color, activeforeground="#0d1117",
                      font=("Segoe UI", 10, "bold"), relief="flat",
                      padx=14, pady=6, cursor="hand2")
        b.pack(side="left", padx=4)
        return b

    _btn("💾 Guardar", save_entry, "#3fb950")
    _btn("🗑 Eliminar", delete_entry, "#f85149")
    _btn("📋 Pegar portapapeles", paste_from_clipboard, "#58a6ff")
    _btn("📥 Importar HAR (KID+KEY)", import_from_har, "#a78bfa")
    _btn("📦 Importar JSON Externo", import_external_json_gui, "#22c55e")
    _btn("🔐 KEY Hunter sobre seleccionado", key_hunter_selected, "#ffaa00")
    _btn("🆕 Nuevo", clear_fields, "#d29922")
    _btn("🔄 Recargar", refresh, "#79c0ff")
    _btn("Cerrar", root.destroy, "#8b949e")

    refresh()

    if standalone:
        root.mainloop()

def _process_pending_events(pin_arg):
    if not pending_events_lock.acquire(blocking=False):
        print("⏳ Verificación de pending en curso en otro lugar, salto")
        return []
    try:
        pending = load_pending_events()
        if not pending: return []
        lead_sec = max(0, config.get("pending_lead_minutes", 5)) * 60
        now_ts = datetime.now(timezone.utc).timestamp()
        due = []; not_due = []
        for ev in pending:
            start_ts = _pending_event_start_ts(ev)
            if start_ts is None or now_ts >= (start_ts - lead_sec):
                due.append(ev)
            else:
                not_due.append(ev)
        if not due: return []
        console_lock.acquire()
        try:
            print(f"\n⏳ Verificando {len(due)}/{len(pending)} pending (lead {lead_sec // 60}min)...")
            ready = []; still = []
            for ev in due:
                aid = ev.get('AssetId') or ''; title = ev.get('Title') or '?'
                if not aid: continue
                try:
                    r = get_single(_get_token(), aid, pin_arg)
                    mu = r[0] if r else None
                    if mu:
                        ready_tile = dict(ev)
                        ready_tile['Type'] = ev.get('Type') or 'UpComing'
                        ready.append(ready_tile)
                        print(f"   ✅ {title}")
                    else:
                        ev['LastAttempt'] = datetime.now().isoformat(timespec="seconds")
                        still.append(ev); print(f"   ⏳ {title}")
                except Exception:
                    ev['LastAttempt'] = datetime.now().isoformat(timespec="seconds")
                    still.append(ev); print(f"   ⏳ {title}")
            save_pending_events(still + not_due)
        finally:
            console_lock.release()
        return ready
    finally:
        pending_events_lock.release()

events_scheduler_running = False
events_scheduler_thread = None
events_scheduler_next_update = None
events_scheduler_lock = threading.Lock()

def format_countdown(seconds):
    if seconds <= 0: return "En curso..."
    return f"{seconds // 60:02d}:{seconds % 60:02d}"

def _parse_hhmm(s):
    try:
        h, m = s.strip().split(":"); h, m = int(h), int(m)
        if 0 <= h <= 23 and 0 <= m <= 59: return h, m
    except Exception: pass
    return None

def _next_fixed_time(times_list):
    now = datetime.now(); today = now.date(); c = []
    for t in times_list or []:
        hm = _parse_hhmm(t)
        if not hm: continue
        target = datetime.combine(today, dt_time(hm[0], hm[1]))
        if target <= now: target += timedelta(days=1)
        c.append(target)
    return min(c) if c else None

def _current_fixed_time_key(times_list, tol=300):
    now = datetime.now(); today = now.date()
    for t in times_list or []:
        hm = _parse_hhmm(t)
        if not hm: continue
        target = datetime.combine(today, dt_time(hm[0], hm[1]))
        delta = (now - target).total_seconds()
        if 0 <= delta < tol: return target.strftime("%Y-%m-%d %H:%M")
    return None

def _run_events_scheduler_cycle():
    try:
        _load_token_safe(do_refresh_if_possible=True)
    except Exception as e:
        print(f"⚠️ refresh: {e}"); return
    if config.get("channels_regenerate_with_events", False):
        skip_regen = False
        try:
            last_run_str = _load_channel_snapshot().get("last_run", "")
            if last_run_str:
                last_run_dt = datetime.fromisoformat(last_run_str)
                if (datetime.now() - last_run_dt).total_seconds() < CHANNELS_REGEN_SKIP_WINDOW_SEC:
                    skip_regen = True
        except Exception:
            pass
        if not skip_regen:
            print("\n📺 Regeneración de canales (pre-eventos)...")
            try: _run_channels_scheduler_cycle()
            except Exception as e: print(f"❌ {e}")
    include_live = config.get("events_include_live", True)
    only_today = config.get("events_only_today", True)
    print("\n🔄 Ciclo EVENTOS...")
    try: events = get_scheduled_events(_get_token(), include_live=include_live, verbose=True)
    except Exception as e: print(f"❌ {e}"); events = []
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
    output_file = config.get("output_file_events", OUTPUT_FILE_EVENTS_DEFAULT)
    result = generate_m3u_from_events(events, output_file=output_file,
                                      auto_pending=True, retain_cache=True,
                                      use_ck_hunter=config.get("ck_hunter_enabled", True))

def events_scheduler_loop():
    global events_scheduler_running, events_scheduler_next_update
    mode = config.get("events_scheduler_mode", "interval")
    if mode == "fixed_times":
        times = config.get("events_fixed_times", [])
        print(f"▶️ Scheduler EVENTOS (horarios): {', '.join(times)}")
        last = None
        while events_scheduler_running:
            nd = _next_fixed_time(times)
            with events_scheduler_lock:
                events_scheduler_next_update = nd.timestamp() if nd else None
            key = _current_fixed_time_key(times, 300)
            if key and key != last:
                print(f"\n⏰ Horario eventos: {key[11:]}")
                try: _run_events_scheduler_cycle(); last = key
                except Exception as e: print(f"❌ {e}"); last = key
            time.sleep(1)
        print("⏹️ Scheduler EVENTOS detenido")
        return
    print(f"▶️ Scheduler EVENTOS (intervalo {config.get('events_scheduler_interval_minutes', 15)} min)")
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

pending_watcher_running = False
pending_watcher_thread = None

def pending_watcher_loop():
    global pending_watcher_running
    interval = max(5, config.get("pending_watcher_interval_sec", 30))
    print(f"▶️ Watcher PENDING (cada {interval}s)")
    while pending_watcher_running:
        try:
            if not load_pending_events():
                ready = []
            else:
                try: _load_token_safe(do_refresh_if_possible=True)
                except Exception as e: print(f"⚠️ refresh pending: {e}")
                ready = _process_pending_events(pin)
            if ready:
                output_file = config.get("output_file_events", OUTPUT_FILE_EVENTS_DEFAULT)
                generate_m3u_from_events(ready, output_file=output_file,
                                          auto_pending=True, retain_cache=True,
                                          use_ck_hunter=config.get("ck_hunter_enabled", True))
        except Exception as e:
            print(f"❌ Watcher pending: {e}")
        for _ in range(interval):
            if not pending_watcher_running: break
            time.sleep(1)
    print("⏹️ Watcher PENDING detenido")

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

channels_scheduler_running = False
channels_scheduler_thread = None
channels_scheduler_next_update = None
channels_scheduler_lock = threading.Lock()

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
            "channels": {c.get('AssetId', ''): c.get('Title', '')
                         for c in channels if c.get('AssetId')}}
    try:
        with open(CHANNEL_SNAPSHOT_FILE, "w", encoding="utf-8") as f:
            json.dump(snap, f, ensure_ascii=False, indent=2)
    except Exception: pass

def _diff_channels(new_channels):
    old = _load_channel_snapshot().get("channels", {})
    new = {c.get('AssetId', ''): c.get('Title', '') for c in new_channels if c.get('AssetId')}
    added = {k: v for k, v in new.items() if k not in old}
    removed = {k: v for k, v in old.items() if k not in new}
    if added:
        print(f"  🆕 {len(added)} canales NUEVOS")
    if removed:
        print(f"  🔻 {len(removed)} canales DESAPARECIDOS")

def _resolve_channels_selection(all_channels):
    if not all_channels: return []
    sel = list(config.get("selected_channels", []) or [])
    if not sel: return all_channels
    snapshot_ids = set(_load_channel_snapshot().get("channels", {}).keys())
    all_by_id = {c.get('AssetId'): c for c in all_channels if c.get('AssetId')}
    added = [aid for aid in all_by_id if aid not in sel and aid not in snapshot_ids]
    if added:
        print(f"\n🆕 {len(added)} canales nuevos → auto-seleccionados")
        sel.extend(added)
        config["selected_channels"] = sel
        save_config()
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
    output_file = config.get("output_file_channels", OUTPUT_FILE_CHANNELS_DEFAULT)
    ok = generate_dazn_playlist(output_file=output_file,
                                 selected_channels=selected)

def channels_scheduler_loop():
    global channels_scheduler_running, channels_scheduler_next_update
    mode = config.get("channels_scheduler_mode", "interval")
    if mode == "fixed_times":
        times = config.get("channels_fixed_times", [])
        print(f"▶️ Scheduler CANALES (horarios): {', '.join(times)}")
        last = None
        while channels_scheduler_running:
            nd = _next_fixed_time(times)
            with channels_scheduler_lock:
                channels_scheduler_next_update = nd.timestamp() if nd else None
            key = _current_fixed_time_key(times, 300)
            if key and key != last:
                try: _run_channels_scheduler_cycle(); last = key
                except Exception as e: print(f"❌ {e}"); last = key
            time.sleep(1)
        return
    print(f"▶️ Scheduler CANALES (intervalo {config.get('channels_scheduler_interval_minutes', 60)} min)")
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

def get_selected_channels_from_config():
    sel = config.get("selected_channels", [])
    if not sel: return None
    all_ch = get_channels(_get_token())
    if not all_ch: return None
    return _resolve_channels_selection(all_ch)

# ==============================================================
# LOGIN / TOKEN
# ==============================================================
def do_login(username, password):
    headers = {
        'accept': '*/*', 'content-type': 'application/json',
        'origin': 'https://www.dazn.com', 'referer': 'https://www.dazn.com/',
        'user-agent': USER_AGENT,
    }
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
    except Exception: return "5.3.8-ES"

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
            except Exception:
                pass
            try: VERSION = get_version()
            except Exception: pass
            print(f"✅ Token cargado del perfil '{pname}' ({pinfo.get('label','')}) — país: {pinfo.get('country','?')}")
            return tok
        else:
            print(f"⚠️ Perfil '{pname}' tiene token inválido, lo ignoro")
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
    print("🔑 Ningún token válido → captura desde el navegador")
    input("   Pulsa ENTER para abrir el navegador...")
    tok = capture_and_save_token()
    if tok:
        try: VERSION = get_version()
        except Exception: pass
        return tok
    print("⚠️ Fallback: login manual")
    username = input('\nEmail: ')
    password = pwinput.pwinput()
    t = do_login(username, password)
    if t:
        with open("token.txt", 'w', encoding='utf-8') as f:
            f.write(t)
        _set_token(t)
        VERSION = get_version()
        return t
    print("❌ Login fallido."); sys.exit(1)

# ==============================================================
# GUI
# ==============================================================
GUI_BG = "#0d1117"; GUI_BG2 = "#161b22"; GUI_FG = "#c9d1d9"
GUI_ACCENT = "#58a6ff"; GUI_GREEN = "#3fb950"; GUI_RED = "#f85149"
GUI_YELLOW = "#d29922"; GUI_MAGENTA = "#bc8cff"; GUI_CYAN = "#79c0ff"
_ANSI_RE = re.compile(r'\x1b\[[0-9;]*m')
_gui_instance = None

class _HarAnalyzer:
    def __init__(self, path, log):
        self.path = Path(path); self.log = log
        self.entries = []; self.hosts = {}
        self.dazn_urls = []; self.interesting = []
        self.stream_urls = []; self.hls_urls = []

    def load(self):
        size_mb = self.path.stat().st_size / 1024 / 1024
        self.log(f"📖 Cargando {self.path.name} ({size_mb:.2f} MB)")
        with open(self.path, "r", encoding="utf-8-sig") as f:
            data = json.load(f)
        self.entries = data.get("log", {}).get("entries", [])
        self.log(f"✅ {len(self.entries)} peticiones")

    def _is_dazn_stream(self, url):
        try:
            p = urlparse(url)
            return p.scheme.lower() == "https" and "indazn.com" in (p.hostname or "")
        except ValueError:
            return False

    def _extract_urls(self, text):
        if not text: return
        norm = text.replace(r"\/", "/").replace(r"\u0026", "&")
        pos = 0
        while True:
            start = norm.find("https://", pos)
            if start == -1: break
            end = start
            while (end < len(norm) and not norm[end].isspace()
                   and norm[end] not in "\"'<>()[]{}"):
                end += 1
            cand = norm[start:end].strip().rstrip(".,;:)]}'\"")
            if self._is_dazn_stream(cand) and cand not in self.stream_urls:
                self.stream_urls.append(cand)
            pos = end

    def _response_text(self, response):
        c = response.get("content", {})
        t = c.get("text") or ""
        if c.get("encoding") == "base64":
            try: return base64.b64decode(t).decode("utf-8", errors="replace")
            except (ValueError, TypeError): return ""
        return t

    def parse(self):
        for entry in self.entries:
            req = entry.get("request", {}); res = entry.get("response", {})
            url = req.get("url", ""); method = req.get("method", "GET")
            status = res.get("status", 0)
            content = res.get("content", {})
            mime = (content.get("mimeType") or "").lower()
            try: host = urlparse(url).netloc.lower()
            except ValueError: host = ""
            self.hosts[host] = self.hosts.get(host, 0) + 1
            if "dazn" in host or "indazn" in host:
                self.dazn_urls.append({"url": url, "method": method,
                                       "status": status, "mime": mime, "host": host})
            if any(w in url.lower() for w in ("playback", "manifest", "m3u8",
                                               "mpd", "stream", "media", "license", "drm")):
                self.interesting.append({"url": url, "method": method,
                                         "status": status, "mime": mime, "host": host})
            self._extract_urls(url)
            body = self._response_text(res)
            if body: self._extract_urls(body)
        self.stream_urls = sorted(set(self.stream_urls))
        self.log(f"🔎 {len(self.hosts)} hosts · {len(self.stream_urls)} streams")

class _HarInspectorWindow:
    def __init__(self, parent, log_callback):
        self.parent = parent; self.log_cb = log_callback
        self.analyzer = None
        self._last_ck_report = None
        self._build()

    def _build(self):
        self.win = tk.Toplevel(self.parent)
        self.win.title("🔬 HAR Stream Inspector + CK Hunter")
        self.win.geometry("1200x780")
        self.win.configure(bg="#0d1117")
        h = tk.Frame(self.win, bg="#1a1a2e", height=60); h.pack(fill="x")
        h.pack_propagate(False)
        tk.Label(h, text="🔬 HAR STREAM INSPECTOR + CK HUNTER", bg="#1a1a2e", fg="#00d4ff",
                 font=("Segoe UI", 16, "bold")).pack(side="left", padx=20, pady=15)
        bar = tk.Frame(self.win, bg="#0d1117"); bar.pack(fill="x", padx=10, pady=8)

        def _btn(text, cmd, color="#58a6ff"):
            b = tk.Button(bar, text=text, command=cmd, bg="#161b22", fg=color,
                          activebackground=color, activeforeground="#0d1117",
                          font=("Segoe UI", 10, "bold"), relief="flat",
                          padx=14, pady=8, cursor="hand2")
            b.pack(side="left", padx=3); return b

        _btn("📂 Abrir HAR", self._open_har, "#3fb950")
        _btn("💾 Guardar URL", self._save_all, "#58a6ff")
        _btn("🎯 Analizar vs DB", self._ck_analyze, "#ffaa00")
        _btn("📥 Exportar KID nuevos", self._ck_export_new, "#a78bfa")
        _btn("➕ Añadir placeholder", self._ck_add_placeholders, "#22c55e")
        _btn("🔑 Gestor KID/KEY", self._open_kid_manager, "#58a6ff")
        _btn("❌ Cerrar", self.win.destroy, "#f85149")
        self.status = tk.StringVar(value="Listo.")
        tk.Label(bar, textvariable=self.status, bg="#0d1117", fg="#c9d1d9",
                 font=("Consolas", 9)).pack(side="right", padx=10)
        nb = ttk.Notebook(self.win)
        nb.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        def _tab(title):
            f = ttk.Frame(nb); nb.add(f, text=title)
            t = scrolledtext.ScrolledText(f, wrap=tk.NONE, font=("Consolas", 9),
                                          bg="#010409", fg="#c9d1d9")
            t.pack(fill="both", expand=True); return t

        self.tab_streams = _tab("📡 Streams")
        self.tab_diag = _tab("🔎 Diagnóstico")
        self.tab_dazn = _tab("🌐 URL DAZN")
        self.tab_ck = _tab("🎯 CK Hunter")

    def _open_kid_manager(self):
        try:
            open_kid_key_manager_tkinter(parent=self.win)
        except Exception as e:
            messagebox.showerror("Error", str(e), parent=self.win)

    def _open_har(self):
        path = filedialog.askopenfilename(
            title="Abrir HAR", filetypes=[("HAR", "*.har"), ("Todos", "*.*")])
        if not path: return
        try:
            self.analyzer = _HarAnalyzer(path, self._log)
            self.analyzer.load(); self.analyzer.parse()
            self._render()
            self.status.set(f"{len(self.analyzer.stream_urls)} streams · "
                            f"{len(self.analyzer.entries)} peticiones")
        except Exception as e:
            messagebox.showerror("Error", str(e), parent=self.win)

    def _render(self):
        a = self.analyzer
        self.tab_streams.delete("1.0", tk.END)
        self.tab_streams.insert(tk.END, "URL streams DAZN\n" + "=" * 76 + "\n\n")
        for i, u in enumerate(a.stream_urls, 1):
            self.tab_streams.insert(tk.END, f"[{i}] {u}\n\n")
        self.tab_diag.delete("1.0", tk.END)
        self.tab_diag.insert(tk.END, "─── HOSTS ───\n")
        for host, cnt in sorted(a.hosts.items(), key=lambda x: -x[1]):
            self.tab_diag.insert(tk.END, f"{cnt:5d}  {host or '(local)'}\n")
        self.tab_dazn.delete("1.0", tk.END)
        self.tab_dazn.insert(tk.END, "URL DAZN\n" + "=" * 76 + "\n\n")
        seen = set()
        for item in a.dazn_urls:
            key = (item["method"], item["url"].split("?", 1)[0])
            if key in seen: continue
            seen.add(key)
            self.tab_dazn.insert(tk.END,
                f"[{item['status']}] {item['method']:6s} {item['url']}\n\n")

    def _save_all(self):
        if not self.analyzer or not self.analyzer.stream_urls:
            messagebox.showwarning("Vacío", "Ninguna URL.", parent=self.win); return
        path = filedialog.asksaveasfilename(
            title="Guardar URL", defaultextension=".txt",
            initialfile="stream_urls.txt",
            filetypes=[("Texto", "*.txt"), ("Todos", "*.*")])
        if not path: return
        Path(path).write_text("\n".join(self.analyzer.stream_urls) + "\n", encoding="utf-8")
        messagebox.showinfo("OK", f"Guardados {len(self.analyzer.stream_urls)} URL.", parent=self.win)

    def _ck_analyze(self):
        if not self.analyzer or not getattr(self.analyzer, "path", None):
            messagebox.showwarning("Sin HAR", "Abre primero un archivo HAR.", parent=self.win)
            return
        try:
            report = _har_analyze_vs_db(self.analyzer.path)
        except Exception as e:
            messagebox.showerror("Error", str(e), parent=self.win)
            return
        t = self.tab_ck
        t.delete("1.0", tk.END)
        t.insert(tk.END, "🎯 CK HUNTER — ANÁLISIS HAR vs DB\n" + "=" * 76 + "\n\n")
        t.insert(tk.END, f"📡 MPD encontrados:          {report['total_mpds']}\n")
        t.insert(tk.END, f"🔑 KID únicos encontrados:   {report['kids_found']}\n")
        t.insert(tk.END, f"🟢 Ya en DB (external):      {len(report['in_db'])}\n")
        t.insert(tk.END, f"🔐 Estáticos (código):       {len(report['static'])}\n")
        t.insert(tk.END, f"🔴 KID NUEVOS huérfanos:     {len(report['new'])}\n")
        t.insert(tk.END, f"⚪ MPD sin KID:              {len(report['no_kid'])}\n")
        t.insert(tk.END, f"🔑 Licencias ClearKey en HAR: {report.get('total_license_keys', 0)}\n")
        t.insert(tk.END, f"🟢 Pares licencia ya conocidos: {len(report.get('license_known') or [])}\n")
        t.insert(tk.END, f"💚 Pares licencia NUEVOS:    {len(report.get('license_new') or [])}\n")
        self._last_ck_report = report

    def _ck_export_new(self):
        report = getattr(self, "_last_ck_report", None)
        if not report:
            messagebox.showinfo("Analiza primero", "Haz clic en '🎯 Analizar vs DB' primero.", parent=self.win)
            return
        new = report.get("new") or []
        if not new:
            messagebox.showinfo("Sin KID nuevos", "Todos los KID ya están en el DB.", parent=self.win)
            return
        path = filedialog.asksaveasfilename(
            title="Exportar KID nuevos",
            defaultextension=".json",
            initialfile="har_new_kids.json",
            filetypes=[("JSON", "*.json"), ("Todos", "*.*")])
        if not path: return
        out = {}
        for item in new:
            kid = item.get("kid")
            if not kid: continue
            out[kid] = {
                "key": "",
                "name": "HAR: " + (item.get("url") or "")[:80],
                "added": datetime.now().isoformat(timespec="seconds"),
                "status": "placeholder",
            }
        try:
            Path(path).write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
            messagebox.showinfo("OK", f"Exportados {len(out)} KID nuevos.", parent=self.win)
        except Exception as e:
            messagebox.showerror("Error", str(e), parent=self.win)

    def _ck_add_placeholders(self):
        report = getattr(self, "_last_ck_report", None)
        if not report:
            messagebox.showinfo("Analiza primero", "Haz clic en '🎯 Analizar vs DB' primero.", parent=self.win)
            return
        complete = (report.get("license_new") or [])
        orphans = (report.get("new") or [])
        if not complete and not orphans:
            messagebox.showinfo("Nada que añadir", "Todos los KID ya están en el DB.", parent=self.win)
            return
        ext = _load_external_keys()
        added_c, updated_c, added_p = 0, 0, 0
        for c in complete:
            kid, key = c["kid"], c["key"]
            cur = ext.get(kid) or {}
            if not isinstance(cur, dict): cur = {}
            if cur.get("key") == key: continue
            existed = kid in ext
            cur["key"] = key
            cur.pop("status", None)
            cur.setdefault("name", (c.get("url") or "licencia")[:80])
            cur.setdefault("added", datetime.now().isoformat(timespec="seconds"))
            ext[kid] = cur
            if existed: updated_c += 1
            else:       added_c += 1
        for o in orphans:
            k = o.get("kid")
            if not k or k in ext: continue
            ext[k] = {
                "key": "",
                "name": (o.get("url") or "HAR placeholder")[:80],
                "added": datetime.now().isoformat(timespec="seconds"),
                "status": "placeholder",
            }
            added_p += 1
        _save_external_keys(ext)
        _invalidate_kid_index()
        messagebox.showinfo(
            "Hecho",
            f"✅ Pares completos añadidos:   {added_c}\n"
            f"✅ Pares completos actualizados: {updated_c}\n"
            f"📌 Placeholder añadidos:       {added_p}",
            parent=self.win)

    def _log(self, msg):
        try: self.log_cb(str(msg))
        except Exception: print(msg)

class DaznGUI:
    def __init__(self, root):
        self.root = root; self.tk = tk; self.ttk = ttk
        self.scrolledtext = scrolledtext
        self._build_main()
        self._update_status()

    def _build_main(self):
        tk = self.tk
        self.root.title("DAZN EXTRACTOR v5.3.8-ES — ATOMIC + CK/KEY/WVD HUNTER + HLS + PERFILES + AUTO-HEALING")
        self.root.geometry("1240x920")
        self.root.configure(bg=GUI_BG); self.root.minsize(1100, 800)
        header = tk.Frame(self.root, bg=GUI_BG2, height=70)
        header.pack(fill="x", side="top"); header.pack_propagate(False)
        tk.Label(header, text="🎯 DAZN EXTRACTOR", bg=GUI_BG2, fg=GUI_ACCENT,
                 font=("Segoe UI", 20, "bold")).pack(side="left", padx=20, pady=10)
        tk.Label(header, text="v5.3.8-ES — CK + KEY + WVD HUNTER + HLS + AUTO-HEALING",
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
        # Selector de navegador (auto/chrome/edge)
        tk.Label(r0, text="🌐 Navegador:", bg=GUI_BG, fg=GUI_CYAN,
                 font=("Segoe UI", 10, "bold")).pack(side="left", padx=(20, 4))
        self._browser_var = tk.StringVar(value=config.get("browser_type", "auto"))
        cb = ttk.Combobox(r0, textvariable=self._browser_var, width=10,
                          values=["auto", "chrome", "edge"], state="readonly")
        cb.pack(side="left", padx=4)
        cb.bind("<<ComboboxSelected>>", self.act_set_browser)

        r1 = row("📺 CANALES", GUI_GREEN)
        self._btn(r1, "▶ Generar M3U", self.act_generate_channels, GUI_GREEN)
        self._btn(r1, "📺 Seleccionar", self.act_select_channels, GUI_GREEN)
        self._btn(r1, "🗑 Reset", self.act_reset_channels, GUI_RED)
        self._hls_var = tk.IntVar(value=1 if config.get("hls_output_enabled", True) else 0)
        tk.Checkbutton(r1, text="📻 HLS (AppleCoreMedia)",
                       variable=self._hls_var, command=self.act_toggle_hls,
                       bg=GUI_BG, fg=GUI_CYAN, selectcolor=GUI_BG,
                       activebackground=GUI_BG, activeforeground=GUI_CYAN,
                       font=("Segoe UI", 10, "bold")).pack(side="left", padx=10)
        r2 = row("📅 EVENTOS", GUI_MAGENTA)
        self._btn(r2, "👁 Ver", self.act_view_events, GUI_MAGENTA)
        self._btn(r2, "🎬 Generar M3U", self.act_generate_events, GUI_MAGENTA)
        self._btn(r2, "⏳ Pending", self.act_pending, GUI_MAGENTA)
        r3 = row("⏰ SCH. EVENTOS", GUI_ACCENT)
        self._btn(r3, "▶ Iniciar", self.act_start_events, GUI_GREEN)
        self._btn(r3, "⏹ Detener", self.act_stop_events, GUI_RED)
        r4 = row("📡 SCH. CANALES", GUI_CYAN)
        self._btn(r4, "▶ Iniciar", self.act_start_channels, GUI_GREEN)
        self._btn(r4, "⏹ Detener", self.act_stop_channels, GUI_RED)
        r5 = row("🔬 HERRAMIENTAS", GUI_MAGENTA)
        self._btn(r5, "🔬 HAR Inspector", self.act_open_har_inspector, GUI_MAGENTA)
        self._btn(r5, "🎯 CK Hunter", self.act_ck_hunter, GUI_YELLOW)
        self._btn(r5, "🔑 Gestor KID/KEY", self.act_kid_key_manager, GUI_CYAN)
        self._btn(r5, "🎬 WVD", self.act_wvd_manager, GUI_RED)
        self._btn(r5, "🔬 Dump Playback", self.act_dump_playback, GUI_YELLOW)
        self._btn(r5, "📥 Importar JSON Externo", self.act_import_external_json, GUI_GREEN)
        self._btn(r5, "🩹 Estáticas deprecadas", self.act_deprecated_statics, GUI_YELLOW)
        r6 = row("⚙️ CONFIG.", GUI_YELLOW)
        self._btn(r6, "👤 Perfiles", self.act_profiles, GUI_CYAN)
        self._btn(r6, "📼 HAR Auto", self.act_toggle_har, GUI_MAGENTA)
        self._btn(r6, "⏱ Grace", self.act_set_grace, GUI_MAGENTA)
        self._btn(r6, "ℹ Estado", self.act_status, GUI_CYAN)
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

    def _new_dialog(self, title, w=700, h=600):
        tk = self.tk
        d = tk.Toplevel(self.root); d.title(title); d.geometry(f"{w}x{h}")
        d.configure(bg=GUI_BG); d.transient(self.root); return d

    def _styled_button(self, parent, text, cmd, color=GUI_ACCENT, side="left"):
        tk = self.tk
        b = tk.Button(parent, text=text, command=cmd, bg=GUI_BG2, fg=color,
                      activebackground=color, activeforeground=GUI_BG,
                      font=("Segoe UI", 10, "bold"), relief="flat", borderwidth=1,
                      padx=14, pady=6, cursor="hand2")
        b.pack(side=side, padx=5, pady=4); return b

    def _update_status(self):
        try:
            parts = []
            if events_scheduler_running: parts.append("⏰ EVENTOS")
            if channels_scheduler_running: parts.append("📡 CANALES")
            st = ck_hunter_stats()
            pname, _ = get_active_profile()
            har_state = "ON" if config.get("har_recording_enabled", True) else "OFF"
            grace = config.get("har_grace_seconds", 45)
            dep = len(_load_deprecated_statics())
            kh_state = "ON" if config.get("key_hunter_enabled", True) else "OFF"
            hls_state = "ON" if config.get("hls_output_enabled", True) else "OFF"
            wvd_state = "ON" if config.get("wvd_enabled", True) else "OFF"
            btype = config.get("browser_type", "auto")
            if _widget_alive(self.status_pill):
                self.status_pill.configure(
                    text=" | ".join(parts) if parts else "⏹ DETENIDO",
                    fg=GUI_GREEN if parts else GUI_RED)
                self.status_bar.configure(
                    text=f"👤 {pname or 'token.txt'} | "
                         f"Navegador: {btype} | "
                         f"Eventos: {'ON' if events_scheduler_running else 'off'} | "
                         f"Canales: {'ON' if channels_scheduler_running else 'off'} | "
                         f"HLS: {hls_state} | "
                         f"WVD: {wvd_state} | "
                         f"HAR: {har_state} ({grace}s) | "
                         f"CK: {st['total_indexed']} KID | KH: {kh_state} | "
                         f"🩹 Dep: {dep} | "
                         f"Pending: {len(load_pending_events())}")
        except Exception: pass
        try:
            if _widget_alive(self.root):
                self.root.after(1000, self._update_status)
        except Exception: pass

    def act_set_browser(self, *_):
        val = (self._browser_var.get() or "auto").lower()
        if val not in ("auto", "chrome", "edge"):
            val = "auto"
        config["browser_type"] = val
        save_config()
        self.log(f"🌐 Navegador configurado: {val}", "ok")

    def act_capture_token(self):
        self.clear_log(); self.log("🔑 Capturando token...", "accent")
        self.run_async(lambda: capture_and_save_token(log=self.log))

    def act_toggle_har(self):
        cur = config.get("har_recording_enabled", True)
        config["har_recording_enabled"] = not cur
        save_config()
        state = "ON" if config["har_recording_enabled"] else "OFF"
        self.log(f"📼 Grabación HAR automática: {state}",
                 "ok" if config["har_recording_enabled"] else "warn")

    def act_toggle_hls(self):
        new_state = bool(self._hls_var.get())
        config["hls_output_enabled"] = new_state
        save_config()
        state = "ON" if new_state else "OFF"
        self.log(f"📻 Salida HLS (AppleCoreMedia): {state} "
                 f"→ {config.get('output_file_hls', OUTPUT_FILE_HLS_DEFAULT)}",
                 "ok" if new_state else "warn")

    def act_wvd_manager(self):
        tk = self.tk
        d = self._new_dialog("🎬 Widevine WVD", 720, 520)
        tk.Label(d, text="🎬 WIDEVINE CDM (WVD)", bg=GUI_BG, fg=GUI_RED,
                 font=("Segoe UI", 14, "bold")).pack(pady=12)
        info = tk.Label(d, text="", bg=GUI_BG, fg="#8b949e",
                        font=("Consolas", 9), justify="left", anchor="w")
        info.pack(padx=20, pady=4, fill="x")

        def refresh():
            ok_pw = _pywidevine_available()
            path = _wvd_path()
            exists = os.path.exists(path)
            size = f"{os.path.getsize(path)/1024:.1f} KB" if exists else "—"
            info.config(text=(
                f"pywidevine instalado   : {'✅' if ok_pw else '❌ (pip install pywidevine)'}\n"
                f"Archivo WVD            : {path}\n"
                f"Existe                 : {'✅' if exists else '❌'}\n"
                f"Tamaño                 : {size}\n"
                f"CDM en caché           : {'✅' if _wvd_cdm is not None else '—'}\n"
                f"Activo en ciclos       : {'✅' if config.get('wvd_enabled', True) else '❌'}"
            ))
        refresh()
        tk.Label(d,
                 text="⚠️ El WVD se usa SOLO como último recurso:\n"
                      "   ClearKey estáticas → API ClearKey → CK Hunter → KEY Hunter → WVD Widevine\n"
                      "   Si falta pywidevine o el WVD, todo lo demás funciona normalmente.",
                 bg=GUI_BG, fg=GUI_YELLOW,
                 font=("Segoe UI", 9, "italic"), justify="left").pack(padx=20, pady=10)
        var_on = tk.IntVar(value=1 if config.get("wvd_enabled", True) else 0)
        tk.Checkbutton(d, text="Habilitar WVD Hunter en los próximos ciclos",
                       variable=var_on, bg=GUI_BG, fg=GUI_FG,
                       selectcolor=GUI_BG, activebackground=GUI_BG,
                       activeforeground=GUI_ACCENT,
                       font=("Segoe UI", 10)).pack(pady=6)
        bf = tk.Frame(d, bg=GUI_BG); bf.pack(fill="x", padx=20, pady=10)

        def pick_wvd():
            path = filedialog.askopenfilename(
                title="Selecciona archivo WVD",
                filetypes=[("Widevine Device", "*.wvd"), ("Todos", "*.*")])
            if not path: return
            config["wvd_file"] = path
            save_config()
            _invalidate_wvd_cache()
            self.log(f"✅ WVD configurado: {path}", "ok")
            refresh()

        def test_load():
            _invalidate_wvd_cache()
            cdm = _load_wvd_cdm(verbose=True)
            if cdm: self.log("✅ WVD cargado correctamente", "ok")
            else: self.log("❌ Fallo al cargar WVD (ver consola)", "err")
            refresh()

        def save_toggle():
            config["wvd_enabled"] = bool(var_on.get())
            save_config()
            self.log(f"✅ WVD Hunter {'ON' if var_on.get() else 'OFF'}", "ok")
            refresh()

        self._styled_button(bf, "📂 Elegir WVD", pick_wvd, GUI_GREEN)
        self._styled_button(bf, "🧪 Probar carga", test_load, GUI_CYAN)
        self._styled_button(bf, "💾 Guardar estado", save_toggle, GUI_ACCENT)
        self._styled_button(bf, "Cerrar", d.destroy, GUI_FG, side="right")

    def act_set_grace(self):
        tk = self.tk
        d = self._new_dialog("Grace period HAR", 400, 220)
        tk.Label(d, text="Segundos de navegación tras capturar el token:",
                 bg=GUI_BG, fg=GUI_FG, font=("Segoe UI", 10)).pack(pady=12)
        v = tk.StringVar(value=str(config.get("har_grace_seconds", 45)))
        tk.Entry(d, textvariable=v, width=10, font=("Consolas", 14),
                 justify="center").pack(pady=8)
        tk.Label(d, text="(0 = cerrar de inmediato, 120 = 2 minutos)",
                 bg=GUI_BG, fg="#8b949e", font=("Segoe UI", 8, "italic")).pack()

        def save_grace():
            try:
                val = max(0, int(v.get()))
            except Exception:
                messagebox.showerror("Error", "Número no válido", parent=d); return
            config["har_grace_seconds"] = val
            save_config()
            self.log(f"⏱ Grace period: {val} segundos", "ok")
            d.destroy()
        bf = tk.Frame(d, bg=GUI_BG); bf.pack(pady=10)
        self._styled_button(bf, "💾 Guardar", save_grace, GUI_GREEN)
        self._styled_button(bf, "Cancelar", d.destroy, GUI_FG)

    def act_dump_playback(self):
        tk = self.tk
        d = self._new_dialog("🔬 Dump Playback API", 900, 650)
        tk.Label(d, text="🔬 Dump completo de la respuesta API Playback",
                 bg=GUI_BG, fg=GUI_YELLOW,
                 font=("Segoe UI", 13, "bold")).pack(pady=10)
        tk.Label(d, text="Pega el AssetId del canal/evento que quieras inspeccionar:",
                 bg=GUI_BG, fg="#8b949e",
                 font=("Segoe UI", 9, "italic")).pack()
        v = tk.StringVar()
        tk.Entry(d, textvariable=v, width=60, font=("Consolas", 11)).pack(pady=8)
        out = tk.Text(d, bg="#010409", fg="#c9d1d9", font=("Consolas", 9),
                      wrap="word", relief="flat", borderwidth=0)
        out.pack(fill="both", expand=True, padx=10, pady=10)

        def run():
            aid = v.get().strip()
            if not aid: return
            try:
                _load_token_safe(do_refresh_if_possible=True)
            except Exception as e:
                out.insert("end", f"❌ {e}\n"); return
            try:
                dec = jwt.decode(_get_token(), options={"verify_signature": False})
                h = {'accept': '*/*', 'authorization': 'Bearer ' + _get_token(),
                     'origin': 'https://www.dazn.com', 'referer': 'https://www.dazn.com/',
                     'user-agent': USER_AGENT, 'x-dazn-device': dec['deviceId'],
                     'x-correlation-id': str(uuid.uuid4())}
                p = {'AppVersion': VERSION, 'DrmType': 'WIDEVINE',
                     'Format': 'MPEG-DASH', 'PlayerId': '@dazn/peng-html5-core/web/web',
                     'Platform': 'web', 'LanguageCode': 'en', 'Model': 'unknown',
                     'Secure': 'true', 'Manufacturer': 'microsoft',
                     'PlayReadyInitiator': 'false', 'Capabilities': 'mta',
                     'AssetId': aid, 'MtaLanguageCode': '', 'token': _get_token()}
                r = requests.get('https://api.playback.indazn.com/v5/Playback',
                                 params=p, headers=h, proxies=proxies,
                                 impersonate='chrome', timeout=30)
                data = r.json()
                out.delete("1.0", "end")
                pds = data.get("PlaybackDetails") or []
                if pds:
                    out.insert("end", f"═══ CDN DISPONIBLES ({len(pds)}) ═══\n")
                    for i, p_ in enumerate(pds):
                        cn = p_.get("CdnName", "?")
                        mu = (p_.get("ManifestUrl") or "")[:90]
                        la = (p_.get("LaUrl") or "")[:90]
                        out.insert("end", f"[{i}] {cn}\n    Manifest: {mu}...\n    LaUrl:    {la}...\n\n")
                    out.insert("end", "═══ JSON COMPLETO ═══\n\n")
                out.insert("end", json.dumps(data, indent=2, ensure_ascii=False))
            except Exception as e:
                out.insert("end", f"❌ {e}\n")
        bf = tk.Frame(d, bg=GUI_BG); bf.pack(fill="x", padx=10, pady=6)
        self._styled_button(bf, "🔍 Dump", run, GUI_GREEN)
        self._styled_button(bf, "Cerrar", d.destroy, GUI_FG, side="right")

    def act_generate_channels(self):
        self.clear_log(); self.log("▶ Generando canales...", "accent")
        self.run_async(self._do_gen_channels)

    def _do_gen_channels(self):
        try: _load_token_safe(do_refresh_if_possible=True)
        except Exception as e: self.log(f"⚠️ {e}", "warn"); return
        s = get_selected_channels_from_config() or get_channels(_get_token())
        generate_dazn_playlist(
            output_file=config.get("output_file_channels", OUTPUT_FILE_CHANNELS_DEFAULT),
            selected_channels=s)

    def act_select_channels(self):
        self.log("📡 Cargando canales...", "accent")
        def _f():
            try:
                all_ch = get_channels(_get_token())
                if _widget_alive(self.root):
                    self.root.after(0, lambda: self._dialog_select(all_ch))
            except Exception as e:
                self.log(f"❌ {e}", "err")
        self.run_async(_f)

    def _dialog_select(self, all_ch):
        tk = self.tk
        if not all_ch:
            self.log("❌ Sin canales", "err"); return
        d = self._new_dialog(f"Seleccionar Canales ({len(all_ch)})", 800, 700)
        top = tk.Frame(d, bg=GUI_BG); top.pack(fill="x", padx=10, pady=8)
        tk.Label(top, text="🔎 Filtro:", bg=GUI_BG, fg=GUI_FG).pack(side="left")
        fv = tk.StringVar(); tk.Entry(top, textvariable=fv, width=40).pack(side="left", padx=5)
        lf = tk.Frame(d, bg=GUI_BG); lf.pack(fill="both", expand=True, padx=10, pady=5)
        cv = tk.Canvas(lf, bg=GUI_BG2, highlightthickness=0)
        sb = tk.Scrollbar(lf, orient="vertical", command=cv.yview)
        inner = tk.Frame(cv, bg=GUI_BG2)
        cv.create_window((0, 0), window=inner, anchor="nw")
        cv.configure(yscrollcommand=sb.set)
        cv.pack(side="left", fill="both", expand=True); sb.pack(side="right", fill="y")
        inner.bind("<Configure>", lambda e: cv.configure(scrollregion=cv.bbox("all")))
        prev_sel = set(config.get("selected_channels", []))
        check_vars = {}
        for ch in all_ch:
            aid = ch.get('AssetId', ''); title = ch.get('Title', '?')
            default_checked = (not prev_sel) or (aid in prev_sel)
            v = tk.IntVar(value=1 if default_checked else 0)
            check_vars[aid] = (v, title, ch)
        widgets = []
        def rebuild(*a):
            if not _widget_alive(inner): return
            for w in widgets: w.destroy()
            widgets.clear()
            f = fv.get().strip().lower()
            for aid, (v, title, ch) in check_vars.items():
                if f and f not in title.lower(): continue
                cb = tk.Checkbutton(inner, text=title, variable=v,
                                    bg=GUI_BG2, fg=GUI_FG, selectcolor=GUI_BG,
                                    activebackground=GUI_BG2,
                                    activeforeground=GUI_ACCENT,
                                    font=("Segoe UI", 10), anchor="w")
                cb.pack(fill="x", padx=5, pady=1)
                widgets.append(cb)
        fv.trace_add("write", rebuild); rebuild()
        bf = tk.Frame(d, bg=GUI_BG); bf.pack(fill="x", padx=10, pady=8)
        def do_all():
            for v, _, _ in check_vars.values(): v.set(1)
        def do_none():
            for v, _, _ in check_vars.values(): v.set(0)
        self._styled_button(bf, "✅ Todos", do_all, GUI_GREEN)
        self._styled_button(bf, "❌ Ninguno", do_none, GUI_RED)
        def save_close():
            sel = [ch for aid, (v, t, ch) in check_vars.items() if v.get()]
            config["selected_channels"] = [c.get('AssetId', '') for c in sel]
            save_config()
            self.log(f"✅ Guardados {len(sel)} canales", "ok")
            d.destroy()
        self._styled_button(bf, "💾 Guardar", save_close, GUI_ACCENT, side="right")
        self._styled_button(bf, "Cancelar", d.destroy, GUI_FG, side="right")

    def act_reset_channels(self):
        config["selected_channels"] = []
        save_config(); self.log("✅ Reset", "ok")

    def act_view_events(self):
        self.clear_log(); self.log("📅 Cargando eventos...", "accent")
        def _f():
            try:
                ev = get_scheduled_events(_get_token(), True, False)
                if _widget_alive(self.root):
                    self.root.after(0, lambda: self._dialog_events(ev))
            except Exception as e:
                self.log(f"❌ {e}", "err")
        self.run_async(_f)

    def _dialog_events(self, events):
        tk = self.tk; ttk = self.ttk
        if not events:
            self.log("❌ Sin eventos", "warn"); return
        d = self._new_dialog(f"Eventos ({len(events)})", 1100, 800)
        tk.Label(d, text="Selecciona eventos → generar M3U ClearKey (CK Hunter activo)",
                 bg=GUI_BG, fg=GUI_MAGENTA, font=("Segoe UI", 12, "bold")).pack(pady=8)
        tv = ttk.Treeview(d, columns=("data", "tipo", "titulo"), show="headings",
                          selectmode="extended")
        for col, txt, w in [("data", "Fecha", 130), ("tipo", "Tipo", 80),
                            ("titulo", "Título", 800)]:
            tv.heading(col, text=txt); tv.column(col, width=w)
        vsb = ttk.Scrollbar(d, orient="vertical", command=tv.yview)
        tv.configure(yscroll=vsb.set); vsb.pack(side="right", fill="y", padx=(0, 10))
        tv.pack(fill="both", expand=True, padx=10, pady=5)
        iid_map = {}
        try: rome = ZoneInfo('Europe/Rome')
        except Exception: rome = timezone.utc
        for i, e in enumerate(events):
            v = e.get('Start') or e.get('EventStartTime') or ''
            try:
                dt = datetime.fromisoformat(str(v).replace('Z', '+00:00')).astimezone(rome)
                when = dt.strftime('%d/%m %H:%M')
            except Exception: when = str(v)[:16]
            tt = (e.get('Type') or '')[:6]
            title = (e.get('Title') or '?').strip()
            iid = f"ev_{i}"
            tv.insert("", "end", iid=iid, values=(when, tt, title))
            iid_map[iid] = e
        bf = tk.Frame(d, bg=GUI_BG); bf.pack(fill="x", padx=10, pady=8)
        def gen_selected():
            sel = [iid_map[iid] for iid in tv.selection() if iid in iid_map]
            if not sel:
                messagebox.showwarning("Ninguno", "Selecciona eventos.", parent=d); return
            d.destroy()
            self.clear_log()
            self.log(f"🎬 Generando M3U para {len(sel)} eventos...", "accent")
            self.run_async(lambda: generate_m3u_from_events(
                sel, output_file=config.get("output_file_events", OUTPUT_FILE_EVENTS_DEFAULT),
                auto_pending=True,
                use_ck_hunter=config.get("ck_hunter_enabled", True)))
        def gen_all():
            d.destroy()
            self.clear_log()
            self.log(f"🎬 Generando M3U para {len(events)} eventos...", "accent")
            self.run_async(lambda: generate_m3u_from_events(
                events, output_file=config.get("output_file_events", OUTPUT_FILE_EVENTS_DEFAULT),
                auto_pending=True,
                use_ck_hunter=config.get("ck_hunter_enabled", True)))
        self._styled_button(bf, "✅ Seleccionar todos", lambda: tv.selection_set(tv.get_children()), GUI_GREEN)
        self._styled_button(bf, "🎬 Generar seleccionados", gen_selected, GUI_MAGENTA)
        self._styled_button(bf, "🎬 Generar todos", gen_all, GUI_ACCENT)
        self._styled_button(bf, "Cerrar", d.destroy, GUI_FG, side="right")

    def act_generate_events(self):
        self.clear_log(); self.log("🎬 Generando eventos automáticos...", "accent")
        self.run_async(self._do_gen_events)

    def _do_gen_events(self):
        try: _load_token_safe(do_refresh_if_possible=True)
        except Exception as e: self.log(f"⚠️ {e}", "warn"); return
        ev = get_scheduled_events(_get_token(), config.get("events_include_live", True), True)
        if config.get("events_only_today"): ev = filter_events_today(ev)
        filt = get_events_filter()
        if filt[0] != "all": ev = apply_event_filter(ev, filt)
        if not ev: self.log("⚠️ Sin eventos", "warn"); return
        generate_m3u_from_events(ev,
            output_file=config.get("output_file_events", OUTPUT_FILE_EVENTS_DEFAULT),
            auto_pending=True,
            use_ck_hunter=config.get("ck_hunter_enabled", True))

    def act_pending(self):
        self.clear_log(); self.log("⏳ Pending...", "accent")
        d = self._new_dialog("Eventos Pending", 800, 500)
        tv = self.ttk.Treeview(d, columns=("titulo", "asset"), show="headings")
        tv.heading("titulo", text="Título"); tv.column("titulo", width=500)
        tv.heading("asset", text="AssetId"); tv.column("asset", width=250)
        tv.pack(fill="both", expand=True, padx=10, pady=8)
        for i, ev in enumerate(load_pending_events()):
            tv.insert("", "end", values=(ev.get('Title', '?'), ev.get('AssetId', '')))
        bf = tk.Frame(d, bg=GUI_BG); bf.pack(fill="x", padx=10, pady=8)
        def clear_all():
            save_pending_events([]); d.destroy()
            self.log("🗑 Pending vaciados", "warn")
        self._styled_button(bf, "🗑 Vaciar", clear_all, GUI_RED)
        self._styled_button(bf, "Cerrar", d.destroy, GUI_FG, side="right")

    def act_start_events(self):
        start_events_scheduler(); self.log("✅ Scheduler eventos ON", "ok")

    def act_stop_events(self):
        stop_events_scheduler(); self.log("⏹ Scheduler eventos OFF", "warn")

    def act_start_channels(self):
        start_channels_scheduler(); self.log("✅ Scheduler canales ON", "ok")

    def act_stop_channels(self):
        stop_channels_scheduler(); self.log("⏹ Scheduler canales OFF", "warn")

    def act_open_har_inspector(self):
        try:
            _HarInspectorWindow(self.root, self.log)
            self.log("🔬 HAR Inspector abierto", "accent")
        except Exception as e:
            self.log(f"❌ {e}", "err")

    def act_kid_key_manager(self):
        self.log("🔑 Abriendo Gestor KID/KEY...", "accent")
        try:
            open_kid_key_manager_tkinter(parent=self.root)
        except Exception as e:
            self.log(f"❌ {e}", "err")

    def act_deprecated_statics(self):
        tk = self.tk
        d = self._new_dialog("🩹 Estáticas deprecadas (auto-healing)", 900, 600)
        tk.Label(d, text="🩹 ESTÁTICAS DEPRECADAS",
                 bg=GUI_BG, fg=GUI_YELLOW, font=("Segoe UI", 14, "bold")).pack(pady=12)
        dep = _load_deprecated_statics()
        tv = self.ttk.Treeview(d, columns=("titulo", "old_kid", "new_kid", "at"),
                               show="headings", selectmode="browse")
        for col, txt, w in [("titulo", "Título", 250), ("old_kid", "KID viejo", 260),
                            ("new_kid", "KID nuevo", 260), ("at", "Fecha", 140)]:
            tv.heading(col, text=txt); tv.column(col, width=w)
        vsb = self.ttk.Scrollbar(d, orient="vertical", command=tv.yview)
        tv.configure(yscroll=vsb.set); vsb.pack(side="right", fill="y", padx=(0, 10))
        tv.pack(fill="both", expand=True, padx=10, pady=6)

        def refresh():
            for iid in tv.get_children():
                tv.delete(iid)
            for name, info in sorted(dep.items()):
                tv.insert("", "end", iid=name,
                          values=(name, info.get("old_kid", "")[:32],
                                  info.get("new_kid", "")[:32],
                                  info.get("at", "")))
        refresh()
        bf = tk.Frame(d, bg=GUI_BG); bf.pack(fill="x", padx=10, pady=8)

        def restore_selected():
            sel = tv.selection()
            if not sel:
                messagebox.showinfo("Sin selección", "Selecciona una fila.", parent=d)
                return
            name = sel[0]
            if _restore_static_for_title(name):
                self.log(f"♻️ Estática restaurada: {name}", "ok")
                refresh()
            else:
                self.log(f"⚠️ No encontrada: {name}", "warn")

        def restore_all():
            if not messagebox.askyesno("Confirmar",
                "¿Restaurar TODAS las estáticas deprecadas?", parent=d):
                return
            _save_deprecated_statics({})
            self.log("♻️ Todas las estáticas restauradas", "ok")
            refresh()

        def deprecate_news_now():
            targets = [
                ("NEWS DAI CAMPI DELLA SERIE A", "d569aaa78cc25b458a20baa59d103847", ""),
            ]
            n = 0
            for name, old_kid, new_kid in targets:
                if _deprecate_static_for_title(name, old_kid, new_kid,
                                                reason="Deprecación manual"):
                    n += 1
            self.log(f"🩹 Deprecadas {n} entradas", "ok")
            refresh()

        self._styled_button(bf, "♻️ Restaurar seleccionada", restore_selected, GUI_GREEN)
        self._styled_button(bf, "♻️ Restaurar todas", restore_all, GUI_MAGENTA)
        self._styled_button(bf, "🩹 Deprecar NEWS ahora", deprecate_news_now, GUI_YELLOW)
        self._styled_button(bf, "Cerrar", d.destroy, GUI_FG, side="right")

    def act_import_external_json(self):
        path = filedialog.askopenfilename(
            title="Importar JSON claves externas (external_keys_export.json)",
            filetypes=[("JSON", "*.json"), ("Todos", "*.*")])
        if not path: return
        try:
            with open(path, "r", encoding="utf-8-sig") as f:
                incoming = json.load(f)
        except Exception as e:
            self.log(f"❌ Error leyendo JSON: {e}", "err"); return
        if not isinstance(incoming, dict):
            self.log("❌ El archivo no contiene un objeto JSON válido", "err"); return
        try:
            stats = import_external_json(path)
        except Exception as e:
            self.log(f"❌ Error import: {e}", "err"); return
        self.log(f"✅ Import: +{stats['added']} nuevos, ~{stats['updated']} act., "
                 f"+{stats['placeholder']} placeholder", "ok")

    def act_ck_hunter(self):
        tk = self.tk
        self.clear_log()
        st = ck_hunter_stats()
        self.log("=" * 55, "accent")
        self.log("  🎯 CK HUNTER — DB ATOMIC", "accent")
        self.log("=" * 55, "accent")
        self.log(f"🔐 Claves estáticas: {st['static']}", "info")
        self.log(f"📦 Linear (canales): {st['by_cat'].get('linear', 0)}", "info")
        self.log(f"📦 Events (eventos): {st['by_cat'].get('events', 0)}", "info")
        self.log(f"📊 Total indexadas: {st['total_indexed']}", "ok")
        d = self._new_dialog("🎯 CK Hunter — DB", 750, 640)
        tk.Label(d, text="🎯 CK HUNTER — DB ATOMIC",
                 bg=GUI_BG, fg=GUI_ACCENT, font=("Segoe UI", 14, "bold")).pack(pady=12)
        info = tk.Frame(d, bg=GUI_BG); info.pack(fill="x", padx=20, pady=8)
        tk.Label(info, text=f"🔐 Estáticas: {st['static']}",
                 bg=GUI_BG, fg=GUI_FG, font=("Consolas", 10), anchor="w").pack(fill="x")
        tk.Label(info, text=f"📦 Linear: {st['by_cat'].get('linear', 0)}",
                 bg=GUI_BG, fg=GUI_FG, font=("Consolas", 10), anchor="w").pack(fill="x")
        tk.Label(info, text=f"📦 Events: {st['by_cat'].get('events', 0)}",
                 bg=GUI_BG, fg=GUI_FG, font=("Consolas", 10), anchor="w").pack(fill="x")
        tk.Label(info, text=f"📊 Total: {st['total_indexed']}",
                 bg=GUI_BG, fg=GUI_GREEN, font=("Consolas", 10, "bold"), anchor="w").pack(fill="x")
        var_on = tk.IntVar(value=1 if config.get("ck_hunter_enabled", True) else 0)
        tk.Checkbutton(d, text="Habilitar CK Hunter en los próximos ciclos",
                            variable=var_on, bg=GUI_BG, fg=GUI_FG,
                            selectcolor=GUI_BG, activebackground=GUI_BG,
                            activeforeground=GUI_ACCENT, font=("Segoe UI", 10)).pack(pady=6)
        var_kh = tk.IntVar(value=1 if config.get("key_hunter_enabled", True) else 0)
        tk.Checkbutton(d, text="Habilitar KEY Hunter (petición directa al license server)",
                             variable=var_kh, bg=GUI_BG, fg=GUI_FG,
                             selectcolor=GUI_BG, activebackground=GUI_BG,
                             activeforeground=GUI_ACCENT, font=("Segoe UI", 10)).pack(pady=4)
        var_hls = tk.IntVar(value=1 if config.get("hls_output_enabled", True) else 0)
        tk.Checkbutton(d, text="📻 Generar también archivo HLS (AppleCoreMedia)",
                             variable=var_hls, bg=GUI_BG, fg=GUI_CYAN,
                             selectcolor=GUI_BG, activebackground=GUI_BG,
                             activeforeground=GUI_CYAN, font=("Segoe UI", 10, "bold")).pack(pady=4)
        var_wvd = tk.IntVar(value=1 if config.get("wvd_enabled", True) else 0)
        tk.Checkbutton(d, text="🎬 Habilitar WVD Widevine (último recurso)",
                             variable=var_wvd, bg=GUI_BG, fg=GUI_RED,
                             selectcolor=GUI_BG, activebackground=GUI_BG,
                             activeforeground=GUI_RED, font=("Segoe UI", 10, "bold")).pack(pady=4)
        bf = tk.Frame(d, bg=GUI_BG); bf.pack(fill="x", padx=20, pady=8)

        def save_toggle():
            config["ck_hunter_enabled"] = bool(var_on.get())
            config["key_hunter_enabled"] = bool(var_kh.get())
            config["hls_output_enabled"] = bool(var_hls.get())
            config["wvd_enabled"] = bool(var_wvd.get())
            save_config()
            self.log(f"✅ Guardado", "ok")
            d.destroy()
        self._styled_button(bf, "💾 Guardar", save_toggle, GUI_GREEN)
        self._styled_button(bf, "🎬 Abrir WVD", self.act_wvd_manager, GUI_RED)
        self._styled_button(bf, "Cerrar", d.destroy, GUI_FG, side="right")

    def act_profiles(self):
        tk = self.tk
        self.clear_log()
        self.log("=" * 55, "accent")
        self.log("  👤 GESTOR DE PERFILES", "accent")
        self.log("=" * 55, "accent")
        profs = list_profiles()
        if not profs:
            self.log("ℹ️ Ningún perfil guardado. Se usa token.txt", "info")
        for p in profs:
            mark = "🟢" if p["active"] else "⚪"
            self.log(f"{mark} {p['name']:15s} | {p['country']:3s} | {p['label']}", "info")

        d = self._new_dialog("👤 Perfiles DAZN", 1100, 820)
        try:
            d.state("zoomed")
        except Exception:
            try:
                d.attributes("-zoomed", True)
            except Exception:
                pass

        tk.Label(d, text="👤 GESTOR DE PERFILES DAZN",
                 bg=GUI_BG, fg=GUI_ACCENT, font=("Segoe UI", 14, "bold")).pack(pady=12)
        tk.Label(d, text="🌐 Cada perfil tiene una sesión de navegador AISLADA (sin tokens cruzados)",
                 bg=GUI_BG, fg="#8b949e", font=("Segoe UI", 9, "italic")).pack()

        lf = tk.Frame(d, bg=GUI_BG); lf.pack(fill="both", expand=True, padx=20, pady=6)
        lb = tk.Listbox(lf, bg=GUI_BG2, fg=GUI_FG, selectbackground=GUI_ACCENT,
                        selectforeground=GUI_BG, font=("Consolas", 11),
                        relief="flat", borderwidth=0, activestyle="none", height=16)
        lb.pack(side="left", fill="both", expand=True)
        sb = tk.Scrollbar(lf, orient="vertical", command=lb.yview)
        sb.pack(side="right", fill="y"); lb.configure(yscrollcommand=sb.set)

        def refresh_list():
            lb.delete(0, tk.END)
            for p in list_profiles():
                mark = "🟢" if p["active"] else "⚪"
                lb.insert(tk.END, f"{mark} {p['name']}  [{p['country']}]  {p['label']}  ({p['token_short']})")
        refresh_list()

        ff = tk.Frame(d, bg=GUI_BG); ff.pack(fill="x", padx=20, pady=6)
        tk.Label(ff, text="Nombre:", bg=GUI_BG, fg=GUI_FG, width=10, anchor="w").grid(row=0, column=0, sticky="w")
        name_v = tk.StringVar()
        tk.Entry(ff, textvariable=name_v, bg=GUI_BG2, fg=GUI_FG, width=20,
                 insertbackground=GUI_FG, relief="flat").grid(row=0, column=1, padx=5)
        tk.Label(ff, text="Etiqueta:", bg=GUI_BG, fg=GUI_FG, width=10, anchor="w").grid(row=0, column=2, sticky="w")
        label_v = tk.StringVar()
        tk.Entry(ff, textvariable=label_v, bg=GUI_BG2, fg=GUI_FG, width=25,
                 insertbackground=GUI_FG, relief="flat").grid(row=0, column=3, padx=5)
        tk.Label(ff, text="(vacío → usa token.txt actual)", bg=GUI_BG, fg="#8b949e",
                 font=("Segoe UI", 8, "italic")).grid(row=1, column=1, columnspan=3, sticky="w")

        bf = tk.Frame(d, bg=GUI_BG); bf.pack(fill="x", padx=20, pady=10)

        def _selected_name():
            sel = lb.curselection()
            if not sel:
                return None
            line = lb.get(sel[0])
            parts = line.split()
            if len(parts) >= 2:
                return parts[1]
            return None

        def do_add_txt():
            name = name_v.get().strip()
            if not name:
                messagebox.showwarning("Falta nombre", "Introduce un nombre.", parent=d); return
            ok, msg = add_profile(name, token=None, label=label_v.get().strip() or None)
            self.log(("✅ " if ok else "❌ ") + msg, "ok" if ok else "err")
            refresh_list(); name_v.set(""); label_v.set("")

        def do_capture():
            name = _selected_name()
            if not name:
                name = name_v.get().strip()
            if not name:
                messagebox.showwarning("Falta nombre",
                    "Selecciona un perfil de la lista, o escribe un nombre en el campo 'Nombre'.",
                    parent=d)
                return
            label_val = label_v.get().strip()
            d.destroy()
            def _cap():
                self.log(f"🔑 Capturando token para el perfil '{name}'...", "accent")
                tok = capture_and_save_token(log=self.log, profile_name=name)
                if tok:
                    ok, msg = add_profile(name, token=tok,
                                          label=label_val or None,
                                          set_active=True)
                    self.log(("✅ " if ok else "❌ ") + msg, "ok" if ok else "err")
                    switch_profile(name)
            self.run_async(_cap)

        def do_switch():
            pname = _selected_name()
            if not pname:
                messagebox.showwarning("Sin selección",
                    "Selecciona un perfil de la lista para activarlo.", parent=d)
                return
            ok, msg = switch_profile(pname)
            self.log(("✅ " if ok else "❌ ") + msg, "ok" if ok else "err")
            refresh_list()

        def do_delete():
            pname = _selected_name()
            if not pname: return
            if not messagebox.askyesno("Confirmar", f"¿Eliminar perfil '{pname}'?", parent=d): return
            ok, msg = delete_profile(pname)
            self.log(("✅ " if ok else "❌ ") + msg, "ok" if ok else "err")
            refresh_list()

        def do_rename():
            pname = _selected_name()
            if not pname: return
            new_name = name_v.get().strip()
            if not new_name:
                messagebox.showwarning("Falta nombre", "Introduce el nuevo nombre.", parent=d); return
            ok, msg = rename_profile(pname, new_name)
            self.log(("✅ " if ok else "❌ ") + msg, "ok" if ok else "err")
            refresh_list(); name_v.set("")

        def do_clear_browser():
            pname = _selected_name()
            if not pname:
                messagebox.showwarning("Sin selección",
                    "Selecciona un perfil para limpiar su sesión de navegador.", parent=d)
                return
            import shutil
            btype = config.get("browser_type", "auto")
            if btype == "edge":
                pdir = _browser_profile_dir(pname, browser="edge")
            else:
                pdir = _browser_profile_dir(pname, browser="chrome")
            if not os.path.isdir(pdir):
                messagebox.showinfo("Nada que limpiar",
                    f"No hay carpeta de navegador para '{pname}'.", parent=d)
                return
            if not messagebox.askyesno("Confirmar",
                f"¿Eliminar la sesión del navegador de '{pname}'?\n\n"
                f"Carpeta: {pdir}\n\n"
                f"Al próximo 🔑 Capturar nuevo tendrás que volver a iniciar sesión.", parent=d):
                return
            try:
                shutil.rmtree(pdir, ignore_errors=True)
                self.log(f"🧹 Sesión de navegador de '{pname}' eliminada", "ok")
                messagebox.showinfo("Hecho",
                    f"Sesión del navegador de '{pname}' limpiada.", parent=d)
            except Exception as e:
                self.log(f"❌ {e}", "err")

        def do_relabel_country():
            pname = _selected_name()
            if not pname:
                return
            with profiles_lock:
                data = _load_profiles()
                info = (data.get("profiles") or {}).get(pname) or {}
                tok = info.get("token", "")
            real = "?"
            if tok and tok.count(".") == 2:
                try:
                    dec = jwt.decode(tok, options={"verify_signature": False})
                    real = dec.get("contentCountry", "?")
                except Exception:
                    pass
            with profiles_lock:
                data = _load_profiles()
                if pname in (data.get("profiles") or {}):
                    data["profiles"][pname]["country"] = real
                    _save_profiles(data)
            self.log(f"🏷 '{pname}' → país real del token: {real}", "ok")
            refresh_list()

        self._styled_button(bf, "➕ Añadir (desde token.txt)", do_add_txt, GUI_GREEN)
        self._styled_button(bf, "🔑 Capturar nuevo", do_capture, GUI_YELLOW)
        self._styled_button(bf, "🔀 Activar", do_switch, GUI_ACCENT)
        self._styled_button(bf, "🧹 Limpiar sesión", do_clear_browser, GUI_RED)
        self._styled_button(bf, "🏷 Releer país", do_relabel_country, GUI_CYAN)
        self._styled_button(bf, "✏️ Renombrar", do_rename, GUI_MAGENTA)
        self._styled_button(bf, "🗑 Eliminar", do_delete, GUI_RED)
        self._styled_button(bf, "Cerrar", d.destroy, GUI_FG, side="right")

    def act_status(self):
        self.clear_log()
        L = self.log
        st = ck_hunter_stats()
        pname, pinfo = get_active_profile()
        dep = _load_deprecated_statics()
        L("=" * 55, "accent"); L("  ESTADO", "accent"); L("=" * 55, "accent")
        L(f"👤 Perfil activo: {pname or '(ninguno → token.txt)'}", "accent")
        L(f"🌐 Navegador: {config.get('browser_type', 'auto')}", "accent")
        L(f"🎯 CK Hunter: {'ON' if config.get('ck_hunter_enabled', True) else 'OFF'} "
          f"({st['total_indexed']} KID conocidos)", "accent")
        L(f"🎬 WVD Widevine: {'ON' if config.get('wvd_enabled', True) else 'OFF'}", "accent")
        L(f"   pywidevine: {'✅' if _pywidevine_available() else '❌ no instalado'}", "accent")
        L(f"   CDM en caché: {'✅' if _wvd_cdm is not None else '—'}", "accent")
        L("=" * 55, "accent")

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
            if "❌" in line or "Failed" in line: tag = "err"
            elif "⚠️" in line: tag = "warn"
            elif "✅" in line: tag = "ok"
            elif "📻" in line: tag = "accent"
            elif "🎬" in line: tag = "accent"
            self.gui.log(line, tag)
    def flush(self): pass

def main_cli():
    global pin, VERSION
    get_token(); pin = config.get('pin', ''); VERSION = get_version()
    try: _release_all_locks()
    except Exception: pass
    while True:
        clear_screen()
        print("🎯 DAZN EXTRACTOR v5.3.8-ES — CLI")
        print("[1] Generar canales  [2] Seleccionar canales  [5] Generar eventos  [E] Estado  [0] Salir")
        c = input("👉 ").strip().lower()
        if c == "0": break
        elif c == "1":
            s = get_selected_channels_from_config() or get_channels(_get_token())
            generate_dazn_playlist(selected_channels=s)
            input("ENTER...")
        elif c == "5":
            ev = get_scheduled_events(_get_token(), config.get("events_include_live", True), True)
            if config.get("events_only_today"): ev = filter_events_today(ev)
            if ev:
                generate_m3u_from_events(ev,
                    output_file=config.get("output_file_events", OUTPUT_FILE_EVENTS_DEFAULT),
                    auto_pending=True,
                    use_ck_hunter=config.get("ck_hunter_enabled", True))
            input("ENTER...")
        elif c == "e":
            st = ck_hunter_stats()
            print(f"CK Hunter: {st['total_indexed']} KID")
            print(f"WVD: {'ON' if config.get('wvd_enabled', True) else 'OFF'}")
            print(f"pywidevine: {'✅' if _pywidevine_available() else '❌'}")
            print(f"Navegador: {config.get('browser_type', 'auto')}")
            input("ENTER...")

def main_gui():
    global _gui_instance, clear_screen, pin
    try: get_token()
    except Exception as e:
        print(f"❌ {e}"); sys.exit(1)
    pin = config.get('pin', '')
    try: _release_all_locks()
    except Exception: pass
    root = tk.Tk()
    _gui_instance = DaznGUI(root)
    clear_screen = lambda: _gui_instance.clear_log()
    sys.stdout = _GuiStdout(_gui_instance)

    try:
        stats = auto_import_recent_hars(log=_gui_instance.log, max_age_sec=600)
        if stats["files"] > 0:
            _gui_instance.log(
                f"✅ Auto-import HAR al inicio: {stats['files']} archivos → "
                f"+{stats['added']} completos, "
                f"~{stats['updated']} act., "
                f"+{stats['placeholder']} placeholder",
                "ok")
    except Exception as e:
        _gui_instance.log(f"⚠️ Auto-import HAR inicio: {e}", "warn")

    try:
        start_events_scheduler()
        _gui_instance.log("✅ Scheduler EVENTOS iniciado", "ok")
    except Exception as e:
        _gui_instance.log(f"⚠️ {e}", "warn")
    try:
        start_channels_scheduler()
        _gui_instance.log("✅ Scheduler CANALES iniciado", "ok")
    except Exception as e:
        _gui_instance.log(f"⚠️ {e}", "warn")
    if config.get("pending_watcher_active", True):
        try: start_pending_watcher()
        except Exception as e:
            _gui_instance.log(f"⚠️ {e}", "warn")
    _gui_instance.log("=" * 55, "accent")
    _gui_instance.log("  🎯 DAZN EXTRACTOR v5.3.8-ES", "accent")
    _gui_instance.log("=" * 55, "accent")
    try: root.mainloop()
    finally: sys.stdout = sys.__stdout__

if __name__ == "__main__":
    import signal
    signal.signal(signal.SIGINT, signal_handler)
    if "--cli" in sys.argv:
        main_cli()
    else:
        main_gui()