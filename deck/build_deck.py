"""Builds deck/d4data_demo.pptx: 11 slides for the 3-minute demo video, charts as images, speaker notes = the video script.
Run: python deck/make_charts.py && python deck/build_deck.py     (Gamma can import the .pptx too)"""
from pathlib import Path

from PIL import Image
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.util import Emu, Inches, Pt

HERE = Path(__file__).resolve().parent
IMG = HERE / "img"
LAND = HERE.parent / "landing" / "img"
APP = "d4data-rent-estimator.vercel.app"
NAVY, BLUE, GREY, PALE, MUT, WHITE = RGBColor(0x14, 0x23, 0x3C), RGBColor(0x2A, 0x78, 0xD6), RGBColor(0xC4, 0xC3, 0xB7), RGBColor(0xF4, 0xF3, 0xEE), RGBColor(0x5B, 0x6A, 0x80), RGBColor(255, 255, 255)

prs = Presentation()
prs.slide_width, prs.slide_height = Inches(13.333), Inches(7.5)
SW, SH = 13.333, 7.5


def new_slide(bg=WHITE, notes=""):
    s = prs.slides.add_slide(prs.slide_layouts[6])
    s.background.fill.solid()
    s.background.fill.fore_color.rgb = bg
    if notes:
        s.notes_slide.notes_text_frame.text = notes
    return s


def text(slide, x, y, w, h, paras, size=18, color=NAVY, bold=False, align=PP_ALIGN.LEFT, anchor=MSO_ANCHOR.TOP, spacing=1.1):
    tb = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = tb.text_frame
    tf.word_wrap = True
    tf.vertical_anchor = anchor
    tf.margin_left = tf.margin_right = Inches(0.05)
    items = paras if isinstance(paras, list) else [paras]
    for i, it in enumerate(items):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        if isinstance(it, tuple):
            t, kw = it
        else:
            t, kw = it, {}
        r = p.add_run()
        r.text = t
        r.font.size = Pt(kw.get("size", size))
        r.font.bold = kw.get("bold", bold)
        r.font.name = "Calibri"
        r.font.color.rgb = kw.get("color", color)
        p.alignment = kw.get("align", align)
        p.line_spacing = spacing
        p.space_after = Pt(kw.get("after", 6))
    return tb


def title(slide, t, sub=None, color=NAVY):
    text(slide, 0.6, 0.4, SW - 1.2, 1.2, t, size=32, bold=True, color=color, anchor=MSO_ANCHOR.TOP, spacing=1.0)
    if sub:
        text(slide, 0.6, 1.45, SW - 1.2, 0.6, sub, size=16, color=MUT)


def picture(slide, path, x, y, w, h):
    """Fit the image inside the (x, y, w, h) box, centred."""
    iw, ih = Image.open(path).size
    scale = min(w / iw, h / ih)
    pw, ph = iw * scale, ih * scale
    return slide.shapes.add_picture(str(path), Inches(x + (w - pw) / 2), Inches(y + (h - ph) / 2), Inches(pw), Inches(ph))


def card(slide, x, y, w, h, head, body, fill=PALE, head_color=BLUE):
    sh = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(x), Inches(y), Inches(w), Inches(h))
    sh.fill.solid(); sh.fill.fore_color.rgb = fill
    sh.line.fill.background()
    sh.adjustments[0] = 0.06
    text(slide, x + 0.2, y + 0.2, w - 0.4, 0.8, head, size=24, bold=True, color=head_color)
    text(slide, x + 0.2, y + 0.95, w - 0.4, h - 1.1, body, size=17, color=NAVY)


def stat(slide, x, y, w, big, label, dark=False):
    sh = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(x), Inches(y), Inches(w), Inches(1.7))
    sh.fill.solid(); sh.fill.fore_color.rgb = NAVY if dark else PALE
    sh.line.fill.background(); sh.adjustments[0] = 0.08
    text(slide, x, y + 0.12, w, 0.9, big, size=44, bold=True, color=WHITE if dark else BLUE, align=PP_ALIGN.CENTER)
    text(slide, x + 0.1, y + 1.0, w - 0.2, 0.6, label, size=15, color=RGBColor(0xCF, 0xE0, 0xF7) if dark else MUT, align=PP_ALIGN.CENTER)


def footer(slide, t="Team d4data | Microburbs Hackathon 2026"):
    text(slide, 0.6, 7.0, SW - 1.2, 0.35, t, size=11, color=MUT)


# 1 ---------------------------------------------------------------- hook
s = new_slide(NAVY, "Rents fell seventeen percent, then climbed forty-eight. So what should your flat rent for this week? We built an estimator that prices all 65,777 City of Sydney flats, and four in five estimates land within a hundred dollars.")
text(s, 0.9, 1.5, SW - 1.8, 2.6, "Rents fell 17%, then climbed 48%. So what should your flat rent for this week?", size=48, bold=True, color=WHITE, spacing=1.0)
text(s, 0.9, 4.3, SW - 1.8, 1.0, "We priced all 65,777 City of Sydney flats. Four in five estimates land within $100.", size=24, color=RGBColor(0xDC, 0xE8, 0xF8))
text(s, 0.9, 6.3, SW - 1.8, 0.5, "Team d4data  |  Microburbs Hackathon  |  7 November 2026", size=15, color=RGBColor(0x9F, 0xB6, 0xD6))

# 2 ---------------------------------------------------------------- why
s = new_slide(notes="Rent is the biggest bill for most households. Tenants can't tell if an asking rent is fair. Landlords price too high and sit vacant, or too low and leave money behind. Agents need a number they can defend.")
title(s, "Rent is the biggest bill, and nobody knows if the number is fair")
card(s, 0.6, 2.2, 3.9, 3.9, "Tenants", "Is this asking rent in line with nearby flats?")
card(s, 4.7, 2.2, 3.9, 3.9, "Landlords", "Too high and the flat sits vacant. Too low and money is left behind.")
card(s, 8.8, 2.2, 3.9, 3.9, "Agents", "Need a number they can defend, with and without parking.")
footer(s)

# 3 ---------------------------------------------------------------- finding 1
s = new_slide(notes="We studied 112,000 adverts. After adjusting for suburb, size and parking, rents ended 2020 seventeen percent below 2019, then jumped forty-eight percent, and now sit thirty-two percent above.")
title(s, "After the 2020 dip, rents rose 48% and now sit 32% above 2019")
picture(s, IMG / "rent_index.png", 0.8, 1.55, SW - 1.6, 5.0)
text(s, 0.6, 6.55, SW - 1.2, 0.5, "Adjusted for suburb, bedrooms, bathrooms, parking and type. Event dates approximate: timing, not proof of cause. Three-bedroom flats fell furthest, 28% from their peak.", size=12, color=MUT)

# 4 ---------------------------------------------------------------- findings 2 and 3
s = new_slide(notes="A car space went from worth nothing to about sixty dollars a week. And the market is cooling: same-flat growth fell from eight to ten percent a year to two to five.")
title(s, "A car space is worth about $60 a week, and the market is cooling")
picture(s, IMG / "car_premium.png", 0.5, 1.7, 6.6, 4.6)
text(s, 0.6, 6.3, 6.5, 0.6, "Matched on suburb, bedrooms, bathrooms and type. About $3,100 a year.", size=13, color=MUT)
text(s, 7.5, 2.0, 5.2, 0.6, "Same-flat rent growth, per year", size=20, bold=True, color=MUT)
text(s, 7.5, 2.8, 5.2, 1.2, "8-10%", size=66, bold=True, color=GREY)
text(s, 7.5, 3.9, 5.2, 0.5, "2022 and 2023", size=18, color=MUT)
text(s, 7.5, 4.6, 5.2, 1.2, "2-5%", size=66, bold=True, color=BLUE)
text(s, 7.5, 5.7, 5.2, 0.5, "now", size=18, color=MUT)

# 5 ---------------------------------------------------------------- how it works
s = new_slide(notes="Our model is LightGBM, predicting log rent, so a few five-thousand-dollar outliers can't drag it around. Almost half of each prediction comes from where the market is right now for that suburb and bedroom count. Then it adjusts for the flat's own history, its building and parking.")
title(s, "Almost half of each prediction comes from where the market is right now")
picture(s, IMG / "factors.png", 0.6, 1.6, 8.2, 4.9)
text(s, 9.1, 2.0, 3.8, 4.5, [("LightGBM", {"bold": True, "size": 22, "color": BLUE}), "Predicts log rent with an absolute-error loss, so a few $5,000-a-week outliers cannot drag it around.", ("Two predictions per flat", {"bold": True, "size": 22, "color": BLUE}), "With and without a car space. Rent with parking is never below rent without."], size=16)
footer(s)

# 6 ---------------------------------------------------------------- momentum
s = new_slide(notes="We add momentum: how much rents moved over the last three and six months, with a three-month lag, because the judged adverts fall months after our data ends.")
title(s, "Momentum tells the model how fast the market was moving")
picture(s, IMG / "momentum.png", 0.6, 1.6, SW - 1.2, 3.9)
text(s, 0.8, 5.5, SW - 1.6, 1.5, ["Market level = average log rent of earlier adverts in a 3-month window, for the suburb and bedroom count.", "Everything is lagged 3 months, because judged adverts fall months after our data ends.", "Example: Surry Hills one-bedrooms rose +2.0% over 6 months."], size=16)

# 7 ---------------------------------------------------------------- date split
s = new_slide(notes="To avoid fooling ourselves, we split by date. We trained only on adverts before June, and scored once on June and July: twenty-seven hundred adverts the model never saw. Nothing after July thirty-first was used.")
title(s, "We split by date so the model never saw the answers")
picture(s, IMG / "date_split.png", 0.6, 1.9, SW - 1.2, 3.6)
text(s, 0.8, 5.6, SW - 1.6, 1.4, ["Settings were chosen using only the training period.", "Check adverts never went into building or tuning the method.", "We did not retrain on the check adverts."], size=17)

# 8 ---------------------------------------------------------------- results
s = new_slide(notes="The result: a typical miss of forty-four dollars a week, seventy-nine percent within a hundred dollars, R-squared point eight eight eight. A simple suburb-and-bedroom median misses by ninety. The organisers' baseline missed by eighty-six on their own set, so that's context, not a head-to-head.")
title(s, "A typical miss of $44 a week, 79% within $100")
stat(s, 0.6, 1.6, 3.9, "$44", "typical weekly miss")
stat(s, 4.7, 1.6, 3.9, "79.2%", "of estimates within $100")
stat(s, 8.8, 1.6, 3.9, "0.888", "R squared on the held-out check")
picture(s, IMG / "model_compare.png", 1.3, 3.5, 7.2, 3.3)
text(s, 8.8, 3.9, 4.0, 2.6, [("Context, not a head-to-head", {"bold": True, "size": 18, "color": BLUE}), "Organisers' baseline: $86 and 55.21% within $100, on their frozen August to September set. Our figures come from an earlier check: 2,713 adverts, 1 Jun to 31 Jul 2026."], size=14, color=NAVY)

# 9 ---------------------------------------------------------------- demo
s = new_slide(notes="Here it is live. Search ten to fourteen Cooper Street: about a thousand and forty-three dollars a week, with a likely range. Switch to the heat map to see rent by square across the city.")
title(s, "Try it: search your address, see the rent heat map")
picture(s, LAND / "fig-app-hero.jpg", 0.5, 1.6, 7.6, 3.6)
picture(s, LAND / "fig-app-heatmap.jpg", 8.4, 1.5, 4.5, 5.0)
text(s, 0.6, 5.35, 7.5, 0.5, "10-14 Cooper Street, Surry Hills: about $1,043 a week without a car space.", size=16, color=NAVY)
text(s, 0.6, 6.0, 7.5, 0.7, APP, size=26, bold=True, color=BLUE)
text(s, 8.4, 6.55, 4.5, 0.4, "Map data: OpenStreetMap contributors", size=11, color=MUT)

# 10 --------------------------------------------------------------- limits and next
s = new_slide(notes="The judged window is two to four months past our data, so the real miss may be larger.")
title(s, "Where we're least sure, and what we'd do next")
card(s, 0.6, 1.9, 6.0, 4.7, "Least sure", ["The judged adverts fall 2 to 4 months after our data, so real error may be higher (a July-only test gave about $50).", "Flats with no rent history miss by about $66 against $42.", "Waterfront and luxury areas and 3-bedrooms are hardest.", "Asking-rent estimates, not valuations."])
card(s, 6.9, 1.9, 5.8, 4.7, "Next", ["Add June and July market-trend data.", "Test floor area and building age.", "Re-check on the hidden August to September adverts."], head_color=BLUE)
footer(s)

# 11 --------------------------------------------------------------- close
s = new_slide(NAVY, "Try your own address and tell us if the number feels right. We're team d4data.")
text(s, 0.9, 1.9, SW - 1.8, 1.8, "Does the number feel right for your flat?", size=48, bold=True, color=WHITE, spacing=1.0)
text(s, 0.9, 4.1, SW - 1.8, 0.8, "Open the live app: " + APP, size=28, bold=True, color=RGBColor(0x9B, 0xBF, 0xEE))
text(s, 0.9, 5.4, SW - 1.8, 0.5, "Team d4data  |  Microburbs Hackathon 2026", size=16, color=RGBColor(0x9F, 0xB6, 0xD6))
text(s, 0.9, 6.5, SW - 1.8, 0.7, "Research for information only; not valuations or financial advice. Uses only information dated by 31 July 2026.", size=12, color=RGBColor(0x9F, 0xB6, 0xD6))

out = HERE / "d4data_demo.pptx"
prs.save(out)
print("wrote", out, f"({out.stat().st_size/1e3:.0f} KB), slides:", len(prs.slides))
