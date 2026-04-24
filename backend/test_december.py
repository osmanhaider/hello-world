"""Test OCR parser on the December 2025 bill (Invoice 1505).
Notable: this bill has no water lines and no doormat rental — just 11 items.
"""
from PIL import Image, ImageDraw, ImageFont
from parser import parse_bill
from translation import enrich_parsed

W, H = 1000, 1200
img = Image.new("RGB", (W, H), "white")
draw = ImageDraw.Draw(img)

font_big  = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 18)
font      = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",      15)
font_bold = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 15)

y = 30
draw.text((40, y), "TALLINN, TEHNIKA TN 22, TEHNIKA TÄNAV T9 KORTERIÜHISTU", font=font_big, fill="black")
y += 50
draw.text((40, y), "Klient:    Muhammad Usman Haider", font=font, fill="black"); y += 22
draw.text((40, y), "           Tehnika 22-6",           font=font, fill="black"); y += 22
draw.text((40, y), "           Tallinn 10149",          font=font, fill="black"); y += 30

draw.text((540, 80),  "Arve nr.        1505",            font=font, fill="black")
draw.text((540, 102), "Kuupäev         08.01.2026",      font=font, fill="black")
draw.text((540, 124), "Tähtaeg         23.01.2026",      font=font, fill="black")
draw.text((540, 146), "Viitenumber     10058",           font=font, fill="black")
draw.text((540, 168), "Periood         Detsember 2025",  font=font, fill="black")

y = 200
draw.text((40, y), "Neto pind   70,40 m²", font=font, fill="black"); y += 40

draw.line((40, y - 5, W - 40, y - 5), fill="black")
draw.text(( 50, y), "Kirjeldus", font=font_bold, fill="black")
draw.text((420, y), "Ühik",      font=font_bold, fill="black")
draw.text((500, y), "Kogus",     font=font_bold, fill="black")
draw.text((620, y), "Hind",      font=font_bold, fill="black")
draw.text((800, y), "Summa",     font=font_bold, fill="black")
y += 25
draw.line((40, y - 2, W - 40, y - 2), fill="black"); y += 8

rows = [
    ("Haldusteenus",                              "m2",  "70,40",  "0,173", "12,19"),
    ("Raamatupidamisteenus",                      "m2",  "70,40",  "0,074",  "5,23"),
    ("Tehnosüsteemide hooldusteenus",             "m2",  "70,40",  "0,225", "15,88"),
    ("Sise-ja väliskoristus",                     "m2",  "70,40",  "0,517", "36,40"),
    ("Prügivedu",                                 "m2",  "70,40",  "0,145", "10,26"),
    ("Üldelekter",                                "m2",  "70,40",  "0,301", "21,23"),
    ("Üldvesi",                                   "m2",  "70,40", "-0,012", "-0,89"),
    ("Küte",                                      "m2",  "70,40",  "0,891", "62,78"),
    ("Elekter päevane Alg: 9444 Lõpp: 9494",      "kwh", "50,00",  "0,171",  "8,55"),
    ("Elekter öine Alg: 8704 Lõpp: 8762",         "kwh", "58,00",  "0,150",  "8,70"),
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
draw.text((600, y), "Kokku",                 font=font_bold, fill="black")
draw.text((800, y), "208,49",                font=font_bold, fill="black"); y += 24
draw.text((500, y), "Tasumisele kuulub EUR", font=font_bold, fill="black")
draw.text((800, y), "208,49",                font=font_bold, fill="black")

path = "/tmp/test_bill_dec2025.png"
img.save(path)
print(f"Generated: {path}")

parsed = parse_bill(path)
enriched = enrich_parsed(parsed)

print("\n" + "═" * 82)
print("DECEMBER 2025 BILL — TESSERACT OCR PARSER RESULTS")
print("═" * 82)

print("\n── HEADER ──")
for k in ["provider", "account_number", "bill_date", "due_date", "period",
          "period_en", "period_start", "period_end", "amount_eur",
          "net_area_m2", "utility_type", "consumption_kwh", "consumption_m3",
          "_source"]:
    v = enriched.get(k)
    print(f"  {k:20s} = {v}")

print("\n── TRANSLATED SUMMARY ──")
print("  " + str(enriched.get("translated_summary", "")))

print("\n── LINE ITEMS ──")
expected_total = 208.49
ok_count = 0
for i, li in enumerate(enriched.get("line_items", []), 1):
    et = (li.get("description_et") or "")[:40]
    en = (li.get("description_en") or "")[:40]
    amt = li.get("amount_eur")
    qty = li.get("quantity")
    unit = li.get("unit") or ""
    amt_s = f"€{amt:>7.2f}" if amt is not None else "   —   "
    qty_s = f"{qty:>7.2f}" if qty is not None else "   —   "
    print(f"  {i:>2}. {et:<40} → {en:<33} {qty_s} {unit:4s} {amt_s}")
    if amt is not None:
        ok_count += 1

line_sum = sum(li.get("amount_eur") or 0 for li in enriched.get("line_items", []))
print("\n── VALIDATION ──")
print(f"  Line items extracted:     {len(enriched.get('line_items', []))} / 11 expected")
print(f"  Line items with amount:   {ok_count}")
print(f"  Sum of line amounts:      €{line_sum:.2f}")
print(f"  Header total (Kokku):     €{enriched.get('amount_eur')}")
print(f"  Expected total:           €{expected_total}")
print(f"  Header match:             {'✓' if enriched.get('amount_eur') == expected_total else '✗'}")
print(f"  Line sum within €2:       {'✓' if abs(line_sum - expected_total) < 2 else '✗'}")
