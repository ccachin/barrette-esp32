# web.py - page web (Wi-Fi) : message, scene, LED, luminosite + envoi / gestion d'images.
# Les images sont converties en RGB565 par le NAVIGATEUR du telephone (rien a installer),
# puis envoyees ici et enregistrees dans images/*.raw
import network
import asyncio
import os
import socket
from time import ticks_ms

IMG_DIR = "images"
DEBUG = True                 # affiche dans la console les requetes DNS / HTTP recues (utile pour diagnostiquer)
OK = "abcdefghijklmnopqrstuvwxyz0123456789-_"


def start_ap(ssid, password, txpower=None, max_clients=None):
    ap = network.WLAN(network.AP_IF)
    ap.active(True)
    try:                                         # le telephone doit utiliser la carte comme serveur DNS
        ip = ap.ifconfig()[0]
        ap.ifconfig((ip, "255.255.255.0", ip, ip))
    except Exception as e:
        print("ifconfig :", e)
    if max_clients:                              # limite le nombre d'appareils connectes en meme temps
        try:
            ap.config(max_clients=max_clients)
        except Exception as e:
            print("max_clients :", e)
    if password and len(password) >= 8:
        ap.config(essid=ssid, password=password, authmode=3)
    else:
        ap.config(essid=ssid, authmode=0)
    if txpower:                                  # puissance d'emission en dBm (moins = moins chaud)
        try:
            ap.config(txpower=txpower)
        except Exception as e:
            print("txpower :", e)
    return ap.ifconfig()[0]


async def dns_server(ip, port=53):
    """Mini serveur DNS : tout nom de domaine -> IP de la carte (portail captif)."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.setblocking(False)
    s.bind(("0.0.0.0", port))
    ipb = bytes(int(x) for x in ip.split("."))
    while True:
        try:
            data, addr = s.recvfrom(512)
        except OSError:
            await asyncio.sleep_ms(60)
            continue
        try:
            if len(data) > 17:
                i = 12
                while data[i] != 0:
                    i += data[i] + 1
                if DEBUG:
                    print("dns:", data[13:i].decode("utf-8", "ignore"), addr[0])
                qend = i + 5
                qtype = data[i + 1] * 256 + data[i + 2]
                resp = (data[:2] + b"\x81\x80\x00\x01" + (b"\x00\x01" if qtype == 1 else b"\x00\x00")
                        + b"\x00\x00\x00\x00" + data[12:qend])
                if qtype == 1:
                    resp += b"\xc0\x0c\x00\x01\x00\x01\x00\x00\x00\x3c\x00\x04" + ipb
                s.sendto(resp, addr)
        except Exception:
            pass


def stop_ap():
    network.WLAN(network.AP_IF).active(False)


def ap_clients():
    try:
        return len(network.WLAN(network.AP_IF).status("stations"))
    except Exception:
        return 0


def unquote(s):
    b = s.replace("+", " ").encode()
    out = bytearray()
    i, n = 0, len(b)
    while i < n:
        if b[i] == 37 and i + 2 < n:
            try:
                out.append(int(b[i + 1:i + 3].decode(), 16))
                i += 3
                continue
            except ValueError:
                pass
        out.append(b[i])
        i += 1
    try:
        return out.decode()
    except UnicodeError:
        return ""


def esc(s):
    return s.replace("&", "&amp;").replace('"', "&quot;").replace("<", "&lt;").replace(">", "&gt;")


def clean(name):
    s = "".join(c for c in name.lower() if c in OK)[:24]
    return s or "image"


def parse_qs(qs):
    q = {}
    for kv in qs.split("&"):
        if "=" in kv:
            k, v = kv.split("=", 1)
            q[k] = unquote(v)
    return q


def list_images():
    try:
        return sorted(n[:-4] for n in os.listdir(IMG_DIR) if n.endswith(".raw"))
    except OSError:
        return []


def free_bytes():
    try:
        st = os.statvfs("/")
        return st[0] * st[3]
    except OSError:
        return 0


def exists(path):
    try:
        os.stat(path)
        return True
    except OSError:
        return False


PAGE = """<!doctype html><html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Barrette</title><style>
body{font-family:sans-serif;background:#111;color:#eee;max-width:420px;margin:auto;padding:16px}
input,select,button{width:100%;box-sizing:border-box;font-size:18px;padding:10px;margin:6px 0 14px;border-radius:8px;border:0}
button{background:#e91e63;color:#fff;font-weight:bold}label{font-size:14px;color:#aaa}
a{color:#4fc3f7}li{margin:8px 0}h3{margin-top:28px;border-top:1px solid #333;padding-top:16px}
</style></head><body><h2>Barrette</h2>
<form action="/" method="get">
<label>Message</label><input name="message" maxlength="120" value="@MSG@">
<label>Scene</label><select name="scene">@OPTS@</select>
<label>Luminosite : @BR@%</label><input type="range" name="brightness" min="5" max="100" value="@BR@">
<label>LED sous l'ecran</label><select name="led">@LEDS@</select>
<label>Luminosite LED : @LB@%</label><input type="range" name="led_brightness" min="0" max="100" value="@LB@">
<button>Envoyer</button></form>
<h3>Images</h3>
<label>Choisir des photos (@W@x@H@ px, convertie automatiquement)</label>
<input type="file" id="f" accept="image/*" multiple>
<select id="m"><option value="cover">Remplir l'ecran (recadre)</option>
<option value="contain">Image entiere (bandes noires)</option></select>
<button type="button" onclick="up()">Envoyer les images</button>
<div id="st"></div>
<p style="font-size:13px;color:#999">Si le choix de fichier ne s'ouvre pas : ouvre <b>http://@IP@</b> dans ton navigateur (Chrome, Safari).</p>
<p><a href="/show?name=">Lancer le diaporama</a> &middot; espace libre : @FREE@ Mo</p>
<ul>@IMGS@</ul>
<script>
var W=@W@,H=@H@,CH=8192;
function load(file){return new Promise(function(ok,ko){var i=new Image();i.onload=function(){ok(i)};i.onerror=function(){ko(new Error('image illisible'))};i.src=URL.createObjectURL(file)})}
function wait(ms){return new Promise(function(r){setTimeout(r,ms)})}
async function post(url,body){
 for(var k=0;k<5;k++){
  var r,t;
  try{r=await fetch(url,{method:'POST',body:body});t=await r.text()}
  catch(e){if(k==4)throw new Error('connexion perdue ('+e.message+')');await wait(600);continue}
  if(r.ok)return t;
  if(r.status==409||r.status>=500&&k<4){await wait(600);continue}
  throw new Error(t)
 }
}
async function up(){
 var fs=document.getElementById('f').files,st=document.getElementById('st'),mode=document.getElementById('m').value;
 if(!fs.length){st.textContent='Choisis des images';return}
 for(var n=0;n<fs.length;n++){
  var lab='Image '+(n+1)+'/'+fs.length;
  try{
   st.textContent=lab+' : conversion...';
   var im=await load(fs[n]),c=document.createElement('canvas');c.width=W;c.height=H;
   var g=c.getContext('2d');g.fillStyle='#000';g.fillRect(0,0,W,H);
   var s=(mode=='cover'?Math.max:Math.min)(W/im.width,H/im.height),w=im.width*s,h=im.height*s;
   g.drawImage(im,(W-w)/2,(H-h)/2,w,h);
   var p=g.getImageData(0,0,W,H).data,o=new Uint8Array(W*H*2);
   for(var i=0,j=0;i<p.length;i+=4,j+=2){var v=((p[i]&248)<<8)|((p[i+1]&252)<<3)|(p[i+2]>>3);o[j]=v>>8;o[j+1]=v&255}
   var name=encodeURIComponent(fs[n].name.replace(/\\.[^.]*$/,''));
   for(var off=0;off<o.length;off+=CH){
    var end=Math.min(o.length,off+CH),last=end>=o.length?1:0;
    var t=await post('/upload?name='+name+'&off='+off+'&last='+last,o.subarray(off,end));
    if(off==0)name=encodeURIComponent(t.replace('OK','').trim());
    st.textContent=lab+' : '+Math.round(end*100/o.length)+'%';
   }
  }catch(e){st.textContent='Erreur ('+lab+') : '+e.message;return}
 }
 location.href='/';
}
</script></body></html>"""


async def serve(S, labels, on_change, led_choices=(), W=320, H=172, gallery=-1, port=80,
                ip="192.168.4.1", dns_port=53):
    size = W * H * 2
    asyncio.create_task(dns_server(ip, dns_port))
    try:                                                      # nettoie les envois interrompus
        for n in os.listdir(IMG_DIR):
            if n.endswith(".part"):
                os.remove(IMG_DIR + "/" + n)
    except OSError:
        pass

    async def reply(w, code, body, ctype="text/plain", extra=""):
        w.write(("HTTP/1.0 %s\r\nContent-Type: %s; charset=utf-8\r\nConnection: close\r\n%s\r\n"
                 % (code, ctype, extra)).encode())
        if body:
            w.write(body.encode() if isinstance(body, str) else body)
        await w.drain()

    async def upload(r, w, q, clen):
        # Envoi par morceaux : /upload?name=x&off=<octets deja recus>&last=0|1
        body = bytearray()
        while len(body) < clen and clen <= 65536:           # on lit TOUJOURS le corps avant de repondre
            chunk = await r.read(min(2048, clen - len(body)))
            if not chunk:
                break
            body += chunk
        S["up"] = ticks_ms()                                  # fige l'animation pendant l'envoi
        if clen > 65536 or len(body) != clen:
            await reply(w, "400 Bad Request", "Morceau incomplet")
            return
        try:
            off = int(q.get("off", "0"))
        except ValueError:
            off = 0
        try:
            os.mkdir(IMG_DIR)
        except OSError:
            pass
        if off == 0:
            if free_bytes() < size + 30000:
                await reply(w, "507 Insufficient Storage", "Plus de place : supprime des images")
                return
            base = clean(q.get("name", "image"))
            name, k = base, 2
            while exists("%s/%s.raw" % (IMG_DIR, name)) or exists("%s/%s.raw.part" % (IMG_DIR, name)):
                name = "%s%d" % (base[:21], k)
                k += 1
        else:
            name = clean(q.get("name", ""))
        path = "%s/%s.raw" % (IMG_DIR, name)
        tmp = path + ".part"
        have = os.stat(tmp)[6] if exists(tmp) else 0
        if off == 0:
            have = 0
        if have == off + clen and off > 0:                    # morceau deja recu (reessai) : ok
            pass
        elif have != off:
            await reply(w, "409 Conflict", "Decalage %d/%d" % (have, off))
            return
        else:
            with open(tmp, "wb" if off == 0 else "ab") as f:
                f.write(body)
            have += clen
        if q.get("last") == "1":
            if have != size:
                os.remove(tmp)
                await reply(w, "400 Bad Request", "Taille finale %d (attendu %d)" % (have, size))
                return
            if exists(path):
                os.remove(path)
            os.rename(tmp, path)
        await reply(w, "200 OK", "OK " + name)

    def page():
        opts = ['<option value="-1"%s>Auto (enchaine tout)</option>'
                % (" selected" if S["scene"] == -1 else "")]
        for i, lb in enumerate(labels):
            opts.append('<option value="%d"%s>%s</option>'
                        % (i, " selected" if S["scene"] == i else "", esc(lb)))
        leds = "".join('<option value="%s"%s>%s</option>'
                       % (k, " selected" if S["led"] == k else "", esc(lb)) for k, lb in led_choices)
        imgs = "".join(
            '<li>%s &middot; <a href="/show?name=%s">Afficher</a> &middot; '
            '<a href="/del?name=%s" onclick="return confirm(\'Supprimer ?\')">Supprimer</a></li>'
            % (esc(n), n, n) for n in list_images()) or "<li>Aucune image</li>"
        return (PAGE.replace("@MSG@", esc(S["message"])).replace("@OPTS@", "".join(opts))
                .replace("@BR@", str(S["brightness"])).replace("@LEDS@", leds)
                .replace("@LB@", str(S["led_brightness"])).replace("@IMGS@", imgs)
                .replace("@W@", str(W)).replace("@H@", str(H)).replace("@IP@", ip)
                .replace("@FREE@", "%.1f" % (free_bytes() / 1048576)))

    def apply_form(q):
        try:
            if q.get("message", "").strip():
                S["message"] = q["message"].strip()[:120]
            if "brightness" in q:
                S["brightness"] = max(5, min(100, int(q["brightness"])))
            if q.get("led") in [k for k, _ in led_choices]:
                S["led"] = q["led"]
            if "led_brightness" in q:
                S["led_brightness"] = max(0, min(100, int(q["led_brightness"])))
            if "scene" in q:
                sc = max(-1, min(len(labels) - 1, int(q["scene"])))
                if sc != S["scene"]:
                    S["image"] = ""
                S["scene"] = sc
            on_change()
        except ValueError:
            pass

    async def handle(r, w):
        try:
            line = await r.readline()
            clen = 0
            host = ""
            while True:
                h = await r.readline()
                if not h or h == b"\r\n":
                    break
                if h[:15].lower() == b"content-length:":
                    clen = int(h[15:].decode().strip())
                elif h[:5].lower() == b"host:":
                    host = h[5:].decode().strip()
            parts = line.split()
            if len(parts) < 2:
                return
            method, path = parts[0].decode(), parts[1].decode()
            route, _, qs = path.partition("?")
            q = parse_qs(qs)
            if DEBUG and route != "/upload":
                print("http:", method, route, host)
            if route == "/upload" and method == "POST":
                await upload(r, w, q, clen)
            elif route == "/del":
                name = clean(q.get("name", ""))
                try:
                    os.remove("%s/%s.raw" % (IMG_DIR, name))
                except OSError:
                    pass
                if S["image"] == name:
                    S["image"] = ""
                on_change()
                await reply(w, "303 See Other", "", extra="Location: /\r\n")
            elif route == "/show":
                if gallery >= 0:
                    S["image"] = clean(q["name"]) if q.get("name") else ""
                    S["scene"] = gallery
                    on_change()
                await reply(w, "303 See Other", "", extra="Location: /\r\n")
            elif route.startswith("/favicon"):
                await reply(w, "404 Not Found", "")
            elif route != "/":                                # sondes "portail captif" Android / iOS / Windows...
                await reply(w, "302 Found", "", extra="Location: http://%s/\r\nCache-Control: no-store\r\n" % ip)
            else:
                if qs:
                    apply_form(q)
                S["page"] = ticks_ms()                            # un telephone a ouvert la page
                await reply(w, "200 OK", page(), "text/html")
        except Exception as e:
            print("web:", repr(e))
            try:
                await reply(w, "500 Internal Server Error", "Erreur carte : " + repr(e))
            except Exception:
                pass
        finally:
            w.close()
            await w.wait_closed()

    await asyncio.start_server(handle, "0.0.0.0", port)
    while True:
        await asyncio.sleep(3600)
