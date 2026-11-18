# Bike Speed AI — Business Plan

**Goal:** $20,000 revenue in 12 months. **Owner time:** ~20 min/month once set up.
**Asset:** this repo. It measures a rider's speed from drone follow-cam footage and burns a
broadcast-style speed graphic into the video (`render.py`), and it also exports per-frame speed as CSV.

---

## 1. The honest picture first

* **Nobody can promise $20k at 20 min/month.** Anyone who does is selling you something. This plan
  gives the target a realistic chance; it doesn't guarantee it.
* **The one-time setup takes about 3 hours of your time, and the law requires it to be you.**
  That covers payment accounts with identity checks, tax and business registration, and your name
  on sales emails. The full list is in [YOUR_TASKS.md](YOUR_TASKS.md).
* **Self-serve sales alone probably won't reach $20k in year 1.** The money is in a few B2B
  licenses to people who already produce cycling, triathlon and event broadcasts. You work in sports
  live production, so you already know these buyers, and that's the unfair advantage here.

## 2. What we sell

| Product | Buyer | Price | How it's delivered | Your time |
|---|---|---|---|---|
| **Creator License** | Cycling YouTubers, coaches, drone pilots | **$49 one-time** | Lemon Squeezy checkout → automatic download link | 0 |
| **Event License** | Race organisers, local sports streams | **$1,500 / event** | Invoice via Lemon Squeezy, delivered as speed-overlay files + CSV | ~5 min to send the email I drafted |
| **Season License** | Regional broadcasters, production houses | **$4,000 / season** | Same, plus white-label colours and logo in the graphic | ~5 min + one 30-min call |

Why Lemon Squeezy: it's a *Merchant of Record*. It collects sales tax and VAT worldwide, takes card
payments, delivers the files and issues the license keys, so there's no tax admin for you. The fee is
about 5% + $0.50 per sale.

## 3. The math to $20,000

| Source | Units | Revenue |
|---|---|---|
| Season licenses | 3 | $12,000 |
| Event licenses | 3 | $4,500 |
| Creator licenses | 80 (~7/month) | $3,920 |
| **Total (before ~5% fees)** | | **$20,420** |

The B2B row carries the plan. **4 season deals alone ≈ $16k.** That's why outreach to your existing
contacts is the main part of your 20 minutes, not admin.

**Costs:** domain ~$12/yr. Hosting is free (static landing page). Lemon Squeezy takes a percentage
only, with no monthly fee. The software runs on the customer's machine, so there are no GPU servers.
**Fixed costs: under $15/year.**

## 4. Getting customers (I write all of this; you press send or approve)

1. **Warm B2B outreach.** Each month: 2 short emails to people in your broadcast network
   (templates in [outreach.md](outreach.md)). One "yes" a quarter is enough.
2. **The demo clip sells it.** A 15-second clip of real drone footage with the speed graphic
   ([YOUR_TASKS.md](YOUR_TASKS.md) step 6) goes on the landing page, YouTube Shorts, Instagram and
   cycling subreddits/forums.
3. **Search traffic.** Landing page copy targets "cycling speed overlay", "drone bike speed",
   and "measure cycling speed from video".
4. **Thai market first.** You can sell in Thai to Thai race organisers (gran fondos, triathlons,
   criteriums), where there's less competition and you already have relationships.

## 5. Your 20 minutes each month

| Minutes | Task |
|---|---|
| 5 | Open the Lemon Squeezy dashboard: check sales and refunds, reply to any email flagged "needs you" |
| 10 | Send the 2 outreach emails I prepared (copy, edit the name, send) |
| 5 | Open a Claude Code session and say **"monthly bike-speed review"**: I update the plan and draft next month's emails/posts |

## 6. Milestones / kill criteria

| By | Signal | If missed |
|---|---|---|
| Month 1 | Setup done, landing page live, 10 outreach emails sent | Do the setup before anything else; nothing works without it |
| Month 3 | ≥1 B2B license **or** ≥15 creator sales | Change the offer: lower B2B price to $750/event, or bundle "done-for-you renders" |
| Month 6 | ≥ $8,000 cumulative | On track. Otherwise decide: push B2B harder (more of your time) or keep it as a side income |

## 7. Product roadmap (I build it, no time from you)

- [x] Headless renderer `render.py` → MP4 with speed graphic + CSV (done in this PR)
- [x] Fixed speed-measurement bug (speeds could read up to ~50% low before) (done in this PR)
- [ ] Simple installer (Windows .exe / macOS app) so creators don't need Python
- [ ] License-key check against the Lemon Squeezy License API
- [ ] White-label options: colours, logo, mph/km/h (mph already supported)
- [ ] Live mode: output a speed value over NDI/HTTP for vMix / OBS / CasparCG, for live broadcasts
