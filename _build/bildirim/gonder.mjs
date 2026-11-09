// Yeni eklenen haberleri bildirim izni veren ziyaretçilere gönderir (Firebase Cloud Messaging).
// GitHub Actions'ta FIREBASE_SERVICE_ACCOUNT gizli değişkeniyle çalışır; yoksa hiçbir şey yapmaz.
import fs from "node:fs";
import path from "node:path";
import admin from "firebase-admin";

const KOK = path.resolve(path.dirname(new URL(import.meta.url).pathname), "..", "..");
const SITE = "https://ciftcigundemi.com";
const DURUM = path.join(KOK, "data", "bildirim-durum.json");
const EN_FAZLA = 2;                 // bir çalışmada en fazla kaç haber bildirilir
const TAZE_SAAT = 12;               // bundan eski haberler bildirilmez
const SESSIZ = [23, 7];             // TR saatiyle 23:00–07:00 arası gönderim yok

const sa = process.env.FIREBASE_SERVICE_ACCOUNT;
if (!sa) { console.log("FIREBASE_SERVICE_ACCOUNT yok, bildirim atlanıyor."); process.exit(0); }

// Test modu: sessiz saat ve yeni haber şartı olmadan tüm abonelere deneme bildirimi gönderir,
// her abonenin sonucunu yazar, hiçbir kaydı silmez ve durum dosyasına dokunmaz.
if (process.env.TEST === "1") {
  admin.initializeApp({ credential: admin.credential.cert(JSON.parse(sa)) });
  const proje = JSON.parse(sa).project_id;
  const snap = await admin.firestore().collection("bildirim").get();
  console.log(`TEST: proje ${proje}, ${snap.size} abone kaydı.`);
  for (const d of snap.docs) {
    const tk = d.get("token"), z = d.get("zaman");
    const zaman = z && z.toDate ? z.toDate().toISOString() : "?";
    if (typeof tk !== "string") { console.log("kayıt", d.id.slice(0, 8), zaman, "token yok"); continue; }
    try {
      const id = await admin.messaging().send({
        token: tk,
        webpush: {
          notification: { title: "Çiftçi Gündemi · Deneme bildirimi", body: "Bu bir deneme bildirimidir. Görüyorsanız bildirimler çalışıyor.", icon: `${SITE}/assets/ikon-192.png`, data: { link: SITE + "/" } },
          fcmOptions: { link: SITE + "/" }, headers: { TTL: "3600", Urgency: "high" }
        }
      });
      console.log("kayıt", d.id.slice(0, 8), zaman, "uç:", tk.split(":")[0].slice(0, 6) + "…", "BAŞARILI", id.split("/").pop());
    } catch (e) { console.log("kayıt", d.id.slice(0, 8), zaman, "HATA", e.code, (e.message || "").slice(0, 200)); }
  }
  process.exit(0);
}

const V = JSON.parse(fs.readFileSync(path.join(KOK, "data", "haberler.json"), "utf8"));
const haberler = [...V.haberler].sort((a, b) => String(b.eklenme || b.tarih).localeCompare(String(a.eklenme || a.tarih)));
let durum = fs.existsSync(DURUM) ? JSON.parse(fs.readFileSync(DURUM, "utf8")) : null;
if (!durum) {
  // İlk çalışma: mevcut haberleri gönderilmiş say, eski haberlerle kimseyi rahatsız etme
  fs.writeFileSync(DURUM, JSON.stringify({ gonderilen: haberler.map(h => h.id) }, null, 1) + "\n");
  console.log("Durum dosyası oluşturuldu; bundan sonra eklenen haberler bildirilecek.");
  process.exit(0);
}
const gonderilen = new Set(durum.gonderilen);
const saat = Number(new Intl.DateTimeFormat("en-GB", { hour: "numeric", hour12: false, timeZone: "Europe/Istanbul" }).format(new Date()));
const sessiz = saat >= SESSIZ[0] || saat < SESSIZ[1];
const simdi = Date.now();
const yeni = haberler.filter(h => !gonderilen.has(h.id));
const taze = yeni.filter(h => simdi - Date.parse(h.eklenme || h.tarih) < TAZE_SAAT * 36e5);
// Bayatlamış yeni haberleri sessizce gönderilmiş say
for (const h of yeni) if (!taze.includes(h)) gonderilen.add(h.id);
if (!taze.length || sessiz) {
  if (sessiz && taze.length) console.log(`Sessiz saat (${saat}:00), ${taze.length} haber sabaha bekliyor.`);
  else console.log("Bildirilecek yeni haber yok.");
  kaydet(); process.exit(0);
}

admin.initializeApp({ credential: admin.credential.cert(JSON.parse(sa)) });
const db = admin.firestore();
const snap = await db.collection("bildirim").get();
const kayitlar = snap.docs.map(d => ({ ref: d.ref, token: d.get("token") })).filter(k => typeof k.token === "string");
console.log(`${kayitlar.length} abone, ${taze.length} yeni haber.`);
for (const d of snap.docs) { const z = d.get("zaman"); console.log("abone kaydı:", z && z.toDate ? z.toDate().toISOString() : "?", "token uzunluğu", (d.get("token") || "").length); }

// Bildirim kapak görseliyle gider: görseli henüz eklenmemiş haber sonraki çalışmayı bekler.
const hazir = taze.filter(h => h.gorsel);
if (!hazir.length) { console.log("Kapak görseli hazır haber yok, bekleniyor."); kaydet(); process.exit(0); }
const secilen = hazir.slice(0, EN_FAZLA);
for (const h of hazir) gonderilen.add(h.id);
const silinecek = new Set();
for (const h of secilen) {
  const link = `${SITE}/haber/${h.id}/`;
  const kapak = `${SITE}/${h.gorsel}`;
  for (let j = 0; j < kayitlar.length; j += 500) {
    const parca = kayitlar.slice(j, j + 500);
    const cevap = await admin.messaging().sendEachForMulticast({
      tokens: parca.map(k => k.token),
      webpush: {
        notification: {
          title: "Çiftçi Gündemi",
          icon: `${SITE}/assets/ikon-192.png`,
          badge: `${SITE}/assets/ikon-192.png`,
          image: kapak,
          tag: h.id,
          lang: "tr",
          data: { link }
        },
        fcmOptions: { link },
        headers: { TTL: String(TAZE_SAAT * 3600), Urgency: "normal" }
      }
    });
    cevap.responses.forEach((r, n) => {
      const kod = r.error && r.error.code;
      if (kod) console.log("hata:", kod, (r.error.message || "").slice(0, 160));
      if (kod === "messaging/registration-token-not-registered" || kod === "messaging/invalid-registration-token") silinecek.add(parca[n].ref);
    });
    console.log(`${h.id}: ${cevap.successCount} başarılı, ${cevap.failureCount} hatalı`);
  }
}
for (const ref of silinecek) await ref.delete();
if (silinecek.size) console.log(`${silinecek.size} geçersiz abone kaydı silindi.`);
kaydet();

function kaydet() {
  const sirali = haberler.map(h => h.id).filter(id => gonderilen.has(id));
  fs.writeFileSync(DURUM, JSON.stringify({ gonderilen: sirali }, null, 1) + "\n");
}
