#!/usr/bin/env python3
"""Refait les captures d'écran de l'app montrées sur le site : assets/img/app/<nom>-<largeur>.webp.

Ce sont de vraies captures du simulateur iOS. Le test d'intégration de l'app (dépôt voisin, ../app)
integration_test/captures_site_test.dart lance l'app en démonstration (données des maquettes, heure figée à 9 h 41),
va d'écran en écran et, à chaque écran à garder, demande une capture à ce script, qui la fait avec
« xcrun simctl io <simulateur> screenshot ». La barre d'état est figée pendant ce temps (« 09:41 » sur un simulateur
en français, réseau et batterie pleins), puis rendue au simulateur.

Usage :
    python3 captures.py --simulateur <UDID>
        toutes les captures, puis les images du site (trois largeurs par écran)
    python3 captures.py --simulateur <UDID> --png ~/Desktop/captures-linga
        garde aussi les PNG d'origine (1320 × 2868 sur un iPhone Pro Max), utiles pour les fiches des stores

Seuls les écrans que les pages utilisent (src/pages/**, chemins /assets/img/app/<nom>-…) deviennent des images ;
les autres images de assets/img/app/ sont retirées. Le site attend des captures d'iPhone Pro Max (1320 × 2868) :
le cadre du téléphone en a les proportions.

Il faut macOS avec Xcode (xcrun simctl), Flutter et cwebp (brew install webp), et le simulateur démarré.
À la fin, « flutter test » désinstalle l'app du simulateur (son comportement par défaut) : relancer « flutter run »
pour la retrouver.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

ROOT = Path(__file__).resolve().parent
PAGES = ROOT / "src" / "pages"
OUT = ROOT / "assets" / "img" / "app"
TEST = "integration_test/captures_site_test.dart"

WIDTHS = (300, 600, 900)  # 1x, 2x et 3x d'un écran affiché sur environ 300 px de large
SIZE = (1320, 2868)  # iPhone Pro Max, en pixels
QUALITY = "84"

NAME_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
USED_RE = re.compile(r"/assets/img/app/([a-z0-9]+(?:-[a-z0-9]+)*)-(\d+)\.webp")

STATUS_BAR = [
    "--time", "9:41",
    "--dataNetwork", "wifi", "--wifiMode", "active", "--wifiBars", "3",
    "--cellularMode", "active", "--cellularBars", "4", "--operatorName", "",
    "--batteryState", "discharging", "--batteryLevel", "100",  # « charged » ajoute l'éclair vert de la charge
]


class Failure(Exception):
    pass


def run(command, **kwargs):
    return subprocess.run(command, check=False, text=True, **kwargs)


def tool(name: str, hint: str) -> str:
    found = shutil.which(name)
    if not found:
        raise Failure(f"« {name} » introuvable : {hint}")
    return found


def check_simulator(udid: str):
    listed = run(["xcrun", "simctl", "list", "devices", "-j"], capture_output=True)
    if listed.returncode != 0:
        raise Failure("xcrun simctl ne répond pas : Xcode est-il installé ?")
    for runtime in json.loads(listed.stdout)["devices"].values():
        for device in runtime:
            if device["udid"] == udid:
                if device["state"] != "Booted":
                    raise Failure(f"le simulateur {device['name']} ({udid}) n'est pas démarré : xcrun simctl boot {udid}")
                return device["name"]
    raise Failure(f"aucun simulateur {udid} (xcrun simctl list devices)")


def capture_server(udid: str, folder: Path, taken: list):
    """Petit serveur local : GET /capture?nom=<nom> écrit <folder>/<nom>.png et répond une fois l'image écrite."""

    class Handler(BaseHTTPRequestHandler):
        def answer(self, status: int, text: str):
            # Le texte va dans le corps, en UTF-8 : la ligne d'état, elle, n'accepte que le Latin-1.
            body = text.encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def fail(self, status: int, name: str, reason: str):
            print(f"ERREUR  capture « {name} » : {reason}", file=sys.stderr, flush=True)
            self.answer(status, reason)

        def do_GET(self):
            url = urlparse(self.path)
            name = parse_qs(url.query).get("nom", [""])[0]
            if url.path != "/capture" or not NAME_RE.match(name):
                self.fail(400, name, "attendu : /capture?nom=nom-de-l-ecran (minuscules, chiffres, tirets)")
                return
            target = folder / f"{name}.png"
            try:
                shot = run(["xcrun", "simctl", "io", udid, "screenshot", "--type=png", str(target)],
                           capture_output=True, timeout=60)
            except subprocess.TimeoutExpired:
                self.fail(500, name, "xcrun simctl io screenshot : pas de réponse en 60 s")
                return
            if shot.returncode != 0 or not target.is_file():
                lines = (shot.stderr or "").strip().splitlines() or ["capture impossible"]
                self.fail(500, name, f"xcrun simctl io screenshot : {lines[-1][:300]}")
                return
            taken.append(name)
            print(f"  capture  {name}", flush=True)
            self.answer(200, "ok")

        def log_message(self, *args):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server


def used_names() -> dict:
    """Écrans utilisés par les pages : nom -> pages."""
    used: dict = {}
    for page in sorted(PAGES.rglob("*.html")):
        for name, width in USED_RE.findall(page.read_text(encoding="utf-8")):
            if int(width) not in WIDTHS:
                raise Failure(f"{page.relative_to(ROOT)} : /assets/img/app/{name}-{width}.webp : "
                              f"largeur inconnue (largeurs produites : {', '.join(map(str, WIDTHS))})")
            used.setdefault(name, set()).add(str(page.relative_to(PAGES)))
    return used


def pixel_size(png: Path) -> tuple:
    info = run(["sips", "-g", "pixelWidth", "-g", "pixelHeight", str(png)], capture_output=True).stdout
    width = re.search(r"pixelWidth: (\d+)", info)
    height = re.search(r"pixelHeight: (\d+)", info)
    if not (width and height):
        raise Failure(f"{png.name} : dimensions illisibles")
    return int(width.group(1)), int(height.group(1))


def convert(png: Path, name: str, cwebp: str, work: Path) -> list:
    """Trois WebP par écran, écrits d'abord dans le dossier de travail puis mis en place d'un coup : un build lancé
    en même temps ne lit jamais une image à moitié écrite."""
    if pixel_size(png) != SIZE:
        width, height = pixel_size(png)
        raise Failure(f"{name} : {width} × {height} au lieu de {SIZE[0]} × {SIZE[1]} : le site attend des captures "
                      "d'iPhone Pro Max (l'île et la barre d'accueil du cadre .phone sont placées pour lui). Changer "
                      "de modèle, c'est changer SIZE ici et les mesures de .phone dans assets/css/linga.css.")
    written = []
    for target in WIDTHS:
        height = round(SIZE[1] * target / SIZE[0])  # 652, 1304, 1955 : les hauteurs écrites dans les pages
        resized = work / f"{name}-{target}.png"
        step = run(["sips", "--resampleHeightWidth", str(height), str(target), str(png), "--out", str(resized)],
                   capture_output=True)
        if step.returncode != 0:
            raise Failure(f"{name} : redimensionnement en {target} px impossible : {step.stderr.strip()}")
        ready = work / f"{name}-{target}.webp"
        step = run([cwebp, "-quiet", "-q", QUALITY, "-m", "6", "-sharp_yuv", "-metadata", "none",
                    str(resized), "-o", str(ready)], capture_output=True)
        if step.returncode != 0 or not ready.is_file() or ready.stat().st_size == 0:
            raise Failure(f"{name} : conversion en WebP impossible : {step.stderr.strip()}")
        written.append((ready, OUT / ready.name))
    return written


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Refait les captures d'écran de l'app pour le site.")
    parser.add_argument("--simulateur", required=True, metavar="UDID",
                        help="UDID du simulateur iOS (xcrun simctl list devices), démarré ; jamais « booted »")
    parser.add_argument("--app", default=str(ROOT.parent / "app"), help="dossier de l'app Flutter (défaut : ../app)")
    parser.add_argument("--png", metavar="DOSSIER", help="garde aussi les PNG d'origine dans ce dossier")
    args = parser.parse_args(argv)

    udid = args.simulateur
    app = Path(args.app).expanduser().resolve()
    try:
        if not re.fullmatch(r"[0-9A-Fa-f-]{36}", udid):
            raise Failure("--simulateur attend un UDID (xcrun simctl list devices), pas un nom ni « booted »")
        if not (app / TEST).is_file():
            raise Failure(f"{app / TEST} introuvable : --app doit désigner le dépôt de l'app")
        tool("xcrun", "il faut Xcode")
        tool("sips", "il faut macOS")
        cwebp = tool("cwebp", "brew install webp")
        flutter = os.environ.get("FLUTTER") or tool("flutter", "Flutter doit être dans le PATH (ou FLUTTER=…)")
        device = check_simulator(udid)
        used = used_names()
        if not used:
            raise Failure("aucune page n'utilise de capture (/assets/img/app/<nom>-<largeur>.webp)")

        work = Path(tempfile.mkdtemp(prefix="linga-captures-"))
        shots = work / "png"
        shots.mkdir()
        taken: list = []
        server = capture_server(udid, shots, taken)
        print(f"Captures sur {device}, barre d'état à 09:41…", flush=True)
        if run(["xcrun", "simctl", "status_bar", udid, "override", *STATUS_BAR]).returncode != 0:
            raise Failure("impossible de figer la barre d'état")
        try:
            test = run([flutter, "test", TEST, "-d", udid,
                        f"--dart-define=LINGA_CAPTURES=http://127.0.0.1:{server.server_address[1]}"], cwd=app)
        finally:
            run(["xcrun", "simctl", "status_bar", udid, "clear"])
            server.shutdown()
        if args.png:  # même après un échec : les captures faites aident à voir où le test s'est arrêté
            keep = Path(args.png).expanduser()
            keep.mkdir(parents=True, exist_ok=True)
            for png in shots.glob("*.png"):
                shutil.copy2(png, keep / png.name)
        if test.returncode != 0:
            kept = "" if args.png else f" ; captures faites : {shots}"
            work = None  # gardé pour voir où le test s'est arrêté
            raise Failure(f"le test d'intégration a échoué ({len(taken)} capture(s) faite(s) : "
                          f"{', '.join(taken) or 'aucune'}){kept}")

        missing = sorted(set(used) - set(taken))
        if missing:
            raise Failure("écrans utilisés par le site mais pas capturés par le test : " + ", ".join(missing))

        ready = []
        for name in sorted(used):
            ready += convert(shots / f"{name}.png", name, cwebp, work)
        OUT.mkdir(parents=True, exist_ok=True)
        for source, target in ready:
            os.replace(source, target)
        written = [target for _, target in ready]
        for old in OUT.iterdir():
            if old.is_file() and old not in written:
                old.unlink()
    except Failure as error:
        print(f"ERREUR  {error}", file=sys.stderr)
        return 1
    finally:
        if "work" in locals() and work is not None:
            shutil.rmtree(work, ignore_errors=True)

    total = sum(f.stat().st_size for f in written)
    print(f"assets/img/app/ : {len(used)} écran(s), {len(written)} image(s), {total / 1024:.0f} Ko")
    unused = sorted(set(taken) - set(used))
    if unused:
        print(f"capturés mais pas utilisés par le site : {', '.join(unused)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
