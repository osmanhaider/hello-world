"""End-to-end test with a native-text PDF (what users typically receive
from their housing association email).
"""
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas
from parser import parse_bill
from translation import enrich_parsed

# Register a font that covers Estonian diacritics (ä, ö, ü, õ, š, ž)
pdfmetrics.registerFont(TTFont("DV",  "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"))
pdfmetrics.registerFont(TTFont("DVB", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"))

pdf_path = "/tmp/test_bill.pdf"
c = canvas.Canvas(pdf_path, pagesize=A4)
W, H = A4

def t(x, y, text, font="DV", size=10):
    c.setFont(font, size)
    c.drawString(x, H - y, text)

# Header
t(40, 40, "TALLINN, TEHNIKA TN 22, TEHNIKA TÄNAV T9 KORTERIÜHISTU", "DVB", 13)
t(40, 70, "Klient:    Muhammad Usman Haider")
t(40, 85, "           Tehnika 22-6")
t(40, 100, "           Tallinn 10149")

t(340, 70,  "Arve nr.",     "DVB"); t(420, 70,  "1550")
t(340, 85,  "Kuupäev",      "DVB"); t(420, 85,  "13.04.2026")
t(340, 100, "Tähtaeg",      "DVB"); t(420, 100, "23.04.2026")
t(340, 115, "Viitenumber",  "DVB"); t(420, 115, "10058")
t(340, 130, "Periood",      "DVB"); t(420, 130, "Märts 2026")

t(40, 150, "Neto pind", "DVB"); t(120, 150, "70,40 m²")

# Table
y = 200
c.line(40, H - y + 8, W - 40, H - y + 8)
t( 50, y, "Kirjeldus", "DVB")
t(280, y, "Ühik",      "DVB")
t(340, y, "Kogus",     "DVB")
t(420, y, "Hind",      "DVB")
t(500, y, "Summa",     "DVB")
y += 8
c.line(40, H - y, W - 40, H - y)
y += 12

rows = [
    ("Haldusteenus",                              "m2",  "70,40",  "0,173", "12,19"),
    ("Raamatupidamisteenus",                      "m2",  "70,40",  "0,074",  "5,23"),
    ("Tehnosüsteemide hooldusteenus",             "m2",  "70,40",  "0,225", "15,88"),
    ("Sise-ja väliskoristus",                     "m2",  "70,40",  "0,517", "36,40"),
    ("Porivaiba renditeenus",                     "krt", "70,40",  "0,076",  "5,38"),
    ("Prügivedu",                                 "m2",  "70,40",  "0,154", "10,90"),
    ("Üldelekter",                                "m2",  "70,40",  "0,238", "16,80"),
    ("Üldvesi",                                   "m2",  "70,40", "-0,015", "-1,06"),
    ("Küte",                                      "m2",  "70,40",  "0,649", "45,75"),
    ("Elekter päevane Alg: 9644 Lõpp: 9726",      "kwh", "82,00",  "0,170", "13,94"),
    ("Elekter öine Alg: 8895 Lõpp: 8971",         "kwh", "76,00",  "0,150", "11,40"),
    ("Külm vesi Alg: 443,500 Lõpp: 446,200",      "m3",   "2,70",  "2,604",  "7,03"),
    ("Soe vesi Alg: 219,600 Lõpp: 220,600",       "m3",   "1,00",  "2,604",  "2,60"),
    ("Vee soojendamine",                          "m3",   "1,00",  "5,611",  "5,61"),
    ("Remondifond",                               "m2",  "70,40",  "0,400", "28,16"),
]
for desc, unit, qty, price, amt in rows:
    t( 50, y, desc)
    t(280, y, unit)
    t(340, y, qty)
    t(420, y, price)
    t(500, y, amt)
    y += 16

y += 6
c.line(40, H - y + 4, W - 40, H - y + 4); y += 10
t(380, y, "Kokku",                 "DVB"); t(500, y, "217,29", "DVB")
y += 20
t(280, y, "Tasumisele kuulub EUR", "DVB"); t(500, y, "217,29", "DVB")

c.save()
print(f"Generated native-text PDF: {pdf_path}")

# Run the parser
parsed = parse_bill(pdf_path)
enriched = enrich_parsed(parsed)

print("\n" + "═" * 82)
print("NATIVE-TEXT PDF PARSER RESULTS")
print("═" * 82)
print(f"\nSource:     {enriched.get('_source')} (confidence: {enriched.get('confidence')})")
print()
for k in ["provider", "account_number", "bill_date", "due_date", "period",
          "period_en", "period_start", "period_end", "amount_eur",
          "net_area_m2", "utility_type", "consumption_kwh", "consumption_m3"]:
    print(f"  {k:20s} = {enriched.get(k)}")

print("\n── LINE ITEMS ──")
for i, li in enumerate(enriched.get("line_items", []), 1):
    et = (li.get("description_et") or "")[:45]
    en = (li.get("description_en") or "")[:35]
    amt = li.get("amount_eur")
    qty = li.get("quantity")
    unit = li.get("unit") or ""
    amt_s = f"€{amt:>7.2f}" if amt is not None else "   —   "
    qty_s = f"{qty:>7.2f}" if qty is not None else "   —   "
    print(f"  {i:>2}. {et:<47} → {en:<35} {qty_s} {unit:4s} {amt_s}")

line_sum = sum(li.get("amount_eur") or 0 for li in enriched.get("line_items", []))
print("\n── VALIDATION ──")
print(f"  Extracted:           {len(enriched.get('line_items', []))} / 15 expected")
print(f"  Line sum:            €{line_sum:.2f}")
print(f"  Header total:        €{enriched.get('amount_eur')}")
print(f"  Line sum == header:  {'✓' if abs(line_sum - (enriched.get('amount_eur') or 0)) < 0.01 else '✗'}")
