"""End-to-end test of the OCR pipeline with a synthetic Estonian bill."""
from PIL import Image, ImageDraw, ImageFont
from parser import parse_bill
from translation import enrich_parsed
import json
import os

# Generate a synthetic Estonian utility bill image that mimics the
# Tehnika TN 22 korteriühistu invoice layout.
W, H = 1000, 1200
img = Image.new("RGB", (W, H), "white")
draw = ImageDraw.Draw(img)

try:
    font_big = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 18)
    font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 15)
    font_bold = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 15)
except OSError:
    font_big = font = font_bold = ImageFont.load_default()

y = 30

draw.text((40, y), "TALLINN, TEHNIKA TN 22 KORTERIÜHISTU", font=font_big, fill="black")
y += 50
draw.text((40, y), "Klient:    Muhammad Usman Haider", font=font, fill="black"); y += 22
draw.text((40, y), "           Tehnika 22-6", font=font, fill="black"); y += 22
draw.text((40, y), "           Tallinn 10149", font=font, fill="black"); y += 30

draw.text((540, 80), "Arve nr.        1550", font=font, fill="black")
draw.text((540, 102), "Kuupäev         13.04.2026", font=font, fill="black")
draw.text((540, 124), "Tähtaeg         23.04.2026", font=font, fill="black")
draw.text((540, 146), "Viitenumber     10058", font=font, fill="black")
draw.text((540, 168), "Periood         Märts 2026", font=font, fill="black")

y = 200
draw.text((40, y), "Neto pind   70,40 m²", font=font, fill="black"); y += 40

# Table header
draw.line((40, y - 5, W - 40, y - 5), fill="black")
draw.text(( 50, y), "Kirjeldus",    font=font_bold, fill="black")
draw.text((420, y), "Ühik",         font=font_bold, fill="black")
draw.text((500, y), "Kogus",        font=font_bold, fill="black")
draw.text((620, y), "Hind",         font=font_bold, fill="black")
draw.text((800, y), "Summa",        font=font_bold, fill="black")
y += 25
draw.line((40, y - 2, W - 40, y - 2), fill="black")
y += 8

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
    ("Elekter päevane Alg: 9644 Löpp: 9726",      "kwh", "82,00",  "0,170", "13,94"),
    ("Elekter öine Alg: 8895 Löpp: 8971",         "kwh", "76,00",  "0,150", "11,40"),
    ("Külm vesi Alg: 443,500 Löpp: 446,200",      "m3",   "2,70",  "2,604",  "7,03"),
    ("Soe vesi Alg: 219,600 Löpp: 220,600",       "m3",   "1,00",  "2,604",  "2,60"),
    ("Vee soojendamine",                          "m3",   "1,00",  "5,611",  "5,61"),
    ("Remondifond",                               "m2",  "70,40",  "0,400", "28,16"),
]
for desc, unit, qty, price, amt in rows:
    draw.text(( 50, y), desc,  font=font, fill="black")
    draw.text((420, y), unit,  font=font, fill="black")
    draw.text((500, y), qty,   font=font, fill="black")
    draw.text((620, y), price, font=font, fill="black")
    draw.text((800, y), amt,   font=font, fill="black")
    y += 24

y += 10
draw.line((40, y, W - 40, y), fill="black"); y += 10
draw.text((600, y), "Kokku", font=font_bold, fill="black")
draw.text((800, y), "217,29", font=font_bold, fill="black"); y += 24
draw.text((500, y), "Tasumisele kuulub EUR", font=font_bold, fill="black")
draw.text((800, y), "217,29", font=font_bold, fill="black")

path = "/tmp/test_bill.png"
img.save(path)
print(f"Generated test bill: {path}")

# Run the parser
parsed = parse_bill(path)
enriched = enrich_parsed(parsed)

print("\n=== HEADER FIELDS ===")
for k in ["provider", "account_number", "bill_date", "due_date", "period",
          "period_en", "amount_eur", "net_area_m2", "utility_type",
          "consumption_kwh", "consumption_m3", "_source"]:
    print(f"  {k:20s} = {enriched.get(k)}")

print("\n=== LINE ITEMS ===")
for li in enriched.get("line_items", []):
    et = li.get("description_et", "")[:40]
    en = li.get("description_en", "")[:40]
    amt = li.get("amount_eur")
    qty = li.get("quantity")
    unit = li.get("unit")
    amt_s = f"€{amt:6.2f}" if amt is not None else "   —  "
    qty_s = f"{qty:7.2f}" if qty is not None else "   —   "
    print(f"  {et:<42} → {en:<35} qty={qty_s} {unit or '':4s} {amt_s}")

print(f"\nTotal line items: {len(enriched.get('line_items', []))}")
print(f"Sum of line amounts: €{sum(li.get('amount_eur') or 0 for li in enriched.get('line_items', [])):.2f}")
print(f"Header total:        €{enriched.get('amount_eur')}")
